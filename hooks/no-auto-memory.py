#!/usr/bin/env python3
"""
Block writes to Claude Code's auto-memory directory.

Persistent state belongs in notes/, inboxes, or agent files — not MEMORY.md.
"""

import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")

    if "/.claude/" not in file_path or "/memory/" not in file_path:
        sys.exit(0)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "Don't use auto-memory. Instead: "
                "(1) write to notes/ working memory files, "
                "(2) send an inbox message for the relevant agent, or "
                "(3) update an *.agent.md file if it's a permanent rule."
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
