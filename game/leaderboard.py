"""Leaderboard persistence helpers for Maze Runner.

JSON schema: {"times": [<float>, ...]}   -- sorted ascending, max MAX_ENTRIES entries.
The file is written next to main.py (current working directory).
"""

import json
import os

LEADERBOARD_FILE = "leaderboard.json"
MAX_ENTRIES = 5


def load_times():
    """Return sorted list of top completion times (floats) from disk.

    Returns an empty list if the file is missing, unreadable, or corrupt.
    """
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, "r") as fh:
            data = json.load(fh)
        return sorted(float(t) for t in data.get("times", []))
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        return []          # treat a corrupt file as empty rather than crashing


def save_time(elapsed):
    """Add *elapsed* to the leaderboard, persist to disk, and return results.

    Args:
        elapsed: completion time in seconds (float).

    Returns:
        (rank, times) where:
            rank  -- 1-based position in the final top-5 list, or None if the
                     time did not make it into the top MAX_ENTRIES.
            times -- the (possibly unchanged) top-5 list after the update.
    """
    elapsed = round(float(elapsed), 2)
    times = load_times()
    times.append(elapsed)
    times.sort()

    # Determine rank before truncating so we know if it made the board
    try:
        rank = times.index(elapsed) + 1   # 1-based; first match wins on ties
    except ValueError:
        rank = None

    times = times[:MAX_ENTRIES]

    # Persist only the top-MAX_ENTRIES entries
    try:
        with open(LEADERBOARD_FILE, "w") as fh:
            json.dump({"times": times}, fh, indent=2)
    except OSError:
        pass           # silently skip if we cannot write (e.g. read-only fs)

    # rank is valid only if it is within the stored entries
    if rank is not None and rank > MAX_ENTRIES:
        rank = None

    return rank, times
