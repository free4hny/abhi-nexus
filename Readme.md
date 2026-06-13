# Abhi-Nexus MCP Server — Project Documentation

**Author:** Abhi  
**Built:** June 2026  
**Stack:** Python, FastMCP, Docker, Unraid, Ollama, VS Code

---

## What Is Abhi-Nexus?

Abhi-Nexus is a production-grade autonomous news intelligence system. It fetches articles from 8 tech sources every day, ranks them using AI, generates summaries in English and Hindi, and delivers a curated email digest at 8:15 AM — fully automatically, with zero human intervention.

It is engineered as a portfolio project that demonstrates real-world multi-agent architecture, production systems thinking, and cost-conscious data engineering.

---

## What Is MCP?

MCP (Model Context Protocol) is an open standard that gives LLMs the ability to interact with external systems in real time. Think of it as giving an AI hands — it can fetch data, trigger actions, and query systems beyond its training data.

Without MCP, an LLM can only think and talk. With MCP, it can act.

**Real-world analogy:** MCP is like a USB standard. Before MCP, every AI integration was a custom cable that only worked with one specific system. After MCP, it becomes a USB port — any compatible client can plug in and use it.

---

## What We Built

We exposed Abhi-Nexus as an MCP server — making the pipeline accessible to any MCP-compatible client (VS Code, Cursor, Open WebUI, or custom agents) without changing any existing agent code.

### Architecture

```
MCP Client (VS Code + Continue + Local LLM)
                    |
         MCP Protocol (SSE, port 7070)
                    |
         Abhi-Nexus MCP Server
         (mcp_server.py — FastMCP 2.0.0)
                    |
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
Fetch Agent    Rank Agent     Delivery Agent
(RSS feeds)   (GPT scoring)   (Email SMTP)
    ▼               ▼               ▼
raw_articles   ranked_articles   Email at
   .json           .json          8:15 AM
```

### Deployment Stack

| Component | Technology |
|---|---|
| Server hardware | Unraid NAS |
| Containerization | Docker + docker-compose |
| Process management | Supervisord |
| MCP framework | FastMCP 2.0.0 |
| Transport | SSE (Server-Sent Events) |
| MCP client | VS Code + Continue extension |
| Local LLM | Ollama (DeepSeek R1 14B, Llama 3) |
| Pipeline LLM | OpenAI GPT-4o-mini |

---

## MCP Tools Exposed

| Tool | What It Does |
|---|---|
| `trigger_pipeline` | Manually run the full Fetch → Rank → Email pipeline |
| `get_articles` | Fetch ranked articles with filters (category, score, limit) |
| `get_top_articles` | Quick shortcut for top N highest-scored articles |
| `get_pipeline_status` | Health check — last run time, article counts, errors |
| `get_settings` | View current pipeline settings (passwords masked) |
| `update_setting` | Change a setting without restarting the container |
| `get_raw_articles` | See Bronze layer unranked articles |
| `scan_vulnerabilities` | Scan packages against CVE database + detect hardcoded secrets in code |
| `get_upgrade_recommendations` | List outdated packages, prioritising security-critical ones |

### MCP Resources

| Resource | URI | What It Exposes |
|---|---|---|
| Ranked articles | `abhinexus://articles/ranked` | Full ranked_articles.json as readable document |
| Pipeline status | `abhinexus://status` | Live pipeline health as readable document |

---

## Security Scanning Tools

Two security tools were added to the MCP server using `pip-audit` — the same CVE database used by Snyk and Dependabot.

### scan_vulnerabilities

Runs three real checks:

- **Dependency CVE scan** — checks every installed package against the NVD (National Vulnerability Database)
- **Secret detection** — scans all `.py` and `.yml` files for patterns matching OpenAI keys, GitHub tokens, AWS keys, hardcoded passwords
- **Summary report** — overall status: CLEAN or CRITICAL, with specific fix recommendations

Usage from VS Code Continue chat:
```
Scan Abhi-Nexus for vulnerabilities
Check for hardcoded secrets in the code
Run a full security audit
```

### get_upgrade_recommendations

Lists all outdated packages with current vs latest version. Flags security-critical packages (fastapi, cryptography, openai, requests etc.) with HIGH priority above normal packages.

### Installation

```bash
docker exec abhi-nexus pip install pip-audit
```

Add to `requirements.txt`:
```
pip-audit
```

---

## File Structure Added

```
z:/abhi-nexus/
└── mcp_server.py          ← New: MCP server exposing all 9 tools and 2 resources
```

### Changes to Existing Files

| File | Change | Reason |
|---|---|---|
| `requirements.txt` | Added `fastmcp==2.0.0`, `pip-audit`, upgraded `openai==1.56.0`, `pydantic==2.13.4`, `uvicorn==0.49.0` | Dependency resolution + security scanning |
| `supervisord.conf` | Added `[program:mcp]` block | Auto-start MCP server with container |
| `docker-compose.yml` | Added port `7070:7070`, moved secrets to env vars | Expose MCP server, remove hardcoded secrets |
| `Dockerfile` | Added `EXPOSE 7070` | Document exposed port |
| `agents/rank_agent.py` | `max_tokens` 1500 → 6000, summary prompt shortened to 1 sentence | Fix JSON truncation bug |
| `agents/fetch_agent.py` | Added Unicode stripping in `clean_text()` | Remove garbage characters from Stack Overflow RSS |

---

## Bugs Fixed During Build

Three pre-existing bugs were discovered and fixed during the MCP integration:

### Bug 1 — OpenAI proxies Error
**Symptom:** `Client.__init__() got an unexpected keyword argument 'proxies'`  
**Cause:** `openai==1.30.0` was too old, incompatible with newer httpx  
**Fix:** Upgraded to `openai==1.56.0`

### Bug 2 — JSON Truncation in Rank Agent
**Symptom:** `Unterminated string` parse errors, all articles falling back to score 0  
**Cause:** `max_tokens=1500` was too low — GPT response cut off mid-JSON  
**Fix:** Increased to `max_tokens=6000`, shortened summary prompt to 1 sentence

### Bug 3 — Unicode Garbage Characters
**Symptom:** Stack Overflow articles had invisible Unicode characters (`\u200b`, `\ufeff` etc.) inflating token count  
**Cause:** Stack Overflow RSS feed embeds tracking/watermark characters in content  
**Fix:** Added character filter in `fetch_agent.py` `clean_text()` function

---

## How to Connect

### VS Code (Continue Extension)

Add to `~/.continue/config.yaml`:

```yaml
name: Abhi-Nexus Config
version: 1.0.0
schema: v1

models:
  - name: DeepSeek 14B
    provider: ollama
    model: deepseek-r1:14b
    apiBase: http://localhost:11434

mcpServers:
  - name: abhi-nexus
    url: http://192.168.4.46:7070/sse
```

### Cursor IDE

Add to Cursor MCP settings:

```json
{
  "mcpServers": {
    "abhi-nexus": {
      "url": "http://192.168.4.46:7070/sse"
    }
  }
}
```

### Verify Server is Running

```bash
curl http://192.168.4.46:7070/sse
```

Expected response:
```
event: endpoint
data: /messages/?session_id=...
: ping - 2026-06-13 ...
```

---

## Adding New Tools

Adding a new MCP tool is one decorated function:

```python
@mcp.tool()
def my_new_tool(param: str = "default") -> dict:
    """Description of what this tool does."""
    # your logic here
    return {"result": "..."}
```

FastMCP automatically generates the schema, validates inputs, and registers the tool. No other changes needed.

---

## Interview Talking Points

**What you built:**
> "I exposed a multi-agent autonomous news pipeline as an MCP server running on self-hosted Docker on Unraid. Any MCP-compatible client — VS Code, Cursor, or a custom agent — can now trigger the pipeline, query ranked articles, monitor health, and run security audits in real time. The LLM stays local using Ollama, so there is zero cloud dependency for the AI layer."

**Why MCP over function calling:**
> "Function calling is per-model and per-request — you define tools inline for one specific app. MCP is transport-agnostic and model-agnostic. I build the server once and any MCP client can use it forever without rewriting the integration."

**On security scanning:**
> "I added two security tools to the MCP server — one that runs pip-audit against the NVD CVE database to detect vulnerable packages, and one that scans the codebase for accidentally hardcoded secrets. The LLM can now ask 'is this system secure?' and get a real answer backed by real data."

**Architecture decision — why not rewrite agents as MCP servers:**
> "The agents already work. MCP is an additive interface layer, not a replacement. I wrapped the existing FastAPI surface and Python functions as MCP tools without touching agent logic. This is the same pattern Meta uses — expose capabilities through a standard interface without disrupting the underlying system."

**Cost discipline:**
> "The pipeline runs at $2/month. Batching 10 articles per API call instead of 1 saves 75% on GPT costs. The MCP server itself is free — open protocol, self-hosted, no per-query charges."

---

## What MCP Is Not

| Misconception | Reality |
|---|---|
| MCP reads and understands your data like RAG | MCP is a messenger — it fetches or triggers, the LLM does the understanding |
| MCP requires Claude or Anthropic products | MCP is an open standard — works with any LLM and any compatible client |
| MCP replaces your existing API | MCP wraps your existing API — nothing gets replaced |
| Local LLMs work well for MCP tool calling | Small local models (under 30B) tend to hallucinate tool responses — larger models or cloud LLMs are more reliable |

---

## Next Steps

- Upgrade to FastMCP 3.x for Streamable HTTP transport (replaces SSE)
- Add authentication layer to MCP server (API key header)
- Build a second agent that calls Abhi-Nexus as a tool in a larger workflow
- Add deep research tool — top 3 articles → web search → enriched summary
- Schedule automated weekly security scans via the MCP trigger
