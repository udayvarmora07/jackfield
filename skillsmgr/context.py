"""The Store that ``global`` means for the current thread of work.

SCOPE-10: this is a ``ContextVar``, not a module global.  As a plain global the
last binding won for every caller in the process, so a second in-process
``WebAppServer`` silently redirected the first server's global reads *and* its
snapshot writes to another data dir.  The web server rebinds it from its own
``store`` at the start of every request thread, and the CLI binds the Store it
was asked for, so neither inherits a stale binding.
"""

from __future__ import annotations

import contextlib
from contextvars import ContextVar

ACTIVE_STORE: ContextVar = ContextVar("skillsmgr_active_store", default=None)


def active_store():
    """The bound Store, or ``None`` when nothing has bound one."""
    return ACTIVE_STORE.get()


def set_active_store(store) -> None:
    """Bind ``store`` for this context (``None`` unbinds)."""
    ACTIVE_STORE.set(store)


@contextlib.contextmanager
def bound_store(store):
    """Bind ``store`` for the block, restoring the prior binding after."""
    token = ACTIVE_STORE.set(store)
    try:
        yield store
    finally:
        ACTIVE_STORE.reset(token)


# Agent tracking (web UI only, B1): what the web app shows.  The CLI never
# binds this, so ``--scope`` and every command keep seeing every scope.  The
# web server binds one overlay per server at the start of each request thread,
# the same way it binds its Store above.  The overlay is duck-typed: it has a
# ``view()`` returning the current tracking view (see ``skillsmgr.tracking``).
SCOPE_OVERLAY: ContextVar = ContextVar("skillsmgr_scope_overlay", default=None)


def active_scope_overlay():
    """The bound tracking overlay, or ``None`` (CLI and direct callers)."""
    return SCOPE_OVERLAY.get()


def set_scope_overlay(overlay) -> None:
    """Bind ``overlay`` for this context (``None`` unbinds)."""
    SCOPE_OVERLAY.set(overlay)


@contextlib.contextmanager
def bound_scope_overlay(overlay):
    """Bind ``overlay`` for the block, restoring the prior binding after."""
    token = SCOPE_OVERLAY.set(overlay)
    try:
        yield overlay
    finally:
        SCOPE_OVERLAY.reset(token)
