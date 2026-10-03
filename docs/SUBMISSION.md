# AML Challenge 2026 — Submission & Deployment Guide

This guide details the deployment, public HTTPS endpoint setup, smoke test validation, and leaderboard submission steps for **AxiomMem** on the Agent Memory Leaderboard (AML).

---

## 1. Hosting & Public HTTPS Endpoint

The AML platform calls your endpoints directly. You host two endpoints:
- `POST https://<your-domain>/add`
- `POST https://<your-domain>/search`

### Option A: Cloudflare Tunnel (Recommended — Free, Stable, Instant HTTPS)
1. Install `cloudflared`:
   ```bash
   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared.deb
   ```
2. Run a quick tunnel to your local AxiomMem port:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
3. Cloudflare will output a public HTTPS URL (e.g., `https://random-subdomain.trycloudflare.com`).

### Option B: Direct VM / Cloud Server (Caddy / Nginx)
If deploying on a VPS (AWS, GCP, DigitalOcean, Hetzner):
1. Run the Docker container:
   ```bash
   docker compose up -d
   ```
2. Point your DNS to the server IP and configure Caddy:
   ```caddy
   memory.yourdomain.com {
       reverse_proxy 127.0.0.1:8000
   }
   ```

---

## 2. Remote Reachability Verification

Before submitting to the AML platform, verify reachability from an external machine:

```bash
# Verify health
curl -f https://<your-public-url>/health

# Run remote smoke test
python scripts/smoke_test.py --base-url https://<your-public-url>
```

---

## 3. Submission Checklist

- [ ] **Division**: Select **Open-source Methods** (prize-eligible, ¥150,000 total pool).
- [ ] **Track**:
  - **Coding Memory** (Primary track)
  - **Textual Memory** (Secondary track)
- [ ] **Repository URL**: `https://github.com/ronisaguey-ux/aml-hackathon.git`
- [ ] **Git Commit Hash**: Freeze at tagged release (e.g. `v0.1.0`).
- [ ] **Endpoints**:
  - Add Endpoint: `https://<your-public-url>/add`
  - Search Endpoint: `https://<your-public-url>/search`
- [ ] **Model Configuration**:
  - Academic Open-Source track constraint: `text-embedding-v4` adapter / `gpt-4o-mini`.
- [ ] **Data Hygiene**: 30-day deletion policy active by default (`AXIOM_DATA_RETENTION_DAYS=30`).

---

## 4. Evaluation Strategy

1. **Trigger Smoke Test**:
   - The platform will issue automated test requests to verify schema echo, immediate visibility, and isolation.
   - Monitor logs via: `docker compose logs -f` or stdout.
2. **First Full Evaluation**:
   - Once smoke passes, initiate the first Full Evaluation run.
   - Results will record across columns A through H.
3. **Reserve Second Evaluation**:
   - Keep the second evaluation in reserve for the final submission window prior to the 2026-11-04 queue close.
