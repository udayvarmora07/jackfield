"""Command-line entry point for Jackfield (``jackfield``, alias ``skills-mgr``).

Exit codes: 0 on success, 1 on operational errors, 2 on usage errors,
130 on interrupt.  The parser lives in :mod:`skillsmgr.cli_parser` and the
command behavior in :mod:`skillsmgr.cli_handlers`.
"""

from __future__ import annotations

import contextlib
import os

import difflib
import re

from .cli_handlers import (
    COMMANDS,
    cmd_ai,
    cmd_init,
    cmd_list,
    cmd_create,
    cmd_add,
    cmd_view,
    cmd_edit,
    cmd_open,
    cmd_remove,
    cmd_disable,
    cmd_enable,
    cmd_validate,
    cmd_search,
    cmd_import,
    cmd_export,
    cmd_backup,
    cmd_restore,
    cmd_doctor,
    cmd_stats,
    cmd_trash_list,
    cmd_trash_purge,
    cmd_templates_list,
    cmd_templates_new,
    cmd_history,
    cmd_db_rebuild,
    cmd_db_resync,
    cmd_sync,
    cmd_scopes,
    cmd_tokens,
    cmd_install,
    cmd_update,
    cmd_gui,
    EXIT_ERROR,
    EXIT_INTERRUPT,
    EXIT_OK,
    EXIT_USAGE,
    make_store,
    validate_cli_combinations,
    validate_cli_names,
)
from .cli_output import err as _err
from .cli_parser import build_parser as _build_parser
from .errors import SkillNotFound, StoreError
from .context import bound_store
from .cli_ai import validate_args as _validate_ai_args

__all__ = [
    "EXIT_OK",
    "EXIT_ERROR",
    "EXIT_USAGE",
    "EXIT_INTERRUPT",
    "COMMANDS",
    "cmd_ai",
    "build_parser",
    "main",
    "cmd_init",
    "cmd_list",
    "cmd_create",
    "cmd_add",
    "cmd_view",
    "cmd_edit",
    "cmd_open",
    "cmd_remove",
    "cmd_disable",
    "cmd_enable",
    "cmd_validate",
    "cmd_search",
    "cmd_import",
    "cmd_export",
    "cmd_backup",
    "cmd_restore",
    "cmd_doctor",
    "cmd_stats",
    "cmd_trash_list",
    "cmd_trash_purge",
    "cmd_templates_list",
    "cmd_templates_new",
    "cmd_history",
    "cmd_db_rebuild",
    "cmd_db_resync",
    "cmd_sync",
    "cmd_scopes",
    "cmd_tokens",
    "cmd_install",
    "cmd_update",
    "cmd_gui",
]


def build_parser():
    """Build the CLI parser wired to the command handlers."""
    return _build_parser(COMMANDS)


_SKILL_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def _did_you_mean(args, store) -> str:
    """Suggest close library skill names for a missing one, or return ``""``.

    Only the manager's own library is consulted (agent scopes keep their own
    error), and only folder names that pass the skill-name rule are printed,
    so a hostile directory name can never reach the terminal.
    """
    name = getattr(args, "name", None)
    if not isinstance(name, str) or getattr(args, "scope", None) not in (None, "global"):
        return ""
    try:
        names = [p.name for p in store.skills_dir.iterdir()
                 if _SKILL_NAME.fullmatch(p.name) and p.is_dir()]
    except OSError:
        return ""
    close = difflib.get_close_matches(name, names, n=3)
    return f"; did you mean {', '.join(repr(c) for c in close)}?" if close else ""


def _call_with_hint(args, store) -> int:
    """Run the handler, adding a close-name hint to a missing-skill error."""
    try:
        return args.func(args, store) or EXIT_OK
    except SkillNotFound as exc:
        hint = _did_you_mean(args, store)
        if not hint:
            raise
        raise SkillNotFound(f"{exc}{hint}") from exc


def _run(args) -> int:
    validate_cli_names(args)
    validate_cli_combinations(args)
    store = make_store(args)
    # ``global`` resolves through this invocation's Store, not a stale one.
    with bound_store(store):
        return _call_with_hint(args, store)


@contextlib.contextmanager
def _scoped_data_env():
    """Restore ``JACKFIELD_DATA`` after one command.

    ``--data-dir`` reaches the Store through that variable (see
    ``cli_handlers.make_store``); an in-process caller's later commands and
    Stores must resolve their own root again, not this command's.
    """
    saved = os.environ.get("JACKFIELD_DATA")
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop("JACKFIELD_DATA", None)
        else:
            os.environ["JACKFIELD_DATA"] = saved


def _run_scoped(args) -> int:
    with _scoped_data_env():
        return _run(args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_ai_args(parser, args)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return _run_scoped(args)
    except (StoreError, ValueError, OSError) as exc:
        _err(str(exc))
        return EXIT_ERROR
    except KeyboardInterrupt:
        _err("interrupted")
        return EXIT_INTERRUPT
    except Exception as exc:
        _err(f"unexpected error: {exc}")
        return EXIT_ERROR

