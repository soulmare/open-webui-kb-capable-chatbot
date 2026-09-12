# Ollama

**Prerequisite:** Docker and Open WebUI already set up per the [README](README.md) (steps 1–2) — this file adds the local Ollama + Gemma 3:4B stack on top of that. For the legacy direct Gemini connection, see [gemini-legacy.md](gemini-legacy.md).

## Architecture

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

---

## 1. Ollama

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

## 2. Download a model

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

## 3. Configure Ollama for Docker

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

## 4. Verification

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

Docker → Ollama:

```bash
docker exec open-webui curl http://host.docker.internal:11434/api/tags
```

---

## Restoring settings

The Ollama connection URL is included in the config backup covered in [gemini-legacy.md](gemini-legacy.md#import-config-backup).
