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

Run in Docker:

```bash
docker run -d \
  -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart no \
  ghcr.io/open-webui/open-webui:main
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

Start:

```bash
docker start open-webui
```

Stop:

```bash
docker stop open-webui
```

Restart:

```bash
docker restart open-webui
```

Logs:

```bash
docker logs open-webui
```

### Update Open WebUI

```bash
docker pull ghcr.io/open-webui/open-webui:main

docker stop open-webui
docker rm open-webui
```

Create the container again:

```bash
docker run -d \
  -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart no \
  ghcr.io/open-webui/open-webui:main
```

The `open-webui` volume is preserved, so Open WebUI data is not lost.

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

### One-time synchronization

Example:

```bash
~/.venvs/oikb/bin/oikb sync \
  /home/alex/Documents/work/AI-Chatbot/data/home-stuff-kb \
  --kb-id ad0507b3-42a3-45b7-9c46-1a24c74c992b
```

Check changes before synchronizing:

```bash
~/.venvs/oikb/bin/oikb sync \
  /home/alex/Documents/work/AI-Chatbot/data/home-stuff-kb \
  --kb-id ad0507b3-42a3-45b7-9c46-1a24c74c992b \
  --dry-run
```

`--dry-run` makes no changes and only shows which files would be added, modified, or deleted.

### Automatic synchronization

For automatic updates when files change, use `watch`:

```bash
~/.venvs/oikb/bin/oikb watch \
  /home/alex/Documents/work/AI-Chatbot/data/home-stuff-kb \
  --kb-id ad0507b3-42a3-45b7-9c46-1a24c74c992b
```

`watch` monitors the directory and automatically performs an incremental sync after changes.

---

## RAG retrieval tuning

Query rewriting for knowledge retrieval is disabled (`Retrieval Query Generation` OFF under Admin Panel → Settings → Interface → Task Model) — it improves retrieval accuracy for this KB. This is applied by the [config import](#6-import-config-backup) above.

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
