CREATE TABLE IF NOT EXISTS emails (
  id TEXT PRIMARY KEY,
  to_address TEXT NOT NULL,
  from_address TEXT NOT NULL,
  subject TEXT,
  text_content TEXT,
  html_content TEXT,
  otp_code TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_to_address ON emails(to_address);
CREATE INDEX IF NOT EXISTS idx_created_at ON emails(created_at);
