-- D1 purchases table — 결제 완료된 리포트 구매 기록
-- Apply via: wrangler d1 migrations apply m_log_db --remote
-- File name convention: migrations/0006_add_purchases.sql

CREATE TABLE IF NOT EXISTS purchases (
    id TEXT PRIMARY KEY,                                    -- pur_{timestamp}_{random}
    user_id TEXT,                                           -- 로그인 사용자 ID
    anonymous_id TEXT,                                      -- 비로그인 사용자 ID
    report_type TEXT NOT NULL,                               -- desire / ai / luck / comprehensive / dating_compatibility / dating_divorce / desire_deep
    fingerprint TEXT NOT NULL,                               -- 명식 fingerprint (getMyeongsikFingerprint)
    tx_id TEXT,                                              -- PortOne txId
    payment_id TEXT,                                         -- PortOne paymentId
    amount INTEGER NOT NULL DEFAULT 3800,                   -- 결제 금액
    status TEXT NOT NULL DEFAULT 'completed',                -- completed / refunded
    purchased_at TEXT NOT NULL,                              -- 구매 시각 ISO
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id, report_type, fingerprint);
CREATE INDEX IF NOT EXISTS idx_purchases_anon ON purchases(anonymous_id, report_type, fingerprint);
CREATE INDEX IF NOT EXISTS idx_purchases_payment ON purchases(payment_id);
