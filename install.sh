#!/bin/sh
# One-command installer for skills-manager (PyPI: skill-control-plane).
#
#   curl -fsSL https://raw.githubusercontent.com/udayvarmora07/skills-manager/main/install.sh | sh
#
# Pass options after `sh -s --`, for example:
#
#   curl -fsSL .../install.sh | sh -s -- --with-tiktoken
#   curl -fsSL .../install.sh | sh -s -- --uninstall
#
# What it does, in order of preference:
#   1. `uv tool install`  when uv is on PATH (uv also supplies Python >= 3.11),
#   2. `pipx install`     when pipx is on PATH,
#   3. a private virtual environment plus a `skills-mgr` link in ~/.local/bin,
#      using the first Python >= 3.11 it finds.
#
# What it never does: run as root on purpose, edit your shell start-up files,
# download another installer, or touch your skills or the manager's data
# directory (~/.local/share/skills-manager). Uninstall leaves that data in place.
#
# The whole script is a function called on the last line, so a download cut
# short cannot run half of it.

set -eu

DIST="skill-control-plane"
COMMAND="skills-mgr"
SOURCE_ARCHIVE="https://github.com/udayvarmora07/skills-manager/archive/refs/heads/main.tar.gz"
VENV_OWNER="skill-control-plane venv 1"

usage() {
    cat <<'EOF'
Install skills-manager (the `skills-mgr` command) in one step.

Usage: install.sh [options]

  --method M        uv, pipx or venv (default: the first one available)
  --version V       install this PyPI release instead of the latest
  --source          install the current GitHub main branch instead of PyPI
  --from SPEC       install from any pip spec: a local checkout, a URL, a wheel
  --with-tiktoken   also install tiktoken for exact token counts
                    (it downloads one encoding file the first time it is used)
  --prefix DIR      venv method: where the environment lives
                    (default: $XDG_DATA_HOME/skill-control-plane/venv)
  --bin-dir DIR     venv method: where the skills-mgr link goes
                    (default: ~/.local/bin)
  --dry-run         print the commands, change nothing
  --uninstall       remove what this script installed (your skills stay)
  -h, --help        show this help

Environment: SKILLS_MGR_INSTALL_METHOD, SKILLS_MGR_INSTALL_PREFIX and
SKILLS_MGR_INSTALL_BIN_DIR set the same defaults as the options above.
EOF
}

say() { printf '%s\n' "skills-mgr install: $*"; }
die() { printf '%s\n' "skills-mgr install: error: $*" >&2; exit 1; }

# Print a command quoted, then run it unless this is a dry run.
run() {
    printf '+'
    for arg in "$@"; do
        case "$arg" in
            *[!A-Za-z0-9_./:=+@%^,-]*|'') printf " '%s'" "$(printf '%s' "$arg" | sed "s/'/'\\\\''/g")" ;;
            *) printf ' %s' "$arg" ;;
        esac
    done
    printf '\n'
    if [ "$DRY_RUN" = 0 ]; then
        "$@"
    fi
}

have() { command -v "$1" >/dev/null 2>&1; }

find_python() {
    for candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
        if have "$candidate" && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

pick_method() {
    if [ -n "$METHOD" ]; then
        return 0
    fi
    if have uv; then
        METHOD=uv
    elif have pipx; then
        METHOD=pipx
    else
        METHOD=venv
    fi
}

venv_bin() {
    # Windows-style layouts (Git Bash, MSYS) put scripts in Scripts/.
    if [ -d "$PREFIX/Scripts" ] && [ ! -d "$PREFIX/bin" ]; then
        printf '%s' "$PREFIX/Scripts"
    else
        printf '%s' "$PREFIX/bin"
    fi
}

owned_launcher() {
    [ -L "$link" ] || return 1
    target_path=$(readlink "$link") || return 1
    case "$target_path" in
        "$PREFIX/bin/$COMMAND"|"$PREFIX/Scripts/$COMMAND") return 0 ;;
    esac
    return 1
}

venv_config() {
    [ ! -L "$PREFIX/pyvenv.cfg" ] && [ -f "$PREFIX/pyvenv.cfg" ]
}

marked_venv() {
    [ ! -L "$marker" ] && [ -f "$marker" ] && printf '%s\n' "$VENV_OWNER" | cmp -s "$marker" -
}

legacy_venv() {
    venv_config && owned_launcher && [ ! -L "$target_path" ] && [ -f "$target_path" ] && [ -x "$target_path" ]
}

check_launcher() {
    if [ -L "$link" ]; then
        owned_launcher || die "$link points to a different installation; pass --bin-dir"
    elif [ -e "$link" ]; then
        die "$link exists and is not a link; remove it or pass --bin-dir"
    fi
}

mark_venv() {
    say "recording virtual environment ownership in $marker"
    if [ "$DRY_RUN" = 0 ]; then
        (umask 077; set -C; printf '%s\n' "$VENV_OWNER" > "$marker")
    fi
}

lock_venv() {
    [ "$DRY_RUN" = 0 ] || return 0
    lock_dir="$PREFIX.skills-manager-lock"
    mkdir "$lock_dir" || die "could not lock $PREFIX; check for another installer using this directory"
    trap 'rmdir "$lock_dir"' EXIT
    trap 'exit 1' HUP INT TERM
}

install_uv() {
    set -- uv tool install --force --python '>=3.11'
    if [ "$WITH_TIKTOKEN" = 1 ]; then
        set -- "$@" --with tiktoken
    fi
    run "$@" "$SPEC"
}

install_pipx() {
    python=$(find_python) || python=""
    if [ -n "$python" ]; then
        run pipx install --force --python "$python" "$SPEC"
    else
        run pipx install --force "$SPEC"
    fi
    if [ "$WITH_TIKTOKEN" = 1 ]; then
        run pipx inject "$DIST" tiktoken
    fi
}

install_venv() {
    python=$(find_python) || die "no Python 3.11 or newer found. Install one, or install uv
(https://docs.astral.sh/uv/) and run this script again: uv fetches Python for you."
    say "using $python"
    [ ! -L "$PREFIX" ] || die "$PREFIX is a link; choose a virtual environment directory"
    check_launcher
    run mkdir -p "$(dirname "$PREFIX")"
    lock_venv
    if [ -L "$PREFIX" ]; then
        die "$PREFIX is a link; choose a virtual environment directory"
    elif [ -e "$PREFIX" ]; then
        if ! marked_venv; then
            if [ ! -d "$PREFIX" ] || ! venv_config; then
                die "$PREFIX exists and is not a virtual environment; refusing to touch it"
            fi
            legacy_venv || die "$PREFIX does not belong to Skills Manager; choose a different --prefix"
            mark_venv
        fi
    else
        run mkdir "$PREFIX"
        mark_venv
    fi
    if ! venv_config; then
        [ ! -e "$PREFIX/pyvenv.cfg" ] && [ ! -L "$PREFIX/pyvenv.cfg" ] || die "$PREFIX/pyvenv.cfg is not a regular file"
        if ! run "$python" -m venv "$PREFIX"; then
            die "could not create a virtual environment. On Debian or Ubuntu, install the
python3-venv package, or install uv or pipx, then run this script again."
        fi
    fi
    bin=$(venv_bin)
    set -- "$bin/python" -m pip install --upgrade --disable-pip-version-check "$SPEC"
    if [ "$WITH_TIKTOKEN" = 1 ]; then
        set -- "$@" tiktoken
    fi
    run "$@"
    target="$bin/$COMMAND"
    if [ "$DRY_RUN" = 0 ]; then
        [ -f "$target" ] && [ -x "$target" ] || die "the package did not install a $COMMAND launcher"
    fi
    check_launcher
    if ! owned_launcher; then
        run mkdir -p "$BIN_DIR"
        # os.symlink refuses an occupied path, including a directory symlink.
        run "$python" -I -c 'import os, sys; os.symlink(sys.argv[1], sys.argv[2])' "$target" "$link"
    fi
}

uninstall() {
    removed=0
    if [ "$METHOD" = "" ] || [ "$METHOD" = uv ]; then
        if have uv && uv tool list 2>/dev/null | grep -q "^$DIST "; then
            run uv tool uninstall "$DIST"
            removed=1
        fi
    fi
    if [ "$METHOD" = "" ] || [ "$METHOD" = pipx ]; then
        if have pipx && pipx list --short 2>/dev/null | grep -q "^$DIST "; then
            run pipx uninstall "$DIST"
            removed=1
        fi
    fi
    if [ "$METHOD" = "" ] || [ "$METHOD" = venv ]; then
        if [ -e "$PREFIX" ] || [ -L "$PREFIX" ] || owned_launcher; then
            if [ -d "$(dirname "$PREFIX")" ]; then
                lock_venv
            fi
        fi
        if [ ! -L "$PREFIX" ] && { marked_venv || legacy_venv; }; then
            if owned_launcher; then
                run rm -f "$link"
            fi
            run rm -rf "$PREFIX"
            removed=1
        elif [ -e "$PREFIX" ] || [ -L "$PREFIX" ]; then
            say "leaving $PREFIX alone: ownership could not be verified"
        elif owned_launcher; then
            run rm -f "$link"
            removed=1
        elif [ -L "$link" ]; then
            say "leaving $link alone: it points to a different installation"
        fi
    fi
    if [ "$removed" = 0 ]; then
        say "nothing installed by this script was found"
    else
        say "removed. Your skills and the manager's data directory were not touched."
    fi
}

verify() {
    if [ "$DRY_RUN" = 1 ]; then
        say "dry run: nothing was changed"
        return 0
    fi
    found=""
    if [ "$METHOD" = venv ]; then
        found="$BIN_DIR/$COMMAND"
    elif have "$COMMAND"; then
        found=$(command -v "$COMMAND")
    fi
    if [ "$METHOD" = venv ]; then
        version_text=$("$found" --version) || die "$found failed its version check"
        say "installed: $version_text"
    elif [ -n "$found" ] && [ -x "$found" ]; then
        say "installed: $("$found" --version)"
    else
        say "installed, but $COMMAND is not on your PATH yet"
    fi
    if ! have "$COMMAND"; then
        case "$METHOD" in
            uv) say "run 'uv tool update-shell' once, then open a new terminal" ;;
            pipx) say "run 'pipx ensurepath' once, then open a new terminal" ;;
            venv) say "add this line to your shell start-up file: export PATH=\"$BIN_DIR:\$PATH\"" ;;
        esac
    fi
    cat <<'EOF'

Next steps:
  skills-mgr scopes        # see every agent's skill folder this tool found
  skills-mgr doctor        # health check, changes nothing
  skills-mgr webui         # open the local web UI on 127.0.0.1

Docs: https://github.com/udayvarmora07/skills-manager#readme
EOF
}

main() {
    METHOD="${SKILLS_MGR_INSTALL_METHOD:-}"
    data_home="${XDG_DATA_HOME:-${HOME:?HOME is not set}/.local/share}"
    PREFIX="${SKILLS_MGR_INSTALL_PREFIX:-$data_home/skill-control-plane/venv}"
    BIN_DIR="${SKILLS_MGR_INSTALL_BIN_DIR:-$HOME/.local/bin}"
    VERSION=""
    SPEC=""
    WITH_TIKTOKEN=0
    DRY_RUN=0
    UNINSTALL=0

    while [ $# -gt 0 ]; do
        case "$1" in
            --method) [ $# -ge 2 ] || die "--method needs a value"; METHOD=$2; shift 2 ;;
            --method=*) METHOD=${1#*=}; shift ;;
            --version) [ $# -ge 2 ] || die "--version needs a value"; VERSION=$2; shift 2 ;;
            --version=*) VERSION=${1#*=}; shift ;;
            --source) SPEC="$SOURCE_ARCHIVE"; shift ;;
            --from) [ $# -ge 2 ] || die "--from needs a value"; SPEC=$2; shift 2 ;;
            --from=*) SPEC=${1#*=}; shift ;;
            --with-tiktoken) WITH_TIKTOKEN=1; shift ;;
            --prefix) [ $# -ge 2 ] || die "--prefix needs a value"; PREFIX=$2; shift 2 ;;
            --prefix=*) PREFIX=${1#*=}; shift ;;
            --bin-dir) [ $# -ge 2 ] || die "--bin-dir needs a value"; BIN_DIR=$2; shift 2 ;;
            --bin-dir=*) BIN_DIR=${1#*=}; shift ;;
            --dry-run) DRY_RUN=1; shift ;;
            --uninstall) UNINSTALL=1; shift ;;
            -h|--help) usage; exit 0 ;;
            *) die "unknown option: $1 (try --help)" ;;
        esac
    done

    case "$METHOD" in
        ''|uv|pipx|venv) ;;
        *) die "--method must be uv, pipx or venv, got '$METHOD'" ;;
    esac
    if [ -n "$VERSION" ]; then
        [ -z "$SPEC" ] || die "--version cannot be combined with --source or --from"
        case "$VERSION" in
            *[!0-9A-Za-z.+!-]*|-*) die "invalid --version '$VERSION'" ;;
        esac
        SPEC="$DIST==$VERSION"
    fi
    [ -n "$SPEC" ] || SPEC="$DIST"
    case "$SPEC" in
        -*) die "a package spec cannot start with '-'" ;;
    esac
    case "$PREFIX" in /*) ;; *) PREFIX="$(pwd)/$PREFIX" ;; esac
    case "$BIN_DIR" in /*) ;; *) BIN_DIR="$(pwd)/$BIN_DIR" ;; esac
    while [ "$PREFIX" != "${PREFIX%/}" ]; do PREFIX=${PREFIX%/}; done
    case "$PREFIX" in ''|*/.|*/..) die "--prefix needs a virtual environment directory" ;; esac
    marker="$PREFIX/.skills-manager-install"
    link="$BIN_DIR/$COMMAND"

    if [ "$(id -u 2>/dev/null || echo 1)" = 0 ] && [ "$DRY_RUN" = 0 ]; then
        say "warning: running as root installs for root only; you probably want your own user"
    fi

    if [ "$UNINSTALL" = 1 ]; then
        uninstall
        return 0
    fi

    pick_method
    case "$METHOD" in
        uv) have uv || die "uv is not on PATH" ;;
        pipx) have pipx || die "pipx is not on PATH" ;;
    esac
    say "installing $SPEC with $METHOD"
    "install_$METHOD"
    verify
}

main "$@"
