#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich>=13.0.0", "filelock>=3.12.0"]
# ///
"""
Inbox management CLI for agent communication.

Usage:
    uv run agents/tools/inbox.py read {role}
    uv run agents/tools/inbox.py add {role} "title" --from X --priority Y [--body "..."]
    uv run agents/tools/inbox.py delete {role} {index_or_id}
"""

import argparse
import hashlib
import re
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

from filelock import FileLock
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

VALID_ROLES = ["coach", "desk", "comms", "meta", "external"]
VALID_PRIORITIES = ["HIGH", "MEDIUM", "LOW"]
INBOX_DIR = Path("agents/state/inboxes")
SESSIONS_DIR = Path("agents/state/sessions")

# Lock timeout: long enough for slow filesystems, short enough to detect crashes
# FileLock auto-releases on process exit, protecting against crashed processes
LOCK_TIMEOUT = 30  # seconds

# Role-based default timeouts for `wait` command (seconds)
# Oracle runs daemon mode (long polling), engineer waits for quick responses
ROLE_TIMEOUTS = {
    "coach": 300,  # 5 min - default
    "desk": 300,  # 5 min - default
    "comms": 300,  # 5 min - default
    "meta": 300,  # 5 min - default
    "external": 300,  # 5 min - default
}


def generate_item_id(title: str, from_agent: str, date_str: str, priority: str) -> str:
    """
    Generate a stable 7-char ID for an inbox item.

    Hash is based on: title + date + from + priority
    Uses first 7 chars of SHA256 (like git commit hashes).
    """
    # Create stable input for hashing
    input_str = f"{title}|{date_str}|{from_agent}|{priority}"

    # Generate hash and take first 7 chars
    hash_obj = hashlib.sha256(input_str.encode("utf-8"))
    return hash_obj.hexdigest()[:7]


def get_inbox_path(role: str) -> Path:
    """Get path to inbox file for a role."""
    return INBOX_DIR / f"{role}.md"


def get_next_session_id(role: str) -> str:
    """
    Generate session ID using PID+timestamp (naturally unique).

    Format: {role}-{YYYY-MM-DD}-{PID}-{timestamp}

    Uses process ID + millisecond timestamp to ensure uniqueness
    without filesystem reads or coordination.
    """
    import os
    import time

    today = date.today().isoformat()
    pid = os.getpid()
    timestamp = int(time.time() * 1000) % 100000  # Last 5 digits ms

    return f"{role}-{today}-{pid}-{timestamp}"


def parse_inbox(content: str) -> list[dict]:
    """
    Parse inbox markdown into structured items.

    Auto-generates IDs for items that don't have them (migration).
    """
    items = []

    # Split on --- separators
    parts = re.split(r"\n---\n", content)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Remove header line if present, keep rest of block
        if part.startswith("# "):
            lines = part.split("\n", 1)
            if len(lines) > 1:
                part = lines[1].strip()
            else:
                continue  # Only header, no content
        if not part:
            continue
        # Skip HTML comments (legacy template format)
        if part.startswith("<!--") and part.endswith("-->"):
            continue

        # Extract title (## line)
        title_match = re.search(r"^## (.+)$", part, re.MULTILINE)
        title = title_match.group(1) if title_match else "Untitled"

        # Extract metadata
        id_match = re.search(r"\*\*ID:\*\*\s*([a-f0-9]{7})(?:\n|$)", part)
        from_match = re.search(r"\*\*From:\*\*\s*(.+?)(?:\n|$)", part)
        date_match = re.search(r"\*\*Date:\*\*\s*(.+?)(?:\n|$)", part)
        priority_match = re.search(r"\*\*Priority:\*\*\s*(.+?)(?:\n|$)", part)
        in_reply_to_match = re.search(r"\*\*In-Reply-To:\*\*\s*([a-f0-9]{7})(?:\n|$)", part)
        status_match = re.search(r"\*\*Status:\*\*\s*CLAIMED by (.+?)(?:\n|$)", part)
        claimed_at_match = re.search(r"\*\*Claimed At:\*\*\s*(.+?)(?:\n|$)", part)

        # Extract values
        from_agent = from_match.group(1).strip() if from_match else "Unknown"
        date_str = date_match.group(1).strip() if date_match else str(date.today())
        priority = priority_match.group(1).strip() if priority_match else "MEDIUM"
        in_reply_to = in_reply_to_match.group(1).strip() if in_reply_to_match else None
        status = status_match.group(1).strip() if status_match else None
        claimed_at = claimed_at_match.group(1).strip() if claimed_at_match else None

        # Get or generate ID
        if id_match:
            item_id = id_match.group(1)
        else:
            # Auto-generate ID for migration
            item_id = generate_item_id(title, from_agent, date_str, priority)

        # Extract body (everything after last metadata line)
        # Body comes after Claimed At, Status, In-Reply-To, or Priority (in that order)
        if claimed_at:
            body_match = re.search(r"\*\*Claimed At:\*\*[^\n]*\n(.+)", part, re.DOTALL)
        elif status:
            body_match = re.search(r"\*\*Status:\*\*[^\n]*\n(.+)", part, re.DOTALL)
        elif in_reply_to:
            body_match = re.search(r"\*\*In-Reply-To:\*\*[^\n]*\n(.+)", part, re.DOTALL)
        else:
            body_match = re.search(r"\*\*Priority:\*\*[^\n]*\n(.+)", part, re.DOTALL)
        body = body_match.group(1).strip() if body_match else ""
        # Unescape --- that were escaped during write
        body = unescape_body_separators(body)

        items.append(
            {
                "id": item_id,
                "title": title,
                "from": from_agent,
                "date": date_str,
                "priority": priority,
                "in_reply_to": in_reply_to,  # Thread correlation for responses
                "status": status,  # None if unclaimed, session-id if claimed
                "claimed_at": claimed_at,  # ISO 8601 timestamp or None
                "body": body,
            }
        )

    return items


def escape_body_separators(body: str) -> str:
    """Escape --- in body to prevent parse_inbox from splitting on it."""
    # Replace \n---\n with \n-​-​-\n (using zero-width spaces)
    # This preserves visual appearance while preventing split
    return body.replace("\n---\n", "\n-\u200b-\u200b-\n")


def unescape_body_separators(body: str) -> str:
    """Unescape --- in body after parsing."""
    return body.replace("\n-\u200b-\u200b-\n", "\n---\n")


def format_item(item: dict) -> str:
    """Format an item as markdown with ID and optional claimed status."""
    lines = [
        f"## {item['title']}",
        "",
        f"**ID:** {item['id']}",
        f"**From:** {item['from']}",
        f"**Date:** {item['date']}",
        f"**Priority:** {item['priority']}",
    ]
    # Add in_reply_to if present (for response threading)
    if item.get("in_reply_to"):
        lines.append(f"**In-Reply-To:** {item['in_reply_to']}")
    # Add status line if claimed
    if item.get("status"):
        lines.append(f"**Status:** CLAIMED by {item['status']}")
    # Add claimed_at timestamp if present
    if item.get("claimed_at"):
        lines.append(f"**Claimed At:** {item['claimed_at']}")
    if item.get("body"):
        lines.append("")
        # Escape --- to prevent splitting issues
        lines.append(escape_body_separators(item["body"]))
    return "\n".join(lines)


def write_inbox(role: str, items: list[dict]) -> None:
    """Write items to inbox file atomically."""
    inbox_path = get_inbox_path(role)
    inbox_path.parent.mkdir(parents=True, exist_ok=True)

    header = f"# {role.capitalize()} Inbox\n\n---\n\n"  # Always --- after header
    if items:
        body = "\n\n---\n\n".join(format_item(item) for item in items)
        content = header + body + "\n\n---\n\n"
    else:
        content = header

    # Atomic write
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        f.write(content)
        temp_path = f.name
    shutil.move(temp_path, inbox_path)


def cmd_read(args: argparse.Namespace) -> None:
    """Display inbox contents with IDs."""
    role = args.role.lower()
    if role not in VALID_ROLES:
        console.print(
            f"[red]Error:[/red] Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}"
        )
        sys.exit(1)

    inbox_path = get_inbox_path(role)
    if not inbox_path.exists():
        console.print(f"[yellow]{role.capitalize()} inbox is empty.[/yellow]")
        return

    # Check if migration needed (quick check before locking)
    content = inbox_path.read_text()
    needs_migration = "**ID:**" not in content and content.strip()

    if needs_migration:
        # Re-read inside lock to prevent TOCTOU race
        lock_path = inbox_path.with_suffix(".lock")
        with FileLock(lock_path, timeout=LOCK_TIMEOUT):
            content = inbox_path.read_text()
            # Re-check: another process may have migrated while we waited for lock
            if "**ID:**" not in content and content.strip():
                items = parse_inbox(content)
                write_inbox(role, items)
                console.print("[dim]Migrated inbox items to include IDs.[/dim]\n")
            else:
                items = parse_inbox(content)
    else:
        items = parse_inbox(content)

    if not items:
        console.print(f"[yellow]{role.capitalize()} inbox is empty.[/yellow]")
        return

    console.print(
        f"\n[bold]{role.capitalize()} Inbox[/bold] ({len(items)} item{'s' if len(items) != 1 else ''})\n"
    )

    for i, item in enumerate(items, 1):
        priority_color = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(
            item["priority"], "white"
        )
        # Include ID and claimed status in header
        # Format: [1] (a3f4b2c) [CLAIMED] Title
        if item.get("status"):
            # Extract claiming role and abbreviated session ID
            session_parts = item["status"].split("-")
            session_role = session_parts[0] if session_parts else "unknown"
            session_abbrev = session_parts[-1] if session_parts else item["status"]
            header = f"[{i}] ({item['id']}) [dim][CLAIMED by {session_role}-{session_abbrev}][/dim] {item['title']}"
        else:
            header = f"[{i}] ({item['id']}) {item['title']}"

        meta = f"From: {item['from']} | Date: {item['date']} | Priority: [{priority_color}]{item['priority']}[/{priority_color}]"

        console.print(
            Panel(
                f"{meta}\n\n{item['body']}" if item["body"] else meta,
                title=header,
                title_align="left",
            )
        )
        console.print()


def cmd_peek(args: argparse.Namespace) -> None:
    """Return first unclaimed item as JSON (read-only, no side effects).

    With --from filter, only returns items from the specified sender role.
    With --in-reply-to filter, only returns responses to the specified message ID.
    """
    import json

    role = args.role.lower()
    if role not in VALID_ROLES:
        console.print(
            f"[red]Error:[/red] Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}"
        )
        sys.exit(1)

    # Parse optional filters
    from_filter = args.from_filter.strip().lower() if args.from_filter else None
    in_reply_to_filter = args.in_reply_to.strip() if args.in_reply_to else None

    inbox_path = get_inbox_path(role)
    if not inbox_path.exists():
        # Empty inbox - return empty object
        print(json.dumps({}))
        return

    content = inbox_path.read_text()
    items = parse_inbox(content)

    # Find first unclaimed item (oldest by document order)
    for item in items:
        if item.get("status"):  # Skip claimed
            continue

        # Apply sender filter if provided (handles "role:name" format)
        if from_filter:
            item_sender = item.get("from", "").lower().split(":")[0]
            if item_sender != from_filter:
                continue

        # Apply in_reply_to filter if provided (exact match)
        if in_reply_to_filter:
            if item.get("in_reply_to") != in_reply_to_filter:
                continue

        # Return item as JSON (omit status field per Oracle)
        output = {
            "id": item["id"],
            "title": item["title"],
            "from": item["from"],
            "date": item["date"],
            "priority": item["priority"],
            "body": item["body"],
        }
        if item.get("in_reply_to"):
            output["in_reply_to"] = item["in_reply_to"]
        print(json.dumps(output))
        return

    # No unclaimed items found (matching filter if provided)
    print(json.dumps({}))


def cmd_wait(args: argparse.Namespace) -> None:
    """
    Block until an unclaimed item is available or timeout occurs.

    Returns item JSON or {"timeout": true}. Uses internal polling to avoid
    wasteful tool calls - checks every 5 seconds internally.

    With --from filter, only waits for items from the specified sender role.
    Items from other senders are ignored (behavioral change from unfiltered wait).

    Timeout defaults are role-based (oracle=50min, engineer=3min) but can be
    overridden with --timeout flag.
    """
    import json
    import time

    role = args.role.lower()
    if role not in VALID_ROLES:
        console.print(
            f"[red]Error:[/red] Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}"
        )
        sys.exit(1)

    # Parse optional filters
    from_filter = args.from_filter.strip().lower() if args.from_filter else None
    in_reply_to_filter = args.in_reply_to.strip() if args.in_reply_to else None

    # Use explicit --timeout if provided, otherwise role-based default
    timeout = args.timeout if args.timeout is not None else ROLE_TIMEOUTS.get(role, 300)
    poll_interval = 5  # Check every 5 seconds
    start_time = time.time()

    while True:
        # Check if we have an item (lockless read is safe here)
        # Safe because: (1) write_inbox() uses atomic shutil.move(), (2) polling retries catch missed items
        inbox_path = get_inbox_path(role)
        if inbox_path.exists():
            content = inbox_path.read_text()
            items = parse_inbox(content)

            # Find first unclaimed item (matching filter if provided)
            for item in items:
                if item.get("status"):  # Skip claimed
                    continue

                # Apply sender filter if provided (handles "role:name" format)
                if from_filter:
                    item_sender = item.get("from", "").lower().split(":")[0]
                    if item_sender != from_filter:
                        continue

                # Apply in_reply_to filter if provided (exact match)
                if in_reply_to_filter:
                    if item.get("in_reply_to") != in_reply_to_filter:
                        continue

                # Return item as JSON (omit status field)
                output = {
                    "id": item["id"],
                    "title": item["title"],
                    "from": item["from"],
                    "date": item["date"],
                    "priority": item["priority"],
                    "body": item["body"],
                }
                if item.get("in_reply_to"):
                    output["in_reply_to"] = item["in_reply_to"]
                print(json.dumps(output))
                return

        # Check timeout
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            # Timeout - no item available
            print(json.dumps({"timeout": True}))
            return

        # Sleep before next check (but don't sleep longer than remaining time)
        remaining = timeout - elapsed
        sleep_time = min(poll_interval, remaining)
        if sleep_time > 0:
            time.sleep(sleep_time)


def cmd_add(args: argparse.Namespace) -> None:
    """Add item to inbox with generated ID."""
    role = args.role.lower()
    if role not in VALID_ROLES:
        console.print(
            f"[red]Error:[/red] Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}"
        )
        sys.exit(1)

    from_agent = args.from_agent
    if not from_agent:
        console.print("[red]Error:[/red] --from is required.")
        sys.exit(1)

    priority = args.priority.upper()
    if priority not in VALID_PRIORITIES:
        console.print(
            f"[red]Error:[/red] Invalid priority '{priority}'. Use: {', '.join(VALID_PRIORITIES)}"
        )
        sys.exit(1)

    # Read body: --body-file takes precedence, then --body, then stdin
    body = ""
    if hasattr(args, "body_file") and args.body_file:
        try:
            body = Path(args.body_file).read_text().strip()
        except Exception as e:
            console.print(f"[red]Error:[/red] Cannot read body file: {e}")
            sys.exit(1)
    elif args.body:
        body = args.body
    elif not sys.stdin.isatty():
        body = sys.stdin.read().strip()

    # Generate ID for new item
    date_str = str(date.today())
    item_id = generate_item_id(args.title, from_agent, date_str, priority)

    # Atomic read-modify-write with file locking
    inbox_path = get_inbox_path(role)
    lock_path = inbox_path.with_suffix(".lock")

    with FileLock(lock_path, timeout=LOCK_TIMEOUT):
        # Read current inbox
        items = parse_inbox(inbox_path.read_text()) if inbox_path.exists() else []

        # Add new item
        items.append(
            {
                "id": item_id,
                "title": args.title,
                "from": from_agent,
                "date": date_str,
                "priority": priority,
                "body": body,
            }
        )

        # Write back atomically
        write_inbox(role, items)

    console.print(f"[green]Added item to {role} inbox:[/green] {args.title} [dim]({item_id})[/dim]")


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete item from inbox by ID or index."""
    role = args.role.lower()
    if role not in VALID_ROLES:
        console.print(
            f"[red]Error:[/red] Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}"
        )
        sys.exit(1)

    id_or_index = args.id_or_index
    inbox_path = get_inbox_path(role)
    lock_path = inbox_path.with_suffix(".lock")

    # Atomic read-modify-write with file locking
    with FileLock(lock_path, timeout=LOCK_TIMEOUT):
        items = parse_inbox(inbox_path.read_text()) if inbox_path.exists() else []

        if not items:
            console.print(f"[red]Error:[/red] {role.capitalize()} inbox is empty.")
            sys.exit(1)

        # Try to parse as ID first (7-char hex string)
        if re.match(r"^[a-f0-9]{7}$", id_or_index):
            # Delete by ID
            item_id = id_or_index
            deleted_idx = None
            for idx, item in enumerate(items):
                if item["id"] == item_id:
                    deleted_idx = idx
                    break

            if deleted_idx is None:
                console.print(f"[red]Error:[/red] No item found with ID '{item_id}'.")
                sys.exit(1)

            deleted = items.pop(deleted_idx)
            write_inbox(role, items)
            console.print(f"[green]Deleted from {role} inbox:[/green] {deleted['title']}")

        else:
            # Try to parse as integer index
            try:
                index = int(id_or_index)
            except ValueError:
                console.print(
                    f"[red]Error:[/red] '{id_or_index}' is not a valid ID (7-char hex) or index (integer)."
                )
                sys.exit(1)

            if index < 1 or index > len(items):
                console.print(
                    f"[red]Error:[/red] {role.capitalize()} inbox has {len(items)} item(s). Cannot delete item {index}."
                )
                sys.exit(1)

            deleted = items[index - 1]

            # Show warning about concurrent access
            console.print(
                f"[yellow]Warning:[/yellow] Using index is unsafe with concurrent agents. Use ID instead: [bold]{deleted['id']}[/bold]"
            )

            items.pop(index - 1)
            write_inbox(role, items)
            console.print(f"[green]Deleted from {role} inbox:[/green] {deleted['title']}")


def cmd_claim(args: argparse.Namespace) -> None:
    """Claim an inbox item for exclusive work."""
    role = args.role.lower()
    if role not in VALID_ROLES:
        console.print(
            f"[red]Error:[/red] Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}"
        )
        sys.exit(1)

    item_id = args.item_id
    session_id = get_next_session_id(role)
    inbox_path = get_inbox_path(role)
    lock_path = inbox_path.with_suffix(".lock")

    # Atomic read-modify-write with file locking
    from datetime import datetime, timezone

    with FileLock(lock_path, timeout=LOCK_TIMEOUT):
        items = parse_inbox(inbox_path.read_text()) if inbox_path.exists() else []

        if not items:
            console.print(f"[red]Error:[/red] {role.capitalize()} inbox is empty.")
            sys.exit(1)

        # Find item by ID
        found_idx = None
        for idx, item in enumerate(items):
            if item["id"] == item_id:
                found_idx = idx
                break

        if found_idx is None:
            console.print(f"[red]Error:[/red] No item found with ID '{item_id}'.")
            sys.exit(1)

        item = items[found_idx]

        # Check if already claimed
        if item.get("status"):
            console.print(
                f"[red]Error:[/red] Item already claimed by session: [bold]{item['status']}[/bold]"
            )
            sys.exit(1)

        # Update item with claimed status and timestamp
        items[found_idx]["status"] = session_id
        items[found_idx]["claimed_at"] = datetime.now(timezone.utc).isoformat()

        write_inbox(role, items)

    console.print(
        f"[green]Claimed:[/green] {item['title']}\n[dim]Session token:[/dim] [bold]{session_id}[/bold]"
    )


def cmd_unclaim(args: argparse.Namespace) -> None:
    """Unclaim an inbox item (requires matching token)."""
    role = args.role.lower()
    if role not in VALID_ROLES:
        console.print(
            f"[red]Error:[/red] Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}"
        )
        sys.exit(1)

    item_id = args.item_id
    token = args.token
    inbox_path = get_inbox_path(role)
    lock_path = inbox_path.with_suffix(".lock")

    # Atomic read-modify-write with file locking
    with FileLock(lock_path, timeout=LOCK_TIMEOUT):
        items = parse_inbox(inbox_path.read_text()) if inbox_path.exists() else []

        if not items:
            console.print(f"[red]Error:[/red] {role.capitalize()} inbox is empty.")
            sys.exit(1)

        # Find item by ID
        found_idx = None
        for idx, item in enumerate(items):
            if item["id"] == item_id:
                found_idx = idx
                break

        if found_idx is None:
            console.print(f"[red]Error:[/red] No item found with ID '{item_id}'.")
            sys.exit(1)

        item = items[found_idx]

        # Check if claimed
        if not item.get("status"):
            console.print(f"[yellow]Warning:[/yellow] Item is not claimed.")
            sys.exit(0)

        # Verify token matches
        if item["status"] != token:
            console.print(
                f"[red]Error:[/red] Cannot unclaim: token mismatch.\n"
                f"Item claimed by: [bold]{item['status']}[/bold]\n"
                f"Your token: [bold]{token}[/bold]"
            )
            sys.exit(1)

        # Remove claim and timestamp
        items[found_idx]["status"] = None
        items[found_idx]["claimed_at"] = None

        write_inbox(role, items)

    console.print(f"[green]Unclaimed:[/green] {item['title']}")


def cmd_respond(args: argparse.Namespace) -> None:
    """
    Best-effort atomic operation: respond to claimed item.

    WARNING: Not fully atomic - if process crashes between delete and respond,
    the message will be lost. Acceptable for agent communication use case.

    1. Read both inboxes (original + sender's)
    2. Verify token matches claimed item
    3. Delete original item
    4. Add response to sender's inbox
    """
    role = args.role.lower()
    if role not in VALID_ROLES:
        print(
            f"Error: Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    item_id = args.item_id
    token = args.token

    # Read body: --body-file takes precedence, then --body, then stdin
    body = ""
    if args.body_file:
        try:
            body = Path(args.body_file).read_text().strip()
        except Exception as e:
            print(f"Error: Cannot read body file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.body:
        body = args.body
    elif not sys.stdin.isatty():
        body = sys.stdin.read().strip()

    if not body:
        print("Error: Response body is required (--body, --body-file, or stdin).", file=sys.stderr)
        sys.exit(1)

    inbox_path = get_inbox_path(role)
    lock_path = inbox_path.with_suffix(".lock")

    # First pass: verify and prepare (read-only, minimal locking)
    with FileLock(lock_path, timeout=LOCK_TIMEOUT):
        items = parse_inbox(inbox_path.read_text()) if inbox_path.exists() else []

        if not items:
            print(f"Error: {role.capitalize()} inbox is empty.", file=sys.stderr)
            sys.exit(1)

        # Find item by ID
        found_idx = None
        for idx, item in enumerate(items):
            if item["id"] == item_id:
                found_idx = idx
                break

        if found_idx is None:
            print(f"Error: No item found with ID '{item_id}'.", file=sys.stderr)
            sys.exit(1)

        item = items[found_idx]

        # Verify item is claimed
        if not item.get("status"):
            print("Error: Item is not claimed. Cannot respond to unclaimed item.", file=sys.stderr)
            sys.exit(1)

        # Verify token matches
        if item["status"] != token:
            print(
                f"Error: Cannot respond: token mismatch.\n"
                f"Item claimed by: {item['status']}\n"
                f"Your token: {token}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Determine sender (where to send response)
        # Handle "role:name" format (e.g., "engineer:swift-falcon" → "engineer")
        sender_role = item.get("from", "").lower().split(":")[0]

    # Validate sender role (outside lock)
    if sender_role not in VALID_ROLES:
        print(
            f"Error: Invalid sender role '{sender_role}' in item. Cannot send response.",
            file=sys.stderr,
        )
        sys.exit(1)

    # CRITICAL: Sequential locks to prevent deadlock (lock 1, release, then lock 2)
    # Delete from our inbox
    with FileLock(lock_path, timeout=LOCK_TIMEOUT):
        items = parse_inbox(inbox_path.read_text()) if inbox_path.exists() else []

        # Re-find and delete item
        found_idx = None
        for idx, item in enumerate(items):
            if item["id"] == item_id:
                found_idx = idx
                break

        if found_idx is None:
            print(f"Error: Item disappeared during respond operation.", file=sys.stderr)
            sys.exit(1)

        item = items.pop(found_idx)
        write_inbox(role, items)

        # Prepare response
        response_title = f"Re: {item['title']}"
        response_item = {
            "id": generate_item_id(response_title, role, str(date.today()), item["priority"]),
            "title": response_title,
            "from": role,
            "date": str(date.today()),
            "priority": item["priority"],
            "body": body,
            "in_reply_to": item_id,  # Thread correlation - lets sender wait for this specific response
        }
    # Lock released here

    # Write to sender's inbox (new lock, prevents deadlock)
    sender_inbox_path = get_inbox_path(sender_role)
    sender_lock_path = sender_inbox_path.with_suffix(".lock")

    with FileLock(sender_lock_path, timeout=LOCK_TIMEOUT):
        sender_items = (
            parse_inbox(sender_inbox_path.read_text()) if sender_inbox_path.exists() else []
        )
        sender_items.append(response_item)
        write_inbox(sender_role, sender_items)

    console.print(
        f"[green]Responded to {sender_role}:[/green] {response_title} [dim]({response_item['id']})[/dim]"
    )


def cmd_unclaim_stale(args: argparse.Namespace) -> None:
    """Force-unclaim items with expired claims (cleanup after crashed daemons)."""
    from datetime import datetime, timezone

    role = args.role.lower()
    if role not in VALID_ROLES:
        console.print(
            f"[red]Error:[/red] Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}"
        )
        sys.exit(1)

    older_than = args.older_than  # seconds
    now = datetime.now(timezone.utc)
    unclaimed = []
    inbox_path = get_inbox_path(role)
    lock_path = inbox_path.with_suffix(".lock")

    # Atomic read-modify-write with file locking
    with FileLock(lock_path, timeout=LOCK_TIMEOUT):
        items = parse_inbox(inbox_path.read_text()) if inbox_path.exists() else []

        if not items:
            console.print(f"[yellow]{role.capitalize()} inbox is empty.[/yellow]")
            return

        # Find and unclaim stale items
        for item in items:
            # Skip unclaimed items
            if not item.get("status"):
                continue

            # Check if has claimed_at timestamp
            if not item.get("claimed_at"):
                # Warn about old claims without timestamp
                console.print(
                    f"[yellow]Warning:[/yellow] Item '{item['title']}' ({item['id']}) is claimed but has no timestamp. Skipping."
                )
                continue

            # Parse timestamp and check age
            try:
                claimed_at = datetime.fromisoformat(item["claimed_at"])
                age_seconds = (now - claimed_at).total_seconds()

                if age_seconds > older_than:
                    # Mark for unclaim
                    item["status"] = None
                    item["claimed_at"] = None
                    unclaimed.append(
                        {"title": item["title"], "id": item["id"], "age_seconds": age_seconds}
                    )
            except (ValueError, TypeError) as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Item '{item['title']}' ({item['id']}) has invalid timestamp: {e}. Skipping."
                )
                continue

        # Write back if any changes
        if unclaimed:
            write_inbox(role, items)

    # Report results (outside lock)
    if unclaimed:
        console.print(f"\n[green]Unclaimed {len(unclaimed)} stale item(s):[/green]\n")
        for item_info in unclaimed:
            age_minutes = int(item_info["age_seconds"] / 60)
            age_hours = int(age_minutes / 60)
            if age_hours > 0:
                age_str = f"{age_hours}h ago"
            elif age_minutes > 0:
                age_str = f"{age_minutes}m ago"
            else:
                age_str = f"{int(item_info['age_seconds'])}s ago"

            console.print(f"  - {item_info['id']}: {item_info['title']} (claimed {age_str})")
    else:
        console.print(f"[dim]No stale claims found (threshold: {older_than}s).[/dim]")


def main():
    parser = argparse.ArgumentParser(
        description="Inbox management for agent communication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run agents/tools/inbox.py read engineer
  uv run agents/tools/inbox.py peek engineer                 # JSON output (non-blocking)
  uv run agents/tools/inbox.py peek engineer --from oracle-daemon  # Only items from oracle-daemon
  uv run agents/tools/inbox.py wait oracle                    # Uses role default (50 min for oracle)
  uv run agents/tools/inbox.py wait engineer --from oracle    # Uses role default (3 min for engineer)
  uv run agents/tools/inbox.py wait engineer --timeout 60     # Override: explicit 60 sec
  uv run agents/tools/inbox.py add engineer "Review code" --from oracle --priority HIGH
  uv run agents/tools/inbox.py add engineer "Fix bug" --from oracle --priority MEDIUM --body "Check line 50"
  uv run agents/tools/inbox.py delete engineer a3f4b2c  # by ID (safer)
  uv run agents/tools/inbox.py delete engineer 1        # by index (shows warning)
  uv run agents/tools/inbox.py claim engineer a3f4b2c   # claim for exclusive work
  uv run agents/tools/inbox.py unclaim engineer a3f4b2c --token engineer-2026-01-02-003
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # read command
    read_parser = subparsers.add_parser("read", help="Display inbox contents")
    read_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    read_parser.set_defaults(func=cmd_read)

    # peek command
    peek_parser = subparsers.add_parser("peek", help="Return first unclaimed item as JSON")
    peek_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    peek_parser.add_argument(
        "--from", dest="from_filter", help="Only return items from this sender role"
    )
    peek_parser.add_argument(
        "--in-reply-to", dest="in_reply_to", help="Only return responses to this message ID"
    )
    peek_parser.set_defaults(func=cmd_peek)

    # wait command
    wait_parser = subparsers.add_parser("wait", help="Block until item available or timeout")
    wait_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    wait_parser.add_argument(
        "--from", dest="from_filter", help="Only wait for items from this sender role"
    )
    wait_parser.add_argument(
        "--in-reply-to", dest="in_reply_to", help="Only wait for responses to this message ID"
    )
    wait_parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds (default: oracle=2999, engineer=359, others=300)",
    )
    wait_parser.set_defaults(func=cmd_wait)

    # add command
    add_parser = subparsers.add_parser("add", help="Add item to inbox")
    add_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    add_parser.add_argument("title", help="Item title")
    add_parser.add_argument("--from", dest="from_agent", required=True, help="Sending agent")
    add_parser.add_argument("--priority", default="MEDIUM", help="Priority (HIGH, MEDIUM, LOW)")
    add_parser.add_argument("--body", help="Item body (or pipe via stdin)")
    add_parser.add_argument(
        "--body-file", dest="body_file", help="Read body from file (avoids multi-line bash)"
    )
    add_parser.set_defaults(func=cmd_add)

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete item from inbox")
    delete_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    delete_parser.add_argument(
        "id_or_index",
        help="Item ID (7-char hex, safer) or index (1-based, shows warning)",
    )
    delete_parser.set_defaults(func=cmd_delete)

    # claim command
    claim_parser = subparsers.add_parser("claim", help="Claim item for exclusive work")
    claim_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    claim_parser.add_argument("item_id", help="Item ID (7-char hex)")
    claim_parser.set_defaults(func=cmd_claim)

    # unclaim command
    unclaim_parser = subparsers.add_parser("unclaim", help="Unclaim item (requires token)")
    unclaim_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    unclaim_parser.add_argument("item_id", help="Item ID (7-char hex)")
    unclaim_parser.add_argument("--token", required=True, help="Session token from claim")
    unclaim_parser.set_defaults(func=cmd_unclaim)

    # respond command
    respond_parser = subparsers.add_parser("respond", help="Respond to claimed item (atomic)")
    respond_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    respond_parser.add_argument("item_id", help="Item ID (7-char hex)")
    respond_parser.add_argument("--token", required=True, help="Session token from claim")
    respond_parser.add_argument("--body", help="Response body (or pipe via stdin)")
    respond_parser.add_argument(
        "--body-file", dest="body_file", help="Read body from file (avoids multi-line bash)"
    )
    respond_parser.set_defaults(func=cmd_respond)

    # unclaim_stale command
    unclaim_stale_parser = subparsers.add_parser(
        "unclaim_stale", help="Force-unclaim items with expired claims"
    )
    unclaim_stale_parser.add_argument("role", help=f"Agent role ({', '.join(VALID_ROLES)})")
    unclaim_stale_parser.add_argument(
        "--older-than", dest="older_than", type=int, required=True, help="Age threshold in seconds"
    )
    unclaim_stale_parser.set_defaults(func=cmd_unclaim_stale)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
