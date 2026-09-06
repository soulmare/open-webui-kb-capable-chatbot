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

Skip if Docker is already installed.

```bash
docker --version
docker run --rm hello-world
```

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

## 6. Connect Ollama to Open WebUI

In Open WebUI:

```text
Settings
→ Admin
→ Connections
→ Ollama
```

URL:

```text
http://host.docker.internal:11434
```

After connecting, Open WebUI should see the Ollama models.

---

## 7. Open WebUI management

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

`--restart no` means Open WebUI does not start automatically after a system reboot.

---

## 8. Update Open WebUI

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

## 9. Verification

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

## 10. RAG / Knowledge

Long-term knowledge can be managed using Markdown files through Open WebUI Knowledge/RAG:

```text
Git repository
      │
      ▼
Markdown files
      │
      ▼
Open WebUI Knowledge / RAG
      │
      ▼
Relevant chunks
      │
      ▼
Ollama → LLM
```

The Git repository is the **source of truth**, while the RAG index is a derived index.

A context window of at least **8192 tokens** is recommended for RAG.

### oikb

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

Example:

```text
oikb, version 0.4.0
```

Configure Open WebUI:

```bash
~/.venvs/oikb/bin/oikb config set url http://localhost:3000
```

In Open WebUI, first enable API key creation:

```text
Settings
→ Admin
→ Authentication
→ API Keys
→ Allow users to create API keys for programmatic access
```

Then create an API key:

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

The resulting workflow is:

```text
Git repository
      │
      ▼
Markdown files
      │
      │ oikb sync / watch
      ▼
Open WebUI Knowledge Base
      │
      ▼
RAG index
      │
      ▼
Gemma 3:4B
```

