"""Bounded retries for Windows snapshot sharing conflicts; preserve atomic replace."""
import time


def replace_snapshot(source, target, *, attempts=8, wait=time.sleep):
    for attempt in range(attempts):
        try:
            return source.replace(target)
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            wait(min(.005 * 2 ** attempt, .05))
