/**
 * ⚡ Cloudflare Worker + D1 Backend for TempMail
 * Domain: yourdomain.com
 * 
 * Features:
 * 1. Email Handler: Cloudflare Email Routing catch-all (*@yourdomain.com) -> saves to D1.
 * 2. Auto OTP Extractor: Automatically extracts 4-8 digit verification codes.
 * 3. HTTP REST API: Endpoints for web frontend & bot automation (/api/generate, /api/messages, /api/code, etc.).
 * 4. Auto Cleanup: Prunes emails older than 48 hours to stay well within D1 5GB free tier.
 */

// --- OTP Extraction Helper ---
function extractOtp(text, subject = '') {
  const combined = `${subject}\n${text}`;
  
  const patterns = [
    /(?:code|kode|pin|otp|verifikasi|verification)[\s:]*([0-9]{4,8})/i,
    /(?:is|adalah)[\s:]*([0-9]{4,8})/i,
    /\b([0-9]{6})\b/,
    /\b([0-9]{4,8})\b/
  ];

  for (const regex of patterns) {
    const match = combined.match(regex);
    if (match && match[1]) {
      return match[1];
    }
  }
  return '';
}

// --- Email Body / Stream Parser Helper ---
async function readStream(stream) {
  const reader = stream.getReader();
  const chunks = [];
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return new TextDecoder('utf-8').decode(result);
}

// Simple MIME text extraction fallback
function extractTextFromMime(raw) {
  let html = '';
  let text = '';

  const htmlMatch = raw.match(/<html[\s\S]*?<\/html>/i);
  if (htmlMatch) {
    html = htmlMatch[0];
  }

  const headerEnd = raw.indexOf('\r\n\r\n');
  const body = headerEnd !== -1 ? raw.substring(headerEnd + 4) : raw;

  text = body.replace(/--[a-zA-Z0-9_-]+(--)?/g, '')
             .replace(/Content-Type:[^\n]+/gi, '')
             .replace(/Content-Transfer-Encoding:[^\n]+/gi, '')
             .trim();

  if (!html && raw.includes('<') && raw.includes('>')) {
    html = raw;
  }

  return { text: text || raw.slice(0, 5000), html };
}

// --- CORS Headers ---
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders,
    },
  });
}

export default {
  // 1. CLOUDFLARE EMAIL ROUTING EVENT HANDLER
  async email(message, env, ctx) {
    try {
      const to = (message.to || '').toLowerCase().trim();
      const from = message.from || 'unknown@sender.com';
      const subject = message.headers.get('subject') || '(Tanpa Subjek)';
      const raw = await readStream(message.raw);
      
      const { text, html } = extractTextFromMime(raw);
      const otp = extractOtp(text, subject);
      const id = crypto.randomUUID();

      // Save into Cloudflare D1
      await env.DB.prepare(
        `INSERT INTO emails (id, to_address, from_address, subject, text_content, html_content, otp_code, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))`
      ).bind(id, to, from, subject, text, html, otp).run();

      // Background auto-cleanup: delete emails older than 2 days
      ctx.waitUntil(
        env.DB.prepare(`DELETE FROM emails WHERE created_at < datetime('now', '-2 days')`).run()
      );
    } catch (err) {
      console.error('Email processing error:', err);
    }
  },

  // 2. HTTP REST API HANDLER
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const DOMAINS_LIST = (env.TEMPMAIL_DOMAINS || env.TEMPMAIL_DOMAIN || 'yourdomain.com')
      .split(',')
      .map((d) => d.trim().toLowerCase())
      .filter(Boolean);
    const PRIMARY_DOMAIN = DOMAINS_LIST[0] || 'yourdomain.com';

    try {
      // Health Check
      if (path === '/' || path === '/health' || path === '/api/health') {
        return jsonResponse({
          status: 'ok',
          message: 'Cloudflare TempMail D1 Engine Active',
          domains: DOMAINS_LIST,
          primaryDomain: PRIMARY_DOMAIN,
          endpoints: ['/api/domains', '/api/generate', '/api/messages', '/api/code', '/code']
        });
      }

      // GET /api/domains
      if (path === '/api/domains' && request.method === 'GET') {
        return jsonResponse(
          DOMAINS_LIST.map((d) => ({ id: d, domain: d, isActive: true, isPrivate: false }))
        );
      }

      // POST /api/generate or POST /api/accounts
      if ((path === '/api/generate' || path === '/api/accounts') && request.method === 'POST') {
        let prefix = 'grok_';
        let targetDomain = DOMAINS_LIST[Math.floor(Math.random() * DOMAINS_LIST.length)];
        try {
          const body = await request.json();
          if (body && body.prefix) prefix = body.prefix;
          if (body && body.domain && DOMAINS_LIST.includes(body.domain.toLowerCase().trim())) {
            targetDomain = body.domain.toLowerCase().trim();
          }
        } catch {}

        const rand = Math.random().toString(36).substring(2, 8);
        const address = `${prefix}${rand}@${targetDomain}`.toLowerCase();
        const token = `d1_${btoa(address)}`;

        return jsonResponse({
          id: address,
          address: address,
          token: token,
          domain: targetDomain,
          createdAt: new Date().toISOString(),
        });
      }

      // GET /api/messages
      if (path === '/api/messages' && request.method === 'GET') {
        let email = url.searchParams.get('email');
        if (!email) {
          const auth = request.headers.get('Authorization') || '';
          if (auth.startsWith('Bearer d1_')) {
            try {
              email = atob(auth.replace('Bearer d1_', ''));
            } catch {}
          }
        }

        if (!email) {
          return jsonResponse({ error: 'Missing required parameter: email' }, 400);
        }

        const emailClean = email.toLowerCase().trim();
        const { results } = await env.DB.prepare(
          `SELECT id, to_address, from_address, subject, otp_code, created_at, substr(text_content, 1, 150) as intro
           FROM emails
           WHERE to_address = ?
           ORDER BY created_at DESC
           LIMIT 50`
        ).bind(emailClean).all();

        const messages = (results || []).map((row) => ({
          id: row.id,
          accountId: row.to_address,
          from: { address: row.from_address, name: row.from_address },
          to: [{ address: row.to_address, name: row.to_address }],
          subject: row.subject || '(Tanpa Subjek)',
          intro: row.otp_code ? `Kode OTP: ${row.otp_code}` : (row.intro || row.subject),
          otp: row.otp_code || null,
          createdAt: row.created_at,
          hasAttachments: false,
          isSeen: false,
        }));

        return jsonResponse(messages);
      }

      // GET /code or /api/code (Fast OTP code polling for bot)
      if ((path === '/api/code' || path === '/code') && request.method === 'GET') {
        const email = url.searchParams.get('email');
        if (!email) {
          return jsonResponse({ status: 'error', message: 'Missing email parameter' }, 400);
        }

        const emailClean = email.toLowerCase().trim();
        const row = await env.DB.prepare(
          `SELECT otp_code, subject, created_at FROM emails
           WHERE to_address = ?
           ORDER BY created_at DESC
           LIMIT 1`
        ).bind(emailClean).first();

        if (row && row.otp_code) {
          return jsonResponse({
            status: 'found',
            code: row.otp_code,
            subject: row.subject,
            received_at: row.created_at,
          });
        }

        return jsonResponse({
          status: 'waiting',
          code: null,
        });
      }

      // GET /raw or /api/raw
      if ((path === '/api/raw' || path === '/raw') && request.method === 'GET') {
        const email = url.searchParams.get('email');
        if (!email) {
          return jsonResponse({ error: 'Missing email parameter' }, 400);
        }

        const emailClean = email.toLowerCase().trim();
        const row = await env.DB.prepare(
          `SELECT * FROM emails WHERE to_address = ? ORDER BY created_at DESC LIMIT 1`
        ).bind(emailClean).first();

        if (!row) {
          return jsonResponse({ status: 'waiting', raw: null, code: null });
        }

        return jsonResponse({
          status: 'found',
          id: row.id,
          from: row.from_address,
          subject: row.subject,
          raw: row.text_content,
          html: row.html_content,
          code: row.otp_code,
          received_at: row.created_at,
        });
      }

      return jsonResponse({ error: 'Endpoint not found' }, 404);
    } catch (err) {
      return jsonResponse({ error: err.message }, 500);
    }
  },
};
