"""Condition registry. Each condition maps to a zero-argument adapter factory.

``append_only`` and ``maintained`` come from ``adapters/brainbob.py`` (the only module
allowed to import BrainBob); if it cannot be imported they are reported unsupported.
"""
from __future__ import annotations

CONDITIONS = ("no_memory", "full_history", "append_only", "maintained", "always_refuse", "unfiltered")


class Unsupported(Exception):
    pass


def resolve(condition: str):
    """Return a zero-argument factory for ``condition`` or raise ``Unsupported``."""
    if condition == "no_memory":
        from .no_memory import NoMemoryAdapter
        return NoMemoryAdapter
    if condition == "full_history":
        from .full_history import FullHistoryAdapter
        return FullHistoryAdapter
    if condition == "always_refuse":
        from .controls import AlwaysRefuseAdapter
        return AlwaysRefuseAdapter
    if condition == "unfiltered":
        from .controls import UnfilteredAdapter
        return UnfilteredAdapter
    if condition in ("append_only", "maintained"):
        try:
            from .brainbob import BrainBobAdapter
        except Exception as e:  # noqa: BLE001 - any import failure means unsupported
            raise Unsupported(f"BrainBobAdapter import failed: {type(e).__name__}: {str(e)[:200]}") from e
        return lambda: BrainBobAdapter(mode=condition)
    raise Unsupported(f"unknown condition {condition!r}")
