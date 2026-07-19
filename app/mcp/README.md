# MCP Server

This package exposes Job Search Copilot as an MCP server over stdio, using the official
Python MCP SDK. You can drive it directly from Claude Desktop or Claude Code instead of
the REST API or a browser. Every tool call goes through the same `app/services/*` layer
the FastAPI routes use, against the same database.

```
app/mcp/
├── handlers.py   # one async function per tool — plain, directly testable, no MCP types
└── server.py     # FastMCP instance + @mcp.tool() wrappers (session handling, error trapping)
```

## Requirement: a local Postgres instance must be running

Stdio is the transport MCP clients are built around: Claude spawns a fresh server
process for the session and closes it when done — there's no persistent listener.
Claude Desktop/Code spawns the `app.mcp.server` process directly via `uv run`, so all
you need is dependencies installed (`uv sync`) and `DATABASE_URL` pointing at a running
Postgres instance (see the repo's [Quickstart](../../README.md#quickstart)).


## Tools exposed

| Tool | Description |
|---|---|
| `search_jobs(query?, location?, status?)` | Search jobs already saved in the database. |
| `add_job(url, title, company, ...)` | Save a job posting you found. |
| `get_pipeline()` | Summarize applications grouped by pipeline status. |
| `update_application(id, status, notes?)` | Move an application to a new pipeline stage. |
| `add_document(type, title, content)` | Store a CV, interview feedback, or research note. |
| `list_documents(type?)` | List stored documents, optionally filtered by type. |

Each tool has a full description and a typed input schema (see `server.py`) — that's
what the LLM reads to decide when and how to call it. Errors (bad input, not found,
DB failures) are caught and returned as a plain message; the LLM never sees a raw
exception.

## Use it from Claude Desktop in 2 minutes

1. Make sure dependencies are installed (`uv sync`) and `.env` points `DATABASE_URL` at
   your local Postgres instance.
2. Open Claude Desktop's config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
3. Add a `job-search-copilot` entry under `mcpServers`, using an absolute path to this
   repo:
   ```json
   {
     "mcpServers": {
       "job-search-copilot": {
         "command": "uv",
         "args": [
           "--directory", "/absolute/path/to/job-copilot",
           "run", "python", "-m", "app.mcp.server"
         ]
       }
     }
   }
   ```
4. Restart Claude Desktop. Start a new chat and ask something like *"What's in my job
   application pipeline?"* — Claude should call `get_pipeline` and show you the answer.

If Claude reports the tool is unavailable or a call fails, check that Postgres is
reachable and `DATABASE_URL` is set correctly.

## Use it from Claude Code

```bash
claude mcp add job-search-copilot -- uv --directory /absolute/path/to/job-copilot run python -m app.mcp.server
```
