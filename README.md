# MN Purchase Agreement Extractor

Upload a Minnesota residential purchase agreement PDF → Claude extracts structured fields → review/edit → export CSV or JSON for title production software.

## Quick Start

```bash
# 1. Install dependencies
pip install streamlit anthropic pandas

# 2. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run locally
streamlit run app.py
```

## Files

| File | Purpose |
|---|---|
| `extraction_schema.json` | JSON Schema defining every field — use this to validate outputs and as a reference when mapping to your title software |
| `extraction_prompt.py` | The system prompt sent to Claude on every extraction, plus a standalone usage example |
| `app.py` | Streamlit app — upload, extract, review/edit, export |

## Deployment for 10 Users

**Option A: Streamlit Community Cloud (free)**
1. Push these files to a GitHub repo
2. Go to share.streamlit.io → deploy from that repo
3. Add `ANTHROPIC_API_KEY` in the app's Secrets settings
4. Share the URL with your team

**Option B: Small VPS (more control)**
1. Spin up a $5-10/mo VPS (DigitalOcean, Linode, etc.)
2. Install Python, clone the repo, run with `streamlit run app.py --server.port 80`
3. Put behind Cloudflare for HTTPS + optional access control

## Cost Estimate

Claude API usage for purchase agreement extraction runs roughly:
- ~10-30K input tokens per agreement (depending on page count / addenda)
- ~1-2K output tokens per extraction
- At Sonnet pricing, roughly **$0.05-0.15 per agreement**
- 10 users × 10 agreements/day = ~$5-15/day

## Next Steps

- [ ] Test against 5-10 real agreements covering your common variations
- [ ] Map the CSV columns to your title software's import format
- [ ] Add basic auth (Streamlit secrets or Cloudflare Access)
- [ ] Add a batch upload mode for processing multiple agreements
- [ ] Add extraction history / audit log (append to a shared CSV or database)
