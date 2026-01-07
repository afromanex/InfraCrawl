"""SQLAlchemy ORM models and a lightweight repository adapter.

This module provides declarative models that match the existing schema and a
`Repository` class that exposes a subset of the current `db.py` functions so
we can migrate incrementally.
"""
from __future__ import annotations

"""Compatibility shim that re-exports the refactored DB modules.

This file keeps short-lived imports working for code that still imports
``infracrawl.orm`` while the codebase transitions to the new
``infracrawl.db`` package.
"""

raise ImportError("infracrawl.orm has been removed; import from infracrawl.db instead")
