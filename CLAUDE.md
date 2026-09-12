# CLAUDE.md

Local Docker chat stack: Open WebUI + LiteLLM (proxies Gemini's native API for tool calling) + `oikb` for Knowledge Base sync. See README.md for full setup/usage.

## Stack

- `docker-compose.yml` — brings up `open-webui` (port 3000) and `litellm` (internal only, on `webui-litellm-net`).
- `litellm/config.yaml` — model mapping, tracked in git, no secrets.
- `litellm/.env` — `GEMINI_API_KEY` + `LITELLM_MASTER_KEY`, gitignored, `chmod 600`.
- `.env` (repo root) — `OIKB_BIN`, `KB_PATH`, `KB_ID` for `scripts/sync_kb.py`; gitignored, copy from `.env.template`.
- `scripts/sync_kb.py` — wraps `oikb sync`/`oikb watch`.

## Secrets — never commit or print

- `litellm/.env`, `.env`, `config-backup.json`, `models-backup.json` are gitignored (contain API keys in plaintext).
- The root `*.sh` quickstart scripts are gitignored too — some have a live Gemini key hardcoded; keep it that way, don't un-ignore them.

## Docs map

- `ollama.md` — alternative local-model stack (Ollama + Gemma), optional, not the default.
- `gemini-legacy.md` — first direct-Gemini connection (pre-LiteLLM), legacy.
- `engines-tests.md` — local test notes, gitignored, not published.

## Conventions

- Commit messages: short, imperative, no body unless needed.
- The `open-webui` Docker volume is `external: true` — don't remove/recreate it casually, it holds all chat/KB data.
