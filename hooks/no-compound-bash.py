#!/usr/bin/env python3
"""
Block compound bash statements - prefer separate tool calls or Python scripts.

Catches: && || ; between commands
Allows: ; inside quoted strings, || in grep patterns

Blocks because engineers ignore warnings. Write Python scripts instead.
"""

import json
import sys
import re


def block(message: str) -> None:
    """Block the command with an error message."""
    print(json.dumps({"error": message}))
    sys.exit(1)


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")

    # Remove quoted strings to avoid false positives
    # e.g., echo "foo && bar" should be allowed
    no_quotes = re.sub(r'"[^"]*"', '', command)
    no_quotes = re.sub(r"'[^']*'", '', no_quotes)

    # Check for compound operators
    if re.search(r'&&', no_quotes):
        block("Write a Python script instead of && chains")

    if re.search(r'\|\|', no_quotes):
        block("Write a Python script instead of || chains")

    # Semicolon between commands (but not at end or in for loops)
    # Allow: for x in ...; do; done
    # Block: cmd1; cmd2
    if re.search(r';\s*\w', no_quotes) and not re.search(r'\b(do|then|else)\s*;', no_quotes):
        # Check it's not a for/while/if construct
        if not re.search(r'\b(for|while|if|elif)\b', command):
            block("Write a Python script instead of ; between commands")

    sys.exit(0)


if __name__ == "__main__":
    main()
