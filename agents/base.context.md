# Base Context for {PROJECT_NAME}

**This file contains PROJECT-SPECIFIC CONTEXT.**
For portable agent instructions, see `base.agent.md`.

## Project Purpose

<!-- Customize: What is this project? What are we working on? 1-3 sentences. -->

## Key Documents

| Need | Read |
|------|------|
| Project overview | `README.md` |
| Dashboard / status | `ops/dashboard.md` |
| Messages for you | `agents/state/inboxes/{your-type}.md` |
| Previous session handoff | `agents/state/sessions/{your-type}/*.md` |
| Working understanding | `me/working-understanding.md` |

## Directory Quick Reference

<!-- Customize: List your project's key directories -->

| Directory | Purpose |
|-----------|---------|
| `me/` | Principal's self-knowledge, stories, goals |
| `ops/` | Dashboard, tracking, operational files |
| `data/` | Actions, contacts, structured data |
| `agents/` | Agent system (bootup files, state, tools) |

## Workflow Commands

```bash
# Inbox management
uv run agents/tools/inbox.py read {role}
uv run agents/tools/inbox.py add {role} "title" --from {sender} --body "..."

# Session naming
uv run agents/tools/agent_name.py
```
