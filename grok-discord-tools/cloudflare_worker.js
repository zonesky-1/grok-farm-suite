/**
 * Cloudflare Temp Mail Worker for Grok-Register & 9Router
 * 
 * CARA PAKAI:
 * 1. Buka Cloudflare Dashboard -> Workers & Pages -> Create application -> Create Worker.
 * 2. Hapus semua isi kode bawaan, lalu paste seluruh isi file ini.
 * 3. Ganti "domainanda.com" di baris MY_DOMAIN di bawah dengan domain Anda.
 * 4. Klik "Deploy".
 * 5. Masuk ke Domain Anda di Cloudflare -> Email Routing -> Routing Rules:
 *    Set Catch-all Rule -> Action: "Send to a Worker" -> Pilih Worker ini.
 */

const MY_DOMAIN = "domainanda.com"; // Ganti dengan nama domain Anda yang ada di Cloudflare

export default {
  // 1. Menangkap semua email masuk dari Cloudflare Email Routing
  async email(message, env, ctx) {
    const raw = await new Response(message.raw).text();
    const to = (message.to || "").toLowerCase().trim();
    const subject = message.headers.get("subject") || "";
    
    // Ekstrak kode OTP xAI otomatis (format: 6 digit atau XXX-XXX)
    const match = subject.match(/\b([A-Z0-9]{3}-[A-Z0-9]{3}|\d{6})\b/i) || raw.match(/\b([A-Z0-9]{3}-[A-Z0-9]{3}|\d{6})\b/i);
    const code = match ? match[0] : "";

    const mailItem = {
      id: "msg_" + Date.now(),
      address: to,
      to: [{ address: to }],
      subject: subject,
      text: raw,
      raw: raw,
      code: code,
      createdAt: new Date().toISOString()
    };

    // Simpan ke Cache internal Cloudflare (Otomatis & Cepat)
    const cacheUrl = `https://mail-cache.internal/mail/${encodeURIComponent(to)}`;
    const cacheResponse = new Response(JSON.stringify(mailItem), {
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "public, max-age=600"
      }
    });
    ctx.waitUntil(caches.default.put(cacheUrl, cacheResponse));

    // Simpan ke D1 Database jika Anda menambahkan binding DB
    if (env.DB) {
      try {
        await env.DB.prepare(
          "CREATE TABLE IF NOT EXISTS mails (id TEXT, address TEXT, subject TEXT, raw TEXT, code TEXT, created_at INTEGER)"
        ).run();
        await env.DB.prepare(
          "INSERT INTO mails (id, address, subject, raw, code, created_at) VALUES (?, ?, ?, ?, ?, ?)"
        ).bind(mailItem.id, to, subject, raw, code, Date.now()).run();
      } catch (e) {}
    }

    // Simpan ke KV jika Anda menambahkan binding MAIL_KV
    if (env.MAIL_KV) {
      try {
        await env.MAIL_KV.put(`mail:${to}`, JSON.stringify(mailItem), { expirationTtl: 600 });
      } catch (e) {}
    }
  },

  // 2. API Endpoint yang dipanggil oleh script Grok Auto Register
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Endpoint: Cek domain aktif
    if (url.pathname === "/api/domains") {
      return Response.json([{ domain: MY_DOMAIN, isVerified: true }]);
    }

    // Endpoint: Buat alamat email acak
    if (url.pathname === "/api/new_address" || url.pathname === "/api/accounts") {
      let reqDomain = MY_DOMAIN;
      try {
        const body = await request.json();
        if (body && body.domain) reqDomain = body.domain;
      } catch (e) {}
      
      const rand = Math.random().toString(36).substring(2, 10);
      const address = `${rand}@${reqDomain}`;
      return Response.json({
        address: address,
        jwt: address,
        token: address
      });
    }

    // Endpoint: Ambil pesan email & kode OTP masuk
    if (url.pathname === "/api/mails" || url.pathname === "/api/messages") {
      const auth = request.headers.get("authorization") || "";
      const email = auth.replace("Bearer ", "").trim().toLowerCase();
      
      let mail = null;

      // Cek Cache Cloudflare
      if (email) {
        const cacheUrl = `https://mail-cache.internal/mail/${encodeURIComponent(email)}`;
        const cached = await caches.default.match(cacheUrl);
        if (cached) {
          mail = await cached.json();
        }
      }

      // Cek D1 jika ada
      if (!mail && env.DB && email) {
        try {
          const row = await env.DB.prepare("SELECT * FROM mails WHERE address = ? ORDER BY created_at DESC LIMIT 1").bind(email).first();
          if (row) {
            mail = {
              id: row.id,
              address: row.address,
              to: [{ address: row.address }],
              subject: row.subject,
              text: row.raw,
              raw: row.raw,
              code: row.code
            };
          }
        } catch (e) {}
      }

      // Cek KV jika ada
      if (!mail && env.MAIL_KV && email) {
        try {
          mail = await env.MAIL_KV.get(`mail:${email}`, "json");
        } catch (e) {}
      }

      const results = mail ? [mail] : [];
      return Response.json({
        results: results,
        "hydra:member": results,
        data: results
      });
    }

    return Response.json({ status: "online", domain: MY_DOMAIN });
  }
};
