# Claude Desk

Claude Code is great, but the "code" is a misnomer. It's really a framework for organizing little workers. But why do they have to be engineers?

This gives you a home office. A coach. A secretary. A PR/comms consultant. Little robot workers that can do anything — not just write code.

I use this to manage my own life. Weekly reflections and plans. Daily todos. Keeping track of what I need to do, who I need to talk to. And also — what actually happened. Reporting what I did, how I feel about it. Everything searchable. Patterns across weeks and months.

These robots call me out on my bullshit.

It's like a mirror. You say a thing at time T, and a robot reminds you — sassily — that you should keep to your word at time T+N. I find this really useful in managing my distractibility. Your mileage may vary, but if you've ever wished you had a personal coach who never forgets and never gets tired of you, this might be for you.

---

## The Roles

### Coach

The star of the show. It maintains a **working understanding** of you — your golden "who am I, what do I want" file. As you and the coach agree that things about you are true, you write them down together.

You can add **principles and aspirations**. What sort of personality do you want to inculcate in yourself? What way of making decisions, or seeing the world, do you want to be coached towards?

If you read a great essay, add it to your coach's principles. The coach internalizes it and pushes you toward it.

Pairs well with [qualified-self](https://github.com/sayhar/qualified-self).

### Desk

The coordinator. Keeps track of everything — your dashboard, your commitments, your follow-ups. Weekly reviews, daily todos. Makes sure nothing slips through the cracks.

### Comms

Helps you understand what to say — but also what other people are telling you. What are the implicit things going on? Make the implicit explicit. Model conversations like chess moves.

### Meta

Modifies the system itself. Update agent files, fix patterns, add new capabilities. The agent that maintains the agents.

---

## Quick Start

```bash
git clone https://github.com/sayhar/claude-desk my-desk
cd my-desk
claude
```

Say "meta" — it walks you through setup. Or work through `SETUP.md` manually.

---

## How It Works

*Sahar here. I'm going to hand the mic to Claude for a minute to explain the technical bits, because I can't be bothered to type them out. Take it away, robot.*

Thanks. Three things make this work:

- **Sessions** — each work thread gets a name (like "calm-river") and a file that tracks what happened. Come back three days later and I offer to pick up where you left off. When context limits hit, I update the session file before stopping so nothing is lost.
- **Inboxes** — agents leave each other messages. The coach notices you made a commitment and messages the desk to track it. File-locked, concurrent-safe, no race conditions. You can run multiple agents in separate tabs simultaneously.
- **Files** — your working understanding, decisions, weekly reviews, people notes. Everything in markdown, everything searchable, everything version-controlled in git.

The whole thing is markdown files and two Python scripts. No build step, no server, no database. `uv run` handles dependencies inline. You can read every file and understand what's happening.

*OK, I'm back. See? Useful little robot.*

---

## For Code Projects

This is for the non-code parts of your life. For software engineering, use [claude-bicycle](https://github.com/sayhar/claude-bicycle) — same architecture, different roles (engineer, oracle).

---

## License

MIT
