# SDD decisions

| Date | Decision | Options considered | Why |
|------|----------|--------------------|-----|
| 2026-09-24 | Web framework: Flask + Jinja2 | FastAPI, Flask | The owner wants to learn Flask. |
| 2026-09-24 | Database: PostgreSQL on Supabase | Local Postgres container, Supabase | Managed database; removes a container from the 2 GB server. |
| 2026-09-24 | Dependency management: Poetry | pip + requirements.txt, Poetry, uv | Lockfile-based reproducible installs; owner's choice. |
