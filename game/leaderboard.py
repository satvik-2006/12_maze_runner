"""Leaderboard persistence helpers for Maze Runner.

Each difficulty level has its own JSON file:
  leaderboard_easy.json / leaderboard_medium.json / leaderboard_hard.json

JSON schema: {"times": [<float>, ...]}  -- sorted ascending, max MAX_ENTRIES items.
Files are written next to main.py (current working directory).
"""

import json
import os

MAX_ENTRIES = 5


def _filepath(difficulty: str) -> str:
    """Return the leaderboard filename for *difficulty*."""
    return f"leaderboard_{difficulty.lower()}.json"


def load_times(difficulty: str = "Medium") -> list:
    """Return a sorted list of top completion times (floats) for *difficulty*.

    Returns an empty list when the file is missing, unreadable, or corrupt.
    """
    path = _filepath(difficulty)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        return sorted(float(t) for t in data.get("times", []))
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        return []   # treat corrupt file as empty rather than crashing


def save_time(elapsed: float, difficulty: str = "Medium"):
    """Add *elapsed* to the leaderboard for *difficulty*, persist, return results.

    Args:
        elapsed:    Completion time in seconds.
        difficulty: One of "Easy", "Medium", "Hard" (case-insensitive key).

    Returns:
        (rank, times) where:
            rank  -- 1-based position in the final top-5, or None if the time
                     did not make it into the top MAX_ENTRIES.
            times -- the updated top-5 list.
    """
    elapsed = round(float(elapsed), 2)
    times = load_times(difficulty)
    times.append(elapsed)
    times.sort()

    # Capture rank before truncation
    try:
        rank = times.index(elapsed) + 1   # 1-based; first match wins on ties
    except ValueError:
        rank = None

    times = times[:MAX_ENTRIES]

    try:
        with open(_filepath(difficulty), "w") as fh:
            json.dump({"times": times}, fh, indent=2)
    except OSError:
        pass   # silently skip on read-only filesystems

    # rank is valid only if it falls within the stored slice
    if rank is not None and rank > MAX_ENTRIES:
        rank = None

    return rank, times
