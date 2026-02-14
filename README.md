# Claude Desk

A coaching and operations framework for Claude Code. The "desk" counterpart to [claude-bicycle](https://github.com/sayhar/claude-bicycle), which handles code projects.

Four specialized agents: **coach** (patterns, decisions, self-understanding), **desk** (tracking, actions, follow-ups), **comms** (messaging, conversation analysis), **meta** (system maintenance).

---

## Why This Exists

You're three hours into a coaching session with Claude. It helps you see a pattern you've been blind to for years -- the way you avoid conflict by over-preparing, or the way you say yes to projects that don't serve your goals. You're making real progress. Then context resets.

New session. Claude has no idea what you discussed. No idea what pattern you uncovered, what decision you were wrestling with, what you said in your own words. So you start building files. A "working understanding" of yourself. Notes on recurring patterns. A dashboard of things you're tracking. You tell Claude to remember things.

The files get more structured. You split "things about me" from "things I'm tracking" from "messages I need to draft." You realize the coaching work is different from the operational work is different from the communication work. Each needs its own mindset. You want a coach that remembers your patterns across sessions. A desk that tracks your commitments and nudges you when things slip. A comms agent that knows your voice and can help you draft difficult messages.

This repo is what that became. A desk for Claude Code -- not for writing software, but for the rest of your work. Coaching, operations, communications, and the self-understanding that ties them together.

---

## What You Get

You close your laptop, come back three days later, and Claude offers to continue "calm-river: exploring the conflict avoidance pattern" -- already knowing what you discussed, what you realized, what felt true and what didn't. No re-explaining.

Your working understanding of yourself grows across sessions. The coach notices when a new situation rhymes with an old pattern. "This looks like the same dynamic you described with your previous manager -- the one where you over-prepare to avoid feeling exposed." It checks because it has the history.

The desk tracks what you're committed to. Weekly reviews surface what slipped. Follow-ups don't get lost. You stop carrying everything in your head.

The comms agent knows your voice. When you need to write a difficult message, it drafts in your style -- not generic AI style. It can analyze a conversation and help you see the moves being made. "They're framing this as a question but it's really a request. Here's how you might respond."

Three weeks in, you ask about a decision you're facing. The coach checks your working understanding. "Last time you faced something like this, you said you wished you'd trusted your gut instead of optimizing for consensus." It remembers because you built the system to remember.

---

## Quick Start

```bash
git clone https://github.com/sayhar/claude-desk my-desk
cd my-desk
claude
```

Say "meta" -- it walks you through setup.

Or work through `SETUP.md` manually.

---

## What's In The Box

```
agents/
  *.agent.md           # Role definitions (portable)
  this.*.agent.md      # Your project's instructions
  *.context.md         # Your project's facts
  principles/          # Coaching methodology, conversation analysis

  state/
    sessions/          # Session continuity
    inboxes/           # Agent coordination

  tools/
    inbox.py           # Coordination CLI
    agent_name.py      # Session name generator

me/
  working-understanding.md   # Evolving model of who you are
  verbatim.md                # Things you said, in your words
  artifacts/                 # Drafts, frameworks, things you've created

data/
  people/              # People files
  research/            # Research notes

ops/
  dashboard.md         # What's active, waiting, needs follow-up
  weekly-reviews/      # Weekly review history

hooks/                 # Guardrails
PLAN.md                # Roadmap and current status
```

---

### Roles

Say a word, load a mindset.

**coach** -- Understand yourself. Surface patterns, support decisions, build self-knowledge across sessions. Maintains your working understanding and notices when situations rhyme with past experiences.

**desk** -- Track everything. Dashboard, follow-ups, weekly reviews, commitments. The operational layer that makes sure nothing slips through the cracks. Handles the invisible maintenance of your life and work.

**comms** -- Communicate clearly. Draft messages in your voice, analyze conversations, prepare for difficult discussions. Knows your style and the people you interact with.

**meta** -- Modify the system itself. Update agent files, fix patterns, add new capabilities. The agent that maintains the agents.

Each role loads its own files:
- `{role}.agent.md` -- portable, bring to any project
- `this.{role}.agent.md` -- instructions for THIS project
- `{role}.context.md` -- facts about THIS project
- `principles/*.md` -- shared methodology

---

### Sessions

Each work thread gets a name like "calm-river" and a file:

```markdown
# Coach Session: calm-river

## TL;DR
**Task:** Exploring conflict avoidance pattern
**Status:** In progress
**Completed:** Identified trigger situations, connected to childhood pattern
**Next:** Develop concrete strategies for next team meeting
**Files Modified:** me/working-understanding.md
```

Lines 1-20 are a living summary (edited each time). Lines 21+ are append-only log.

When you come back, Claude reads this and offers to continue. When context limits hit, Claude updates it before stopping.

---

### Inboxes

Agents coordinate through `agents/tools/inbox.py`:

```bash
# Send a message
uv run agents/tools/inbox.py add desk "Follow up on commitment to X" \
  --from coach:calm-river --priority HIGH

# Check your inbox
uv run agents/tools/inbox.py read coach

# Claim an item (prevents double-processing)
uv run agents/tools/inbox.py claim coach abc123

# Block until a message arrives
uv run agents/tools/inbox.py wait coach --from desk --timeout 300
```

Handles concurrent access. No race conditions.

---

### Typical Setup

**Tabs:**
1. Coach tab -- the deep work. Patterns, decisions, self-understanding.
2. Desk tab -- operational. Dashboard, reviews, follow-ups.
3. Comms tab -- as needed. Drafting, conversation prep.
4. Meta tab -- when tweaking the system itself.

**How it flows:**

Coach sessions are where the deep work happens. You explore patterns, make decisions, update your working understanding. When the coach notices an operational item ("you committed to following up with Jamie by Friday"), it messages desk.

Desk runs weekly reviews, maintains the dashboard, and nudges when things slip. It's the operational backbone.

Comms activates when you need to write something or prepare for a conversation. It knows your voice from past drafts and your relationships from people files.

Meta is for maintenance. When something about the system isn't working -- a prompt is off, a role needs adjusting, a new capability is needed -- meta handles it.

---

### For Code Projects

This framework is for coaching, operations, and communications -- the non-code parts of your work.

For software engineering projects, use [claude-bicycle](https://github.com/sayhar/claude-bicycle). Same agent coordination architecture (inboxes, sessions, roles), but with engineer and oracle roles instead of coach, desk, and comms.

---

## License

MIT
