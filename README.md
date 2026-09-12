# Ollama + Open WebUI

Local LLM stack for Linux/Kubuntu:

* Docker
* Ollama
* Gemma 3:4B
* Open WebUI
* oikb for Knowledge Base synchronization

Architecture:

```text
Browser
   │
   ▼
Open WebUI (Docker)
   │
   │ host.docker.internal:11434
   ▼
Ollama (Linux host)
   │
   ▼
Gemma 3:4B
```

Gemini is wired in twice on purpose — see [Gemini via LiteLLM](#gemini-via-litellm-native-tool-calling):

```text
Open WebUI (Docker)
   │
   ├── direct ──▶ generativelanguage.googleapis.com/v1beta/openai   (models/gemini-3.5-flash-lite, legacy function calling)
   │
   └── webui-litellm-net (internal Docker network, no published port)
                  ▼
              LiteLLM (Docker)
                  │ gemini/gemini-3.5-flash-lite (native Gemini API)
                  ▼
              generativelanguage.googleapis.com
```

## 1. Docker

Docker is required. Install it following the official docs: https://docs.docker.com/engine/install/

---

## 2. Ollama

Install:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Check:

```bash
ollama --version
systemctl status ollama
```

Ollama should run as a systemd service.

---

## 3. Download a model

For example, Gemma 3:4B:

```bash
ollama pull gemma3:4b
```

Check:

```bash
ollama list
```

Optionally test:

```bash
ollama run gemma3:4b
```

Exit:

```text
/bye
```

---

## 4. Configure Ollama for Docker

By default, Ollama may listen only on `127.0.0.1`, preventing the Open WebUI container from connecting to it.

Create a systemd override:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d

sudo tee /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
```

Apply the changes:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Check:

```bash
ss -lntp | grep 11434
```

Expected:

```text
LISTEN ... *:11434 ... *:*
```

**Warning:** this exposes the Ollama API on all network interfaces, not just to Docker. Anyone on the same network can reach port 11434 with no authentication — make sure it's not reachable outside a trusted LAN, or restrict it with a firewall.

---

## 5. Open WebUI

Run via Docker Compose (`docker-compose.yml` in the repo root — also brings up `litellm`, see [Gemini via LiteLLM](#gemini-via-litellm-native-tool-calling)):

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

## 6. Import Config Backup

`config-backup.json` (see [Backup and restore](#backup-and-restore)) holds this instance's exported settings, including the Ollama connection URL, API key creation being enabled, and the RAG retrieval-query tuning described further down this README. Importing it in one step wires up all of that instead of setting each one by hand:

```text
Admin Panel
→ Settings
→ Database
→ Import Config
→ select config-backup.json
```

After importing, Open WebUI should see the Ollama models.

**Warning:** this file contains the Gemini API key in plaintext (`openai.api_keys` is part of the exported config). Treat it like a credential — don't commit it, don't share it. It's already excluded via `.gitignore`.

---

## 7. Verification

Ollama:

```bash
systemctl status ollama
```

Models:

```bash
ollama list
```

Ollama API:

```bash
curl http://127.0.0.1:11434/api/tags
```

Open WebUI:

```bash
docker ps
```

Docker → Ollama:

```bash
docker exec open-webui curl http://host.docker.internal:11434/api/tags
```

Web UI:

```text
http://localhost:3000
```

---

## Maintenance

### Open WebUI management

Start/stop/restart (both services):

```bash
docker compose up -d
docker compose stop
docker compose restart
```

Logs:

```bash
docker compose logs -f open-webui
```

### Update Open WebUI

```bash
docker compose pull open-webui
docker compose up -d open-webui
```

The `open-webui` volume is external and untouched by this, so data is not lost.

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

API key creation is already enabled via the [config import](#6-import-config-backup) above. Create an API key:

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

## RAG retrieval tuning

`Retrieval Query Generation` (Admin Panel → Settings → Interface → Task Model) is ON, with a custom `Query Generation Prompt Template` instead of the built-in default:

```text
### Task:
Rewrite the user's latest message into a single, self-contained search query for a personal knowledge base, resolving any pronouns or references ("it", "they", "both", "that one") using the chat history so the query makes sense on its own, with no prior context.

### Rules:
- Always produce exactly one query. This is a lookup against a small personal knowledge base, not a decision about whether external search is worthwhile - never return an empty list.
- Include every specific entity, name, or attribute from the chat history that the latest message refers to.
- Do not add commentary or explanation.

### Output:
Strictly return JSON: { "queries": ["..."] }

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>
```

`rag.top_k` (Admin Panel → Settings → Documents) is raised from 6 to 10 — even a correctly rewritten query left some relevant entries just outside the old top-6 cutoff, and headroom matters more as the KB grows.

All three settings are applied by the [config import](#6-import-config-backup) above.

---

## Model capabilities for reliable KB & web search retrieval

Per-model, under `Admin Panel → Models → (select model)`, two settings control whether a model actually searches your data instead of just guessing:

- **Capabilities → File Context**: gates whether Knowledge/file retrieval runs at all for that model. Defaults to ON, but check it explicitly — it was found switched OFF here on `gemini-3.5-flash-lite` during setup, which silently disabled KB search with no visible error.
- **Capabilities → Web Search**: independent of File Context — must be ON for that model to even offer the web search toggle in chat.
- **Advanced Params → Function Calling → Legacy**: the setting both features actually depend on. It forces Knowledge search and web search (and also image generation / code interpreter) to run automatically before generation, instead of leaving it up to the model to decide whether to call a search tool. Left at the default (native/unset), the model can just answer directly — which, in testing here, it consistently did on personal questions even with a KB correctly attached, silently skipping the search.

In short:

| Goal | Required settings |
|---|---|
| KB search works | `File Context` ON + `Function Calling` → `Legacy`, on any model with a Knowledge collection attached |
| Web search works | `Web Search` capability ON + `Function Calling` → `Legacy`, **and** the web search toggle turned on for that message in the chat UI (it's a per-message opt-in, unlike Knowledge which is always-on once attached) |

`File Context` has no effect on web search, and `Web Search` capability has no effect on KB search — they're independent switches. `Function Calling` is the one setting shared by both.

---

## Gemini via LiteLLM (native tool calling)

`models/gemini-3.5-flash-lite`, via Google's OpenAI-compatible endpoint, silently ignores tools offered with `Function Calling: Native` — no tool call, no error, just a plain "I don't have internet access." That's why that model is set to `Legacy` (see [Model capabilities](#model-capabilities-for-reliable-kb--web-search-retrieval)): Legacy forces the search instead of letting the model decide.

Same prompt via Gemini's **native** API (`gemini/gemini-3.5-flash-lite` through LiteLLM, not the OpenAI-compat endpoint) returns a correct `tool_calls` response — so the compat layer is what's broken, not the model.

Fix: run [LiteLLM](https://github.com/BerriAI/litellm) as a local proxy on Gemini's native API, added as a second, separate Open WebUI connection. `models/gemini-3.5-flash-lite` (direct, Legacy) stays untouched; `litellm.gemini-3.5-flash-lite` (native, agentic) is new — both selectable side by side.

### Setup

Managed by the same `docker-compose.yml` as Open WebUI (`docker compose up -d` brings up both). Relevant bits:

* `litellm/config.yaml` — model mapping, tracked in git (no secrets in it).
* `litellm/.env` — `GEMINI_API_KEY` (same key already used by the direct connection) and a generated `LITELLM_MASTER_KEY`. Gitignored, `chmod 600`, referenced via `env_file` in compose.
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

### Verified end-to-end

"get the latest news from NASA" on `litellm.gemini-3.5-flash-lite`, Web Search toggle on: 4 `search_web` calls, 7 round trips through `litellm` logs, final answer grounded with 11 cited sources.

**Gotcha:** the Web Search toggle is per-message — the model capability alone doesn't add `search_web` to the tool list. Without it, only always-on tools (`query_knowledge_files`, `search_notes`, ...) are offered, which the model correctly ignores for a news question.

### Maintenance

Logs:

```bash
docker compose logs -f litellm
```

Restart after editing `litellm/config.yaml` or `litellm/.env`:

```bash
docker compose up -d --force-recreate litellm
```

Independent of the direct connection — stopping `litellm` doesn't affect `models/gemini-3.5-flash-lite`.

---

## Backup and restore

### General settings

Export/import works via the UI:

```text
Admin Panel
→ Settings
→ Database
→ Export Config / Import Config
```

This covers RAG defaults, task settings, connection URLs, and the Ollama/API-key/retrieval-tuning settings referenced above. It also contains the Gemini API key in plaintext — don't commit or share the exported file.

### Per-model settings (Capabilities, Function Calling, Knowledge)

There's no working export/import for these — Open WebUI's `/api/v1/models/export` only returns models with a `base_model_id` set, which excludes direct provider-model overrides like `models/gemini-3.5-flash-lite`. Back these up by re-applying the settings from [Model capabilities for reliable KB & web search retrieval](#model-capabilities-for-reliable-kb--web-search-retrieval) manually, per model, under `Admin Panel → Models`.
