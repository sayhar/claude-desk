# Project Setup

You are setting up a coaching and operations framework for Claude Code. No agent roles exist yet — you're just Claude with these instructions. Work through each section with the user.

When done, you'll write the real `.claude/CLAUDE.md` and delete this file. The agent system bootstraps itself into existence through this process.

---

## 1. Git Setup

- [ ] **Rename origin to upstream** (keep for pulling framework updates):
  ```bash
  git remote rename origin upstream
  git remote set-url --push upstream DISABLE
  ```

Keeps `upstream` for pulling framework updates (`git fetch upstream && git merge upstream/main`) but blocks accidental pushes. Add your own `origin` later.

---

## 2. Project Identity

> **Ask the user:** What should we call this project?

Replace `{PROJECT_NAME}` with the answer in these files (line 1 of each):
- `agents/base.context.md`
- `agents/this.base.agent.md`
- `agents/this.coach.agent.md`
- `agents/this.desk.agent.md`
- `agents/this.comms.agent.md`
- `agents/this.meta.agent.md`
- `agents/coach.context.md`
- `agents/desk.context.md`
- `agents/comms.context.md`
- `agents/meta.context.md`

Also: `README.md` line 1 — `# Claude Desk` → `# {project name}`

---

## 3. Dependencies

- [ ] **Install uv** (if needed): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] **Test inbox**: `uv run agents/tools/inbox.py read coach` (should show empty)
- [ ] **Test name gen**: `uv run agents/tools/agent_name.py` (should output a name)

---

## 4. Project Context

This is a kickoff conversation. Take time here.

### 4.1 What & Who → `agents/base.context.md`

- What are we coaching/tracking? (1-2 sentences — what kind of work, decisions, or life areas)
- Who is the user? (Role, situation, what they need from this system)

### 4.2 Coaching Domain → `agents/coach.context.md`

- What topics, patterns, goals matter?
- What does the user want to understand about themselves?
- What recurring decisions or struggles come up?

### 4.3 Operations → `agents/desk.context.md`

- What are we tracking? (Projects, commitments, people, deadlines)
- What needs follow-up? (Recurring reviews, check-ins, maintenance)
- What does "nothing slipping through the cracks" look like?

### 4.4 Communications → `agents/comms.context.md`

- Who does the user communicate with? (Key people, relationships, dynamics)
- What channels? (Email, messages, docs, meetings)
- What's the user's voice like? (Tone, style, patterns to preserve)

---

## 5. Seed Files

Create initial data directories and files based on what you learned in step 4:

- [ ] `me/working-understanding.md` — Seed with what you learned about the user in step 4. This is the coach's evolving model of who the user is, what they care about, how they think.
- [ ] `me/verbatim.md` — Empty body, but include these rules at the top:
  ```markdown
  # Verbatim

  Things the user said in their own words. Do not paraphrase. Do not summarize.
  Add new entries at the top. Include date and context.

  ---
  ```
- [ ] `me/artifacts/` — Empty directory for user-created artifacts (drafts, frameworks, etc.)
- [ ] `data/people/` — Empty directory for people files
- [ ] `data/research/` — Empty directory for research notes
- [ ] `ops/dashboard.md` — Seed with initial status based on what you learned:
  ```markdown
  # Dashboard

  Last updated: {date}

  ## Active

  {items from the kickoff conversation}

  ## Waiting On

  ## Follow-ups

  ## Weekly Review

  Next review: {suggest a day}
  ```
- [ ] `ops/weekly-reviews/` — Empty directory for weekly review files

---

## 6. Finalize

Write `.claude/CLAUDE.md` with the contents below (replacing `{PROJECT_NAME}` with the actual project name), then delete this file (`SETUP.md`).

Tell the user: "Setup complete! Type `/exit` and run `claude` to start."

**Contents for `.claude/CLAUDE.md`:**

````
# {PROJECT_NAME}

**Base context (always loaded):**

@../agents/base.agent.md
@../agents/this.base.agent.md
@../agents/base.context.md

---

**Role routing (load based on user's first message):**

If user says "**coach**" or asks for coaching, self-understanding, decision support:
- Read `agents/coach.agent.md`
- Read `agents/this.coach.agent.md`
- Read `agents/coach.context.md`
- Read `agents/principles/coaching.md`

If user says "**desk**" or asks for status, tracking, follow-ups, weekly review:
- Read `agents/desk.agent.md`
- Read `agents/this.desk.agent.md`
- Read `agents/desk.context.md`

If user says "**comms**" or asks for messaging, drafting, conversation analysis:
- Read `agents/comms.agent.md`
- Read `agents/this.comms.agent.md`
- Read `agents/comms.context.md`
- Read `agents/principles/conversation-analysis.md`

If user says "**meta**" or asks about the agent system itself:
- Read `agents/meta.agent.md`
- Read `agents/this.meta.agent.md`
- Read `agents/meta.context.md`

**Default:** If unclear, assume coach.
````
