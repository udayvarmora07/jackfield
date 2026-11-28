# Build notes: where the code is and the rules it must keep

The build has not started. There is no `build-progress.md`, `ux-review.md` or `launch-plan.md` yet. This page lists only pointers into the repository, plus facts checked there on 2026-11-26. It contains no code.

## Where the code lives

| What | Where |
|---|---|
| Repository | this checkout (`skills-manager/`), one level up from `handoff/` |
| Web UI backend (stdlib HTTP server, REST API) | `skillsmgr/webapp.py` |
| Web UI frontend (Vue 3, vendored, no build step) | `skillsmgr/webui/`: `index.html`, `domain.js` (loads before `app.js`), `app.js`, `styles.css`, `tools.css` and the other `*.js` files |
| Vendored libraries | `skillsmgr/webui/static/vendor/`: `vue.global.prod.js` (sha256-pinned, SEC-9), `markdown-it.umd.min.js` and its licences |
| Bundled fonts | `skillsmgr/webui/static/fonts/`: Plex Sans 400 variable (latin, latin-ext), Plex Mono 400/500/600 (latin, latin-ext) |
| Logo | `skillsmgr/webui/logo.svg` |
| Web UI docs (architecture, REST API, frontend map) | `docs/08-web-ui.md` |
| Repo rules | `AGENTS.md` (and `CLAUDE.md`, which points to it) |

## How to run and check it

From the repository root (commands from `AGENTS.md`):

```bash
python3 -m skillsmgr webui
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

```bash
python3 smoke_web.py
```

```bash
python3 check_design_tokens.py
```

```bash
python3 check_package_data.py
```

`smoke_web.py` must run after any change to `webapp.py`, and `smoke_store.py` after any change to `store.py`. CI also runs `tools/e2e_v2` in headless Chrome.

## Rules the redesign must keep (locked in `AGENTS.md`)

1. The filesystem stays the source of truth. SQLite is a rebuildable index; never trust it over the files.
2. The SQLite schema and `SCHEMA_VERSION` stay unchanged.
3. The CLI stays stdlib-only.
4. Web UI: stdlib backend, **no build step, no new runtime dependencies**, Vue vendored in the repository, binds **127.0.0.1** by default and works offline. The localhost binding is the only security boundary.
5. No new CLI commands or Store methods without approval. Ask before deleting or trashing data or switching the UI framework.
6. Update `task.md` and `docs/06-progress-log.md` after each change, and run the hostile self-review in `AGENTS.md` before calling anything done.

## What the design asks of the build

- **Tokens.** Take colours, type, spacing, radii, shadows and sizes from `../4-design-system/tokens.json`. `tokens.css` next to it is generated from the same file. Light and dark are both first-class.
- **Components.** Use the `sm-*` classes in `../4-design-system/components/bundle.css` and each component's `README.md`. Where the artboards use local names (`tick`, `seg`, `choice`, `chk`), use the system names (`decisions.md` row 36).
- **Fonts: IBM Plex Sans and Plex Mono, bundled, never Google Fonts.** The app runs offline on 127.0.0.1. The woff2 files are already in `static/fonts/` and `check_package_data.py` already checks they exist. Still to do (`open-questions.md` #5):
  - ship the SIL OFL 1.1 licence text with them (a copy is in `../3-ui/prototype/fonts/OFL-IBM-Plex.txt`);
  - add `@font-face` rules for the Mono latin-ext files;
  - keep `package-data` in `pyproject.toml` (`webui/static/fonts/*`) and the `check_package_data.py` assertions in step.
  - Build only with the pinned, hash-verified toolchain (`requirements-build.txt`, SEC-8). The artefact must not ship `tests/`, `docs/`, `.env`, a database or bytecode (SEC-13).
- **Agent marks.** One colour (`ink-2`), drawn through a CSS mask from inline SVG data URIs (the `[data-a="CC"]` rules in `bundle.css`):
  - Claude Code and OpenCode: their own logos from **simple-icons 16.36.0**.
  - Codex: a neutral terminal icon (`decisions.md` row 45).
  - Shared folder: a folder. This project: code brackets.
  - Cursor, Gemini and Command Code have no mark yet (`open-questions.md` #2).
  - Marks are `aria-hidden`. The place name always sits beside them.
- **The old look must go in one change.** `styles.css`, `DESIGN.md` and `check_design_tokens.py` are tied together (`open-questions.md` #4).
- **Order of work** (requirements A10): bugs first (wrong status, silent overwrite, broken tools, off-screen errors), then the four everyday jobs, then all other pages.
