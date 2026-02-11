# Cloudflare Tunnel Setup

## Overview

The app is exposed via a Cloudflare Tunnel running as a systemd service. The tunnel creates an outbound-only connection to Cloudflare's edge — no inbound ports are open on the machine.

## Config

- Tunnel config: `/home/yorrick/.cloudflared/config.yml` (also copied to `/etc/cloudflared/config.yml` by the service installer)
- Credentials: `/home/yorrick/.cloudflared/<tunnel-id>.json`
- Certificate: `/home/yorrick/.cloudflared/cert.pem`

The ingress rule in `config.yml` routes `autopilot-voxstore.yorrick.app` to `http://localhost:8002` (the autopilot webhook server). A catch-all rule returns 404 for unmatched requests.

## Service management

```bash
# Check status
systemctl status cloudflared

# Restart
sudo systemctl restart cloudflared

# Logs
journalctl -u cloudflared -f
```

The service is enabled on boot (`systemctl enable cloudflared`).

## Changing the backend port

Edit `/etc/cloudflared/config.yml`, update the `service` field under ingress, then restart:

```bash
sudo systemctl restart cloudflared
```

## DNS

The hostname is routed via a CNAME record managed by Cloudflare. To update it:

```bash
cloudflared tunnel route dns <tunnel-name> <new-hostname>
```

## Security

The tunnel is outbound-only — no inbound ports needed.

### Zero Trust Access

Zero Trust Access is configured via the Cloudflare dashboard at https://one.dash.cloudflare.com → Access → Applications.

Path-based bypass requires **two separate Access applications** (Cloudflare doesn't support path selectors within a single policy):

**Application 1 — Webhook bypass (more specific, takes priority):**
1. Add application → Self-hosted
2. Name: `<app-name>-webhooks`
3. Domain: `<hostname>` + Path: `webhook`
4. Policy: Action = Bypass, Include = Everyone

**Application 2 — Protected app (catch-all):**
1. Add application → Self-hosted
2. Name: `<app-name>`
3. Domain: `<hostname>` (no path)
4. Policy: Action = Allow, Include = Emails = authorized email(s)

The more specific path match (Application 1) takes priority, so webhook requests pass through while everything else requires email OTP login.

### Rate limiting

Cloudflare WAF rate limiting rules apply to tunnel traffic. Configure via Dashboard → Security → WAF → Rate limiting rules.

E.g., limit `/webhook/*` to 30 requests per minute per IP to prevent abuse.

### Webhook signature verification

Even with the bypass, webhook endpoints should verify request signatures in the app:
- **GitHub**: verify `X-Hub-Signature-256` header using HMAC-SHA256 with the webhook secret
- **Sentry**: verify `Sentry-Hook-Signature` header using HMAC-SHA256 with the client secret. Sentry also supports an `X-Sentry-Token` header — a static secret configured in Sentry's webhook settings. Sentry recommends this over IP whitelisting.

### IP whitelisting (optional, extra layer)

Both GitHub and Sentry publish their outbound IP ranges. These can be added as an additional "Include = IP Ranges" rule on the webhook bypass Access application.

- **GitHub**: IPs available via `curl -s https://api.github.com/meta | jq '.hooks'`. These change periodically — monitor the API.
- **Sentry**: IPs listed at https://docs.sentry.io/security-legal-pii/security/ip-ranges/

IP whitelisting is the weakest layer since IPs change. Signature verification is the strongest guarantee.

### Security layers summary

| Layer | Protection |
|-------|-----------|
| Cloudflare WAF | Rate limiting on `/webhook/*` |
| Zero Trust Access | Email OTP for humans, bypass for `/webhook/*` |
| App level | Verify webhook signatures (GitHub: `X-Hub-Signature-256`, Sentry: `Sentry-Hook-Signature` / `X-Sentry-Token`) |
| IP whitelisting (optional) | Restrict webhook bypass to known GitHub/Sentry IPs |
