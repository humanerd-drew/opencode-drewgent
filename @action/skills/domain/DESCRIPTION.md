---
title: Description
type: skill
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@action/skills/SKILL-INDEX]]"
---

space: outcome
type: document

Passive domain intelligence using only Python stdlib and public data sources.
Zero dependencies. Zero API keys. Works out of the box.

## Capabilities

- Subdomain discovery via crt.sh certificate transparency logs
- Live SSL/TLS certificate inspection (expiry, cipher, SANs, TLS version)
- WHOIS lookup — supports 100+ TLDs via direct TCP queries
- DNS records: A, AAAA, MX, NS, TXT, CNAME
- Domain availability check (DNS + WHOIS + SSL signals)
- Bulk multi-domain analysis in parallel (up to 20 domains)

## Data Sources

- crt.sh — Certificate Transparency logs
- WHOIS servers — Direct TCP to 100+ authoritative TLD servers  
- Google DNS-over-HTTPS — MX/NS/TXT/CNAME resolution
- System DNS — A/AAAA records

## Related
- [[@action/skills/SKILL-INDEX]]
