# Backend and API for the Redesign

**Version 1.0.0**

**AI manifest**: Which existing REST routes serve each redesign action, what the
UI derives on the client, and the gaps. The redesign is planned as a
**frontend-only** build: no new route, Store method, CLI command or schema
change. Route facts were read from `docs/08-web-ui.md` and the calls `app.js`
makes today (2026-11-27). The full REST reference stays in @docs/08-web-ui.md.

## Rule

**[SPEC]** If a screen seems to need something the API does not give, first try
to derive it from existing responses (`model.js`). Only if that is impossible:
stop, write the gap into @docs/redesign-build/09-open-questions-and-risks.md,
and ask the maintainer before adding a route (AGENTS.md "ASK before"). Any
`webapp.py` change runs `python3 smoke_web.py`; any `store.py` change runs
`python3 smoke_store.py`.

## Reads

**[SPEC]**

| Need | Route | Notes |
|---|---|---|
| All copies for the table | `GET /api/skills?scope=all&body=0` | `content_hash`, `enabled`, `description`, `tokens`, `physical_path`, scope, `native_state`, instance state. Already filtered by tracking on the server |
| Columns, folders, counts | `GET /api/scopes` | Tracked scopes only; the showing project only |
| One document | `GET /api/skills/<name>?scope=` | Lazy, cached by `scope+name+content_hash` (`ensureBodies`) |
| Same-name instances in a recursive scope | `GET /api/skills?scope=<s>&q=<name>` | Matched by `physical_path` (existing behaviour) |
| History | `GET /api/history?limit=&name=&scope=&snapshots=1` | S3 details, S8 recent changes, Undo of edits |
| Trash | `GET /api/trash[?scope=]` | S8 |
| Templates | `GET /api/templates`, `GET /api/templates/<id>` | S5 |
| Why isn't it running | `GET /api/doctor?explain=<consumer>&skill=<name>[&project=]` | S6, S2 Unknown |
| Setup check | `GET /api/doctor?scope=all&hygiene=1` | Doctor tool; S7 "what was checked" |
| Tracking | `GET /api/tracking` | S14–S19, S1 doorways, notices |
| Workspaces | `GET /api/workspaces` | Where agents look |
| AI settings | `GET /api/ai/settings` | S11, AI tool pages |

## Writes

**[SPEC]**

| Action | Route | Undo |
|---|---|---|
| Turn off / on in one place | `POST /api/skills/<name>/disable?scope=` / `…/enable?scope=` | The opposite call |
| Add to a place (Not here) | `POST /api/sync {name, from_scope, to_scopes:[…]}` | Move the new copy to Trash (`DELETE /api/skills/<name>?scope=&purge=0`) |
| Make match / replace damaged / keep version N | `POST /api/sync {…, force:true}` → `replaced_to_trash` map | Restore each replaced copy from Trash (`POST /api/trash/<name>?scope=` with its `trash_path`) |
| Several rows at once | `POST /api/batch/preview`, `POST /api/batch/execute` | Per the batch plan's inverse (existing) |
| Edit | `PATCH /api/skills/<name>?scope=` per place | `POST /api/trash/<name>?snapshot=<id>&scope=` (existing snapshot rollback) |
| Create | `POST /api/skills?scope=` per place | Move to Trash |
| Move to Trash | `DELETE /api/skills/<name>?scope=&purge=0` | `POST /api/trash/<name>?scope=` |
| Delete forever | `DELETE /api/skills/<name>?scope=&purge=1` | None: say so first |
| Restore | `POST /api/trash/<name>[?scope=]` (+ `trash_path`) | Move to Trash again |
| Empty trash | `POST /api/trash/purge` | None: say so first |
| Backup / load | `GET /api/export[?full=1]`, `PUT /api/import?filename=&force=&full=` | Load shows its plan first |
| Tracking | `PUT /api/tracking` (whole document, `revision`) | PUT the previous document |
| Check a folder | `POST /api/tracking/check-folder` | Read-only |
| AI tools | the existing `/api/ai/*` routes | Per tool (snapshot provenance for applied edits) |

**[SPEC]** Every JSON `POST` sends `Content-Type: application/json`, even with no
body (415 otherwise). Errors are one shape `{error, code}`; show `error` in
plain words and put `code` under "Technical details". A 409 from tracking is
"These settings changed in another window. Reload to see them."

## What the client derives

**[SPEC]** Kept in `model.js`, pure and tested:

- **Rows and columns:** group copies by skill name; columns = tracked scopes in
  the order of `GET /api/scopes`; the showing project's scopes as one "This
  project" column.
- **Square status, verdict, attention items:** the rules in
  @docs/redesign-build/04-frontend-architecture.md.
- **Previews:** "12 lines, 1 extra file" from the source copy's body and file
  list; Different / Compare diffs from the two bodies (`diffLines`, existing);
  Now → After from the status rules.
- **Skill list space:** "Uses about 2% of Claude's skill list space" from
  `tokens` and the listing budget the backend already reports (`hygiene`
  listing budget); never show the raw numbers in main text.
- **Changed on disk:** compare `(scope, name, content_hash, enabled)` between
  reads.

## Known gaps and how this spec handles them

**[SPEC]**

| Gap | Handling | Needs approval? |
|---|---|---|
| Agents without a settings reader (Cursor, custom agents) | Square rules 7–8 cannot fire; Q1 decides On vs Unknown | No (frontend rule) |
| "Actually loaded" | Always Unknown with the fixed explanation (S6) | No |
| "Recent changes" undo for older history rows | Offer Undo only where a snapshot id exists in `/api/history?snapshots=1`; others are read-only lines | No |
| "Last one: 20 Nov" for backups | The app does not record backup downloads today; omit the line unless a local preference stores the last download time (browser `localStorage`, per browser) | No; if a server record is wanted, it is new scope (ask) |
| Text size and date format | Browser preferences (`preferences.js`), as today | No |
| A cheap "has anything changed" call | Use the existing list call with `body=0`; add nothing | No; a fingerprint route would need approval |
