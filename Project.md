# MN-PA-Data-Extractor Project

## Overview
Streamlit app that extracts structured data from Minnesota residential purchase agreements using LLMs, with review/edit and export to CSV/JSON.

## Goals
- Reduce API costs by making GLM-5.2 (via OpenRouter) the default model.
- Keep Claude as fallback/option.
- Maintain or improve extraction quality.
- Easy to extend to other models later.
- Good UX for title production workflow.

## Current Architecture (as of June 28, 2026)
- Streamlit frontend
- Anthropic Claude backend
- Supabase for storage
- Schema-driven extraction

## Model Backend Plan (Pluggable)
- Default: Hosted GLM-5.2 via OpenRouter (cheaper, strong on long-context/structured tasks)
- Option: Claude (via dropdown)
- Future: Local lighter models or other providers

## Next Steps / Roadmap
- [ ] Add pluggable model backend (this PR)
- [ ] Test extraction quality with GLM-5.2
- [ ] UI model selector
- [ ] Batch processing
- [ ] Extraction history / audit log

## Decisions Log
- 2026-06-28: GLM-5.2 via OpenRouter as default (cost + performance balance)
