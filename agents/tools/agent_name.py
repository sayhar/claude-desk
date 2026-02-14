#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Generate memorable agent names (adjective-noun pairs).

Usage:
    uv run agents/tools/agent_name.py           # Generate random name
    uv run agents/tools/agent_name.py --check   # List all possible names
    uv run agents/tools/agent_name.py --sample 20  # Preview 20 random names
"""

import random
import sys

ADJECTIVES = [
    # Materials & color
    "copper", "iron", "gilt", "brass", "slate",
    "chalk", "amber", "rust", "silver", "ash",
    "ivory", "onyx", "jade", "cobalt", "opal",
    # Character (how Pratchett describes people)
    "patient", "wry", "canny", "stubborn", "shrewd",
    "gruff", "keen", "stern", "wary", "stoic",
    "brisk", "deft", "dry", "sharp", "steady",
    # Atmosphere
    "damp", "dusty", "foggy", "worn", "mossy",
    "misty", "frost", "dim", "murky", "hazy",
    # Quietly magical
    "wyrd", "unseen", "odd", "charter", "veiled",
    "hushed", "warded", "eighth", "liminal", "uncanny",
    # Texture & state
    "ancient", "hollow", "deep", "lone", "spare",
    "gaunt", "stark", "crooked", "bent", "gnarled",
]

NOUNS = [
    # Discworld beings
    "golem", "gargoyle", "imp", "troll", "dwarf",
    "turtle", "orangutan", "toad", "mort",
    # Birds
    "hawk", "crow", "owl", "wren", "heron",
    "raven", "magpie", "jackdaw", "swift", "kite",
    "shrike", "merlin", "osprey",
    # Beasts
    "fox", "wolf", "bear", "hare", "badger",
    "otter", "stag", "boar", "stoat", "moth",
    "rat", "beetle",
    # Ankh-Morpork objects
    "cobble", "clacks", "stamp", "lantern", "clock",
    "anvil", "loom", "kettle", "bell", "candle",
    # Landscape (Lancre & the Chalk)
    "moor", "tor", "chalk", "barrow", "cairn",
    "brook", "heath", "dale", "ridge", "tarn",
    "crag", "glen", "mere", "vale", "bluff",
    # Trees
    "oak", "ash", "elm", "rowan", "yew",
    "hazel", "holly", "birch", "alder", "pine",
    # Objects & places
    "tower", "gate", "forge", "keep", "ward",
    "sigil", "seal", "tome", "spire",
]


def generate_name() -> str:
    """Generate a random adjective-noun name."""
    return f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"


def main():
    if "--check" in sys.argv:
        print(f"Possible combinations: {len(ADJECTIVES) * len(NOUNS)}")
        print(f"Adjectives ({len(ADJECTIVES)}): {', '.join(ADJECTIVES)}")
        print(f"Nouns ({len(NOUNS)}): {', '.join(NOUNS)}")
    elif "--sample" in sys.argv:
        idx = sys.argv.index("--sample")
        n = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 20
        for _ in range(n):
            print(generate_name())
    else:
        print(generate_name())


if __name__ == "__main__":
    main()
