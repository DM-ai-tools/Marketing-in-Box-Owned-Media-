# Claude Code capability guide — Marketing-in-a-Box

A reference for what's available in this environment (this project's `.claude/` config plus the
harness), how to reach for it, and worked examples. This is a working reference, not project
convention — the authoritative conventions live in `CLAUDE.md`.

---

## 1. The core tools (always available)

These are the primitives everything else is built from. Prefer the dedicated tool over Bash/PowerShell
whenever one fits — it's faster for you to review and cheaper in tokens.

| Tool | Use for | Don't use for |
| --- | --- | --- |
| `Read` | Reading a known file (text, image, PDF, .ipynb) | Directory listing — use `Glob` |
| `Edit` | Targeted string replacement in an existing file | New files — use `Write` |
| `Write` | Creating a new file, or a full-file rewrite | Small tweaks — use `Edit` (cheaper diff) |
| `Glob` | Find files by name/path pattern (`**/*.tsx`) | Content search — use `Grep` |
| `Grep` | Search file *contents* by regex, with glob/type filters | Open-ended "where is X" across an unfamiliar area — use `Explore` agent instead once it'd take 3+ queries |
| `Bash` | POSIX/Git Bash shell commands, git, npm | File read/write/search — use the dedicated tools above |
| `PowerShell` | Windows-native shell (PS 5.1 syntax, no `&&`/`||`) | Same caveat — dedicated tools first |

**This repo is on Windows.** `Bash` here is Git Bash (POSIX sh) — real `/` paths, no `%VAR%`.
`PowerShell` is Windows PowerShell 5.1 — no `&&`, no ternary, `$env:VAR` for env vars. Pick whichever
syntax the command actually needs; both are wired to the same working directory.

**Example — find and fix a bug:**
```
Grep(pattern="def scrape_page", path="application/backend/app/services/scraper.py", output_mode="content")
Read(file_path="application/backend/app/services/scraper.py")
Edit(file_path=..., old_string=..., new_string=...)
Bash(command="cd application/backend && pytest tests/test_scraper.py -q")
```

---

## 2. Agents (the `Agent` tool)

Spawns a subagent with its own context window and a restricted toolset. Use it to (a) parallelize
independent work, or (b) keep a large search/investigation out of your own context.

**Don't use it when the target is already known** — a direct `Read`/`Grep` is faster and cheaper.
Reserve it for open-ended questions spanning the codebase, or tasks matching a listed agent's
specialty.

### Agents actually configured in this repo (`.claude/agents/`)

| Agent | When to reach for it |
| --- | --- |
| `backend-specialist` | FastAPI routers/services, SQLAlchemy/Alembic models, Celery tasks in `application/backend` |
| `frontend-specialist` | React/TS components, state, styling in `application/frontend` |
| `database-architect` | Schema changes, migrations, indexing, query plans |
| `debugger` | A specific bug/crash/stack trace that needs root-causing |
| `test-engineer` | Writing/fixing pytest or frontend test coverage |
| `security-auditor` | Auth, secrets handling, OWASP-type review (e.g. touching `context_dev.py`'s key handling) |
| `devops-engineer` | Deploy, CI, process management — **high-risk, confirm before acting** |
| `performance-optimizer` | Bundle size, slow endpoints, profiling |
| `seo-specialist` | On-page SEO changes if this app ever touches its own marketing surface |
| `code-archaeologist` | Understanding an undocumented corner before refactoring it |
| `qa-automation-engineer` | Playwright/e2e setup |
| `documentation-writer` | Only when explicitly asked for docs — don't self-invoke |
| `product-manager` / `product-owner` / `project-planner` | Turning a vague ask into scoped requirements/tasks |
| `orchestrator` | A task that genuinely needs several of the above combined |
| `mobile-developer`, `game-developer`, `penetration-tester` | Not relevant to this repo today — skip |

Plus generic ones from the harness:

| Agent | When to reach for it |
| --- | --- |
| `Explore` | Read-only, fast codebase search — "where is X defined", "which files reference Y". 3+ queries deep → delegate here instead of doing it yourself. |
| `general-purpose` | Multi-step research/execution that doesn't match a specialist |
| `Plan` | Design an implementation plan before writing code on a non-trivial change |

### Example — parallel independent investigation
```
Agent(description="Find DESIGN.md staleness callers", subagent_type="Explore",
      prompt="Search application/backend for every call site of _reuse_stored_design and
              DESIGN_CAPTURE_VERSION. Report file:line for each, and whether it reads or bumps
              the version. Search breadth: medium.")
Agent(description="Audit context_dev.py key handling", subagent_type="security-auditor",
      prompt="Review application/backend/app/services/context_dev.py for any path where
              CONTEXT_DEV_API_KEY could leak into logs, model context, or the frontend bundle.
              CLAUDE.md says the SDK reads it from env directly and nothing should pass it
              explicitly. Confirm that invariant holds; report violations with file:line.")
```
Send both in one message (no dependency between them) so they run concurrently.

### Example — sequential, dependent work
```
Agent(description="Design DESIGN_CAPTURE_VERSION bump plan", subagent_type="Plan",
      prompt="...", run_in_background=false)
# then, after reviewing the plan output:
Agent(description="Implement the version bump", subagent_type="backend-specialist",
      prompt="Following this plan: <paste>. Implement in app/services/design_md.py...")
```

---

## 3. Skills (the `Skill` tool)

A skill loads packaged instructions into the current turn (or runs as a background subagent,
depending on the skill). Invoke it when the task matches its one-line description — check the
`<system-reminder>` skill listing for the live set; it's long, project-scoped skills are marked
with a path prefix.

### Skills most relevant to this codebase

| Skill | When |
| --- | --- |
| `design-spec` | **Before writing any UI**, and any time you touch `DESIGN.md` generation (`app/services/design_md.py`) — it's literally the spec for that file's format |
| `python-patterns` | FastAPI/SQLAlchemy backend work |
| `frontend-design` / `frontend-architecture` | React/TS UI work — design taste vs. structural organization respectively |
| `nextjs-react-expert` | Only if this app moves to Next.js — currently plain Vite, skip |
| `powershell-windows` | Writing PowerShell scripts (this is a Windows dev box) |
| `bash-linux` | Bash scripts run via Git Bash |
| `testing-patterns` / `tdd-workflow` | Writing/structuring pytest or frontend tests |
| `code-review` (slash-style skill) | Reviewing a diff/PR for correctness bugs |
| `simplify` / `simplify-code` | Cleanup pass on over-engineered code |
| `systematic-debugging` | A gnarly bug that resists a quick fix |
| `verify-changes` | After writing code — prove it works by running it, not just eyeballing it |
| `security-review` | Security-sensitive changes (auth, the Context.dev key, secrets) |
| `mcp-builder` | If this project ever exposes its own MCP server |
| `database-design` | Alembic migrations, schema changes |
| `api-patterns` | New FastAPI route design (versioning, pagination, response shape) |
| `memory-system` | User says "remember this" / "don't forget" |
| `run` | User wants the app actually launched/screenshotted to confirm a change works |

### Example
```
Skill(skill="design-spec")
# now write/update DESIGN.md generation logic with the spec's rules loaded
```
```
Skill(skill="verify-changes")
# after implementing a fix, prove it: run the app/tests, don't just claim success
```

**Don't invoke skills speculatively.** If a skill's description doesn't clearly match, skip it —
loading irrelevant instructions crowds out useful context.

---

## 4. Workflow tool (multi-agent orchestration)

`Workflow` runs a JS script that fans out multiple agents deterministically (e.g. review N
dimensions in parallel, then verify each finding). **Opt-in only** — never call it unless the user
said "use a workflow" / "ultracode" / invoked a skill that calls it. It can spawn dozens of agents
and burn a lot of tokens. For anything else, use `Agent` directly or ask the user first.

---

## 5. MCP servers (external integrations)

Configured for this session; most need OAuth before their tools work. Check status if a request
needs one of these — don't assume, don't fabricate results.

| Server | What it's for | Status |
| --- | --- | --- |
| **Adspirer** | Real ad account management — Google/Meta/TikTok/LinkedIn/Amazon/ChatGPT Ads. Campaign creation, performance, audiences, budgets. | Connected — huge tool surface, use `search_tools` then `get_tool_schema` before calling anything, per its own instructions |
| **Apollo.io** | Lead gen, enrichment, sales sequences, CRM-ish contacts/deals | Connected |
| **Gmail**, **Microsoft 365** (Outlook/Teams/SharePoint) | Email/calendar/chat/file ops | Connected |
| **Google Drive** | File search/read/write in Drive | Connected |
| **Claude Docs** | Living collaborative docs (different from this file — see below) | Connected |
| **HiggsField AI** | Image/video/audio/3D generation, voice cloning, website builder | Connected |
| **Asana, Atlassian, Box, Canva, Figma, Gamma, HubSpot, Intercom, Linear, Notion, WordPress.com, monday.com** | Various | **Needs auth** — tell the user to authorize via claude.ai connector settings |
| **bigquery, hex, ahrefs, amplitude, klaviyo, similarweb, slack, supermetrics** | Data/marketing plugins | **Needs auth** via `claude mcp` / `/mcp` |
| **definite** (data plugin) | — | **Failed to connect** (endpoint not found) — tell user to fix/retry, don't assume unconfigured |

**When to reach for one:** only when the user's request is actually about that external system —
e.g. "check our Google Ads spend" → Adspirer, "find this lead's email" → Apollo, "post this to
Slack" → tell user Slack isn't authorized yet. Never invent account IDs, page IDs, or tool
arguments — resolve them through the server's own discovery tools first.

---

## 6. Artifact tool — sharing something outside the terminal

Publishes an HTML page (report, dashboard, deck-like doc) as a private, shareable link. Use when
the user (or someone they name) needs to *read or interact with* something outside this
conversation — not for code that belongs in the repo. Always run `action: "quickstart"` first for
a new artifact type (deck/doc/design), and load `artifact-design` before writing the HTML.

**Example** — user asks "write up the DESIGN.md staleness fix for the team":
```
Artifact(action="quickstart", intent="document")
# → follow its guidance, then write and publish the HTML
```

---

## 7. Other utility tools

| Tool | Use for |
| --- | --- |
| `AskUserQuestion` | Only when genuinely blocked on a decision only the user can make (auto mode biases toward *not* asking — make the reasonable call and proceed) |
| `ToolSearch` | Load schemas for deferred tools (e.g. `WebFetch`, `WebSearch`, `Monitor`, `SendMessage`) before calling them — they're listed by name only until fetched |
| `ScheduleWakeup` | Only inside a `/loop` dynamic-pacing session |
| `ReportFindings` | Only when explicit code-review instructions say to use it |
| `ListAgents` | See what subagents/teammates you can `SendMessage` to |

**Example — using a deferred tool:**
```
ToolSearch(query="select:WebFetch", max_results=1)
# now WebFetch has a full schema and is callable
WebFetch(url="https://docs.context.dev/api-reference/web-scraping/markdown.md", prompt="...")
```

---

## 8. Decision cheat-sheet

- **Know the exact file/symbol?** → `Read` / `Grep` / `Edit` directly. Don't delegate.
- **Need to find something across an unfamiliar area (3+ queries)?** → `Explore` agent.
- **Backend logic change?** → `backend-specialist` agent, or just do it directly if small; load
  `python-patterns` / `api-patterns` / `database-design` as needed.
- **Frontend/UI change?** → `frontend-specialist` agent; load `design-spec` first if it touches
  anything DESIGN.md-related, `frontend-design` for visual taste.
- **Bug hunt?** → `debugger` agent or `systematic-debugging` skill for a tricky one.
- **About to ship a change?** → `verify-changes` skill — run it, don't just inspect it.
- **Multiple independent lookups/audits?** → several `Agent` calls in **one message** (parallel).
- **User explicitly asked for multi-agent orchestration?** → `Workflow` tool. Otherwise never.
- **Need live ad-account or CRM data?** → the relevant MCP server, via its own discovery tools
  first (`search_tools`, `get_tool_schema` for Adspirer, etc).
- **Producing something for someone other than the user?** → `Artifact`, not a local file.
