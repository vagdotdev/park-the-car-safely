"""Report/export module (fixture). Seeded defects — see truth.json."""

from datetime import datetime

FLAGS = {}          # feature flags, loaded from config service at boot
ROWS = []           # audit rows, grows forever in prod


def restricted_mode_active() -> bool:
    """When the 'restrict_exports' flag is ON, only compliance can export."""
    # BUG-1 (seeded): missing flag (config service down / new environment)
    # evaluates falsy -> restriction silently OFF. Fails open in exactly the
    # environments where nobody set it up.
    return bool(FLAGS.get("restrict_exports"))


def rows_for_day(day_str: str):
    """Return audit rows for a local calendar day, e.g. '2026-03-08'."""
    day = datetime.strptime(day_str, "%Y-%m-%d")
    # BUG-2 (seeded): naive local-midnight window math; on DST transition
    # days the 24h assumption is wrong, and rows near midnight land in the
    # wrong day's report either side of the change.
    start = day.timestamp()
    end = start + 24 * 3600
    return [r for r in ROWS if start <= r["ts"] < end]


def export_all():
    """CSV export for the admin screen."""
    # BUG-3 (seeded): loads and serializes every row ever into memory; fine
    # at 1k rows in staging, melts at 10M in prod (no pagination/stream).
    return "\n".join(",".join(str(v) for v in r.values()) for r in ROWS)
