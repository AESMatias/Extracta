# SDD decisions

| Date | Decision | Options considered | Why |
|------|----------|--------------------|-----|
| 2026-09-24 | Web framework: Flask + Jinja2 | FastAPI, Flask | The owner wants to learn Flask. |
| 2026-09-24 | Database: PostgreSQL on Supabase | Local Postgres container, Supabase | Managed database; removes a container from the 2 GB server. |
| 2026-09-24 | Dependency management: Poetry | pip + requirements.txt, Poetry, uv | Lockfile-based reproducible installs; owner's choice. |
| 2026-09-24 | LLM provider: Gemini (`google-genai`), default model `gemini-3.1-flash-lite`, switchable via `LLM_PROVIDER`/`LLM_MODEL` | OpenAI SDK, Gemini 2.5 Flash-Lite, Gemini 3.1 Flash-Lite, Gemini 3.5 Flash-Lite | Cheapest Flash model open to new projects ($0.25/$1.50 per 1M tokens); 2.5 models are restricted to prior users. 3.1 shuts down 2027-05-07, so the move to 3.5 Flash-Lite is one `.env` line. |
