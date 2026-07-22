<div align="center">

<img src="assets/marquee-stop.svg" alt="STOP! HEY YOU! Are you looking for a new job?" width="100%">

<img src="assets/title-glitter.svg" alt="JOB SEARCH COPILOT" width="100%">

<img src="assets/new-badge.svg" alt="NEW!" width="70">&nbsp;&nbsp;<img src="assets/under-construction.svg" alt="Under construction" width="320">&nbsp;&nbsp;<img src="assets/new-badge.svg" alt="NEW!" width="70">

</div>

<img src="assets/divider-flames.svg" alt="" width="100%">

<div align="center">

# 🚨 STOP! 🚨

## 👀 HEY YOU! YES, YOU! 👀

### Are you looking for a new job?

Are you slowly losing your sanity because every single application asks for the<br>
**EXACT. SAME. INFORMATION.** over and over again?

Have you manually typed your address, email, phone number, LinkedIn, GitHub,<br>
favorite programming language, years of experience, and that one project you're proud of<br>
approximately **7,482 times** this week?

Do you have seventeen sticky notes scattered around your desk that say things like:

</div>

> 📝 *"Applied... maybe?"*
>
> 📝 *"Rejected? Ghosted? Both?"*
>
> 📝 *"Remember to follow up on Thursday."*
>
> 📝 *"Which company was 'Innovative Solutions Global Dynamic AI Cloud Enterprise Ltd.' again?"*

<div align="center">

## 🎺 WELL SUFFER NO MORE! 🎺

### Introducing...

# 🤖 THE JOB SEARCH COPILOT*

An AI-powered companion that takes the soul-crushing, mind-numbing,<br>
keyboard-destroying parts of job hunting and says:

## *"Don't worry, human. I got this."* 😎

✅ It keeps track of applications.<br>
✅ It remembers things.<br>
✅ It helps with the repetitive nonsense.<br>
✅ It lets you focus on what actually matters.<br>

<img src="assets/divider-flames.svg" alt="" width="100%">

## 💬 "But Marcin... what's the catch?" 💬

# THERE ISN'T ONE.

### It's...

<img src="assets/free-blink.svg" alt="FREE" width="260">

❌ Not *"free for 14 days."*<br>
❌ Not *"free until you accidentally click Premium."*<br>
❌ Not *"free if Mercury is in retrograde."*<br>

**Actually. Completely. Ridiculously. FREE.**

Just clone the repository. 💾<br>
Install it. 🔧<br>
Run it. 🏃<br>
Watch your new AI sidekick bully repetitive job applications into submission. 🥊

<img src="assets/divider-flames.svg" alt="" width="100%">

## ⭐⭐⭐⭐⭐ REAL CUSTOMER REVIEWS ⭐⭐⭐⭐⭐

<sup>(100% authentic, definitely not all written by the same person)</sup>

| Rating | Review | Verified Customer              |
|:---:|---|--------------------------------|
| ⭐⭐⭐⭐⭐ | *"Before this project I spent six hours filling out applications every day. Now I only spend six hours waiting for recruiters to reply."* | **Marcin P.**                  |
| ⭐⭐⭐⭐⭐ | *"I installed it and immediately got promoted. I wasn't even employed."* | **M. Płotka**                  |
| ⭐⭐⭐⭐⭐ | *"This repository made my coffee taste better."* | **M.P.king_of_the_seven_seas** |
| ⭐⭐⭐⭐⭐ | *"My keyboard sent me a thank-you letter because I no longer have to type my address 94 times a day."* | **M. Plotka**                  |
| ⭐⭐⭐⭐⭐ | *"I downloaded this repository and my neighbors started respecting me."* | **Marcin**                     |
| ⭐⭐⭐⭐⭐ | *"I wasn't even looking for a job. Now I have three."* | **M. P.**                      |
| ⭐⭐⭐⭐⭐ | *"This is the greatest technological breakthrough since Ctrl+C and Ctrl+V."* | **Mar. Plo.**                  |

<img src="assets/divider-flames.svg" alt="" width="100%">

## ⚠️ FINAL WARNING ⚠️

You have exactly **two choices.**

**Option A:**<br>
Continue copying your phone number into forms until the heat death of the universe. 💀

**Option B:**<br>
Clone this repository and let AI suffer instead. 🤖

*The choice seems suspiciously obvious.*

## 👉 GO AHEAD. 👈

🍴 **Fork it.**<br>
🚀 **Run it.**<br>
💼 **Get that job.**

Your future employed self is already wondering why you're still reading this<br>
instead of scrolling up and **smashing that Clone button.**

</div>

<br>

<img src="assets/end-of-ad.svg" alt="End of advertisement — technical documentation begins below" width="100%">

<br>

# Job Search Copilot

An AI-powered assistant for managing a job search: tracking roles, applications,
and the documents (CVs, interview feedback, company research) that go with them.

## Architecture

```
┌──────────────┐      ┌──────────────┐
│   FastAPI    │─────▶│  PostgreSQL  │
│   (app/)     │      │  + pgvector  │
└──────────────┘      └──────────────┘

 MCP server │ RAG pipeline │ A2A agents
```

- **MCP server** — expose job-search tools (search jobs, log an application,
  pull up interview notes) to Claude Desktop/Code.
- **RAG pipeline** — hybrid (pgvector + full-text) semantic search and cited,
  Claude-generated answers over your CVs, interview feedback, and company
  research. See [RAG Pipeline](#rag-pipeline) below.
- **A2A multi-agent layer** — cooperating agents for sourcing candidate roles,
  matching them against your profile, and drafting tailored application
  material.

### Quickstart guide will be here once the project will be ready

The API is now at http://localhost:8000, docs at http://localhost:8000/docs.

Docker/Compose files are still present in the repo but are not currently used —
the project runs directly against a local Postgres instance for now.

```bash
uv run pytest
```

### Linting, formatting, type-checking

```bash
uv run ruff check .
uv run ruff format .
uv run pyright
```

### Pre-commit

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## MCP Server

Job Search Copilot can be driven directly from Claude Desktop or Claude Code via an
MCP server that wraps the same service layer as the REST API. See
[`MCP README.md`](app/mcp/README.md) for the full tool list and a 2-minute Claude
Desktop setup guide.

## RAG Pipeline

Job Search Copilot answers questions and matches jobs against your own CVs, interview
feedback, and company research via hybrid (pgvector + full-text) retrieval and
Claude-generated, cited answers — exposed as `POST /rag/search`/`POST /rag/ask` and the
MCP tools `search_knowledge_base`/`match_job`. See [`RAG README.md`](app/rag/README.md)
for the architecture diagram, chunking strategy, embedding provider choice, and the
hybrid-search/RRF tradeoff.

<br>

<img src="assets/divider-flames.svg" alt="" width="100%">

<div align="center">

<img src="assets/hit-counter.svg" alt="Visitor counter: 007482" width="230">

<img src="assets/buttons-88x31.svg" alt="Made with robots | Free for LIFE! | Y2K compliant | Get me now" width="380">

📖 [**~*~ SiGn My GuEsTbOoK ~*~**](../../issues/new) 📖

<sub>© 2026 PanMartinez<br>

</div>
