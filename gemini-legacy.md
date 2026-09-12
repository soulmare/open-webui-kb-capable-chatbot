# Legacy Direct Gemini Connection

**Prerequisite:** Docker and Open WebUI already set up per the [README](README.md) (steps 1–2). This file covers the original, now-legacy direct Gemini connection — superseded by [litellm.gemini-3.5-flash-lite](README.md#3-litellm-setup) — kept here for reference. For the local Ollama stack, see [ollama.md](ollama.md).

## Architecture

```text
Open WebUI (Docker)
   │
   └── direct ──▶ generativelanguage.googleapis.com/v1beta/openai   (models/gemini-3.5-flash-lite, legacy function calling)
```

---

## Direct Gemini connection (legacy function calling)

`models/gemini-3.5-flash-lite`, via Google's OpenAI-compatible endpoint, silently ignores tools offered with `Function Calling: Native` — no tool call, no error, just a plain "I don't have internet access." That's why this connection is set to `Legacy`: Legacy forces Knowledge search and web search (and also image generation / code interpreter) to run automatically before generation, instead of leaving it up to the model to decide whether to call a search tool.

Per-model settings (`Admin Panel → Models → models/gemini-3.5-flash-lite`):

- **Capabilities → File Context**: gates whether Knowledge/file retrieval runs at all for that model. Defaults to ON, but check it explicitly — it was found switched OFF here during setup, which silently disabled KB search with no visible error.
- **Capabilities → Web Search**: independent of File Context — must be ON for that model to even offer the web search toggle in chat.
- **Advanced Params → Function Calling → Legacy**: the setting both features actually depend on.

In short:

| Goal | Required settings |
|---|---|
| KB search works | `File Context` ON + `Function Calling` → `Legacy` |
| Web search works | `Web Search` capability ON + `Function Calling` → `Legacy`, **and** the web search toggle turned on for that message in the chat UI (it's a per-message opt-in, unlike Knowledge which is always-on once attached) |

`File Context` has no effect on web search, and `Web Search` capability has no effect on KB search — they're independent switches. `Function Calling` is the one setting shared by both.

---

## RAG retrieval tuning (legacy function calling only)

In Open WebUI's source (`generate_queries()` in `middleware.py`), this query-generation step only runs when `Function Calling` is `Legacy`. In `Native` mode (the current litellm setup) the middleware skips it entirely and hands tools directly to the model, which composes its own search query — this template and `top_k` have no effect there.

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

All of this, plus the Ollama connection URL (see [ollama.md](ollama.md)) and API key creation being enabled, is applied in one step by [Import Config Backup](#import-config-backup) below.

---

## Import Config Backup

`config-backup.json` holds this instance's exported settings: the Ollama connection URL, API key creation being enabled, and the RAG retrieval-query tuning above.

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

There's no working export/import for these — Open WebUI's `/api/v1/models/export` only returns models with a `base_model_id` set, which excludes direct provider-model overrides like `models/gemini-3.5-flash-lite`. Back these up by re-applying the settings from [Direct Gemini connection](#direct-gemini-connection-legacy-function-calling) manually, under `Admin Panel → Models`.
