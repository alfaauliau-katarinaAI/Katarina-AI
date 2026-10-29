"""Bounded retries for transient Windows snapshot sharing conflicts; atomic replace only."""
import time


def replace_snapshot(source, target, *, attempts=12, wait=time.sleep):
    """Retry short-lived sharing violations without risking a non-atomic write.

    The previous retry budget (~0.2s) was too short for antivirus/readers
    holding latest.json on Windows. Persistent permission errors still raise:
    the observer must fail closed instead of publishing partial snapshots.
    """
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        try:
            return source.replace(target)
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            wait(min(0.02 * 2 ** attempt, 0.5))
