#!/usr/bin/env python3
"""
Block inline code patterns - use files/scripts instead.

Catches:
  - heredocs: cat > file << 'EOF'
  - redirects: echo "..." > file
  - inline python: python -c "..." or uv run python -c "..."
  - bash special syntax: $'...' quoting, $(...) substitution
"""

import json
import sys
import re


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")

    # Inline code patterns
    patterns = [
        # Heredocs
        (r"<<\s*'?EOF'?", "Use Write tool instead of heredocs"),
        (r"<<\s*'?END'?", "Use Write tool instead of heredocs"),
        (r"cat\s*<<", "Use Write tool instead of heredocs"),
        # File redirects
        (r"cat\s+>\s*\S+", "Use Write tool instead of cat > file"),
        (r"echo\s+.*>\s*[^|]", "Use Write tool instead of echo > file"),
        (r"printf\s+.*>\s*\S+", "Use Write tool instead of printf > file"),
        # Inline Python
        (r"python3?\s+-c\s+", "Write a .py file instead of python -c"),
        (r"uv run python\s+-c\s+", "Write a .py file instead of python -c"),
        # Bash special syntax (triggers manual approval, use alternatives)
        (r"\$'", "Use Python script instead of $'...' bash quoting (e.g., count unicode: uv run python script.py)"),
        (r"\$\(", "Use Python script instead of $(...) command substitution"),
    ]

    for pattern, reason in patterns:
        if re.search(pattern, command):
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": reason,
                        }
                    }
                )
            )
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
