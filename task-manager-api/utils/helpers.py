"""Shared calculations and the storage-compatible UTC clock."""

from datetime import datetime, timezone


def utc_now():
    # Existing SQLite DateTime columns store naive UTC, including historical data.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def calculate_percentage(part, total):
    return round(part / total * 100, 2) if total else 0
