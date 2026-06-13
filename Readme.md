# Abhi-Nexus MCP Server

Exposes your pipeline as MCP tools so any client (Cursor, Open WebUI,
your own agent) can trigger it, query it, and monitor it.

---

## Step 1 — Install FastMCP

```bash
pip install fastmcp
```

---

## Step 2 — Copy mcp_server.py to your project root

Place it at:
```
z:/abhi-nexus/mcp_server.py
```

---

## Step 3 — Test it locally first

```bash
cd z:/abhi-nexus
python mcp_server.py
```

You should see:
```
Starting Abhi-Nexus MCP Server...
Data directory: z:/abhi-nexus/data
Tools exposed: trigger_pipeline, get_articles, ...
```

---

## Step 4 — Connect to Cursor

1. Open Cursor → Settings → MCP
2. Add new server with this config:

```json
{
  "mcpServers": {
    "abhi-nexus": {
      "command": "python",
      "args": ["z:/abhi-nexus/mcp_server.py"]
    }
  }
}
```

3. Restart Cursor
4. Open Cursor chat and ask:
   - "What is the pipeline status?"
   - "Show me top 3 articles from today"
   - "Trigger the pipeline now"

---

## Tools available

| Tool | What it does |
|---|---|
| `trigger_pipeline` | Manually run the full pipeline |
| `get_articles` | Get ranked articles with filters |
| `get_top_articles` | Quick shortcut for top N articles |
| `get_pipeline_status` | Health check — last run, counts, errors |
| `get_settings` | View current settings (passwords masked) |
| `update_setting` | Change a setting without restarting |
| `get_raw_articles` | See Bronze layer unranked articles |

---

## Adding new tools later (security scanning etc.)

Adding a new tool is as simple as adding a new function:

```python
@mcp.tool
def scan_for_vulnerabilities(target: str = "dependencies") -> dict:
    """Scan Abhi-Nexus for security vulnerabilities."""
    # your logic here
    return {"vulnerabilities": [...]}
```

That's it. The MCP server picks it up automatically.

---

## Transport options

- **stdio** (default): Works with Cursor, Claude Desktop. Run locally.
- **HTTP**: Run as a server so remote agents can call it.
  ```python
  mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
  ```