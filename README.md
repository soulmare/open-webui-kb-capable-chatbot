# Open WebUI chatbot with Knowledge Base search capability

Local chat stack for Linux/Kubuntu:

* Docker
* Open WebUI
* LiteLLM — proxies Gemini's native API so tool calling (Knowledge/web search) actually works
* oikb for Knowledge Base synchronization

> An earlier local-model stack (Ollama + Gemma 3:4B) also exists — see [ollama.md](ollama.md). So does a first, now-legacy direct Gemini connection — see [gemini-legacy.md](gemini-legacy.md).

## Architecture

```text
Browser
   │
   ▼
Open WebUI (Docker)
   │
   │ webui-litellm-net (internal Docker network, no published port)
   ▼
LiteLLM (Docker)
   │
   │ gemini/gemini-3.5-flash-lite (native Gemini API)
   ▼
generativelanguage.googleapis.com
```

## 1. Docker

Docker is required. Install it following the official docs: https://docs.docker.com/engine/install/

---

## 2. Open WebUI + LiteLLM

Run via Docker Compose (`docker-compose.yml` in the repo root — brings up both services):

```bash
docker compose up -d
```

Check:

```bash
docker ps
```

Open:

```text
http://localhost:3000
```

---

## 3. LiteLLM setup

Managed by the same `docker-compose.yml`. Relevant bits:

* `litellm/config.yaml` — model mapping, tracked in git (no secrets in it).
* `litellm/.env` — `GEMINI_API_KEY` and a generated `LITELLM_MASTER_KEY`. Gitignored, `chmod 600`, referenced via `env_file` in compose.
* `webui-litellm-net` — plain bridge network (not `--internal`, that would also block LiteLLM's outbound calls to Google), shared by both services in compose. Not LAN-exposed simply because `litellm` publishes no port to the host.

```yaml
# litellm/config.yaml
model_list:
  - model_name: gemini-3.5-flash-lite
    litellm_params:
      model: gemini/gemini-3.5-flash-lite
      api_key: os.environ/GEMINI_API_KEY

litellm_settings:
  drop_params: true
```

Open WebUI connection — `Admin Panel → Settings → Connections` (or the `/openai/config` API): base URL `http://litellm:4000/v1`, API key = `LITELLM_MASTER_KEY`, prefix ID `litellm` (model shows up as `litellm.gemini-3.5-flash-lite`). Model entry for it: `Function Calling: Native`, `Web Search` capability on.

---

## 4. Model capabilities for reliable KB & web search retrieval

Per-model, under `Admin Panel → Models → litellm.gemini-3.5-flash-lite`, two settings control whether the model actually searches your data instead of just guessing:

- **Capabilities → File Context**: gates whether Knowledge/file retrieval runs at all for this model. Check it's ON.
- **Capabilities → Web Search**: independent of File Context — must be ON for this model to even offer the web search toggle in chat.
- **Advanced Params → Function Calling → Native**: the model decides itself when to call `query_knowledge_files` / `search_web`, instead of them running automatically on every message.

`File Context` has no effect on web search, and `Web Search` capability has no effect on KB search — they're independent switches. The web search toggle itself is a per-message opt-in in the chat UI, unlike Knowledge which is always-on once a collection is attached.

### Verified end-to-end

"get the latest news from NASA" on `litellm.gemini-3.5-flash-lite`, Web Search toggle on: 4 `search_web` calls, 7 round trips through `litellm` logs, final answer grounded with 11 cited sources.

**Gotcha:** the Web Search toggle is per-message — the model capability alone doesn't add `search_web` to the tool list. Without it, only always-on tools (`query_knowledge_files`, `search_notes`, ...) are offered, which the model correctly ignores for a news question.

---

## Maintenance

Start/stop/restart (both services):

```bash
docker compose up -d
docker compose stop
docker compose restart
```

Logs:

```bash
docker compose logs -f open-webui
docker compose logs -f litellm
```

Update Open WebUI:

```bash
docker compose pull open-webui
docker compose up -d open-webui
```

The `open-webui` volume is external and untouched by this, so data is not lost.

Restart LiteLLM after editing `litellm/config.yaml` or `litellm/.env`:

```bash
docker compose up -d --force-recreate litellm
```

---

## Creating a Knowledge Base

Before syncing files into it (below), create the collection in Open WebUI:

```text
Workspace
→ Knowledge
→ Create
→ enter a name and description
```

Add content via **Add Content** (upload files, or **+ New Directory** for nested folders). Attach the collection to a model under `Workspace → Models → Edit`, or reference it ad hoc in chat with `#`.

**Finding the collection's ID** (needed as `KB_ID` below): Open WebUI's docs don't spell out where to find it — check the browser URL while the collection is open, or the `/api/v1/knowledge/...` requests in the browser's network tab if it's not obvious there.

---

## Knowledge Base sync (oikb)

`oikb` is a separate tool for synchronizing a local directory with an Open WebUI Knowledge Base. It performs incremental synchronization: new, modified, and deleted files are processed, while unchanged files are skipped.

Install it in a separate Python virtual environment:

```bash
python3 -m venv ~/.venvs/oikb
~/.venvs/oikb/bin/pip install oikb
```

Check:

```bash
~/.venvs/oikb/bin/oikb --version
```

Configure Open WebUI:

```bash
~/.venvs/oikb/bin/oikb config set url http://localhost:3000
```

Create an API key (enable API key creation first under `Admin Panel → Settings` if it's off):

```text
Settings
→ Account
→ API Keys
```

Store the key in the `oikb` configuration:

```bash
~/.venvs/oikb/bin/oikb config set token 'YOUR_API_KEY'
```

### `scripts/sync_kb.py`

Wraps `oikb sync`/`oikb watch`, reading `OIKB_BIN`, `KB_PATH`, and `KB_ID` from a `.env` file in the repo root instead of hardcoding them (`.env` is gitignored — copy `.env.template` to get started):

```bash
cp .env.template .env
# edit .env if your oikb path, KB directory, or KB ID differ from the defaults
```

One-time synchronization:

```bash
python3 scripts/sync_kb.py
```

Check changes before synchronizing:

```bash
python3 scripts/sync_kb.py --dry-run
```

`--dry-run` makes no changes and only shows which files would be added, modified, or deleted.

Watch the directory and sync automatically on changes:

```bash
python3 scripts/sync_kb.py --watch
```

---

## Backup and restore

### General settings

Open WebUI's `Admin Panel → Settings → Database → Export Config / Import Config` backs up connection URLs (including the litellm one) and task/RAG defaults. If exported, treat the file like a credential — it can contain API keys in plaintext — don't commit or share it.

### Per-model settings (Capabilities, Function Calling, Knowledge)

There's no working export/import for per-model settings such as Capabilities and Function Calling. Back these up by re-applying the settings from [Model capabilities](#4-model-capabilities-for-reliable-kb--web-search-retrieval) manually, under `Admin Panel → Models`.
