# Meta Context for {PROJECT_NAME}

**Project-specific facts for agent system work.**

For portable meta instructions, see `meta.agent.md`.
For project-specific instructions, see `this.meta.agent.md`.

---

## Architecture Notes

<!-- Customize: How is the agent system set up for this project? -->

**Roles:** coach, desk, comms, meta

**File structure:**
- `agents/*.agent.md` -- Portable role instructions (don't project-customize)
- `agents/this.*.agent.md` -- Project-specific role instructions
- `agents/*.context.md` -- Project-specific facts
- `agents/principles/` -- Methodology files (portable)
- `agents/state/` -- Runtime state (inboxes, sessions, working files)
- `agents/tools/` -- Shared tooling (inbox.py, agent_name.py)

## Improvement Log

<!-- Customize: Track changes made to the agent system -->
<!-- Format: date, what changed, why, requested by whom -->
