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
| Skill page document and Details | `GET /api/skills/<name>?scope=&view=reader&target_path=` | Exact selected folder. Returns current UTF-8 text, rendered-source body, file counts and the personal Claude Code listing estimate where applicable |
| Document for the editor and comparisons | `GET /api/skills/<name>?scope=` | Lazy, cached by scope, name, path and content hash. Comparison reads for same-name instances in one scope match scoped list rows by `physical_path` |
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
| Turn off / on in one place | Checked batch `disable` / `enable` | Check the post-change copy and apply the opposite batch operation |
| Add to a place (Not here) | Checked batch `sync` to an empty destination | Move the added copy to Trash if its folder still matches the installed tree |
| Make match / replace damaged / keep version N | Check the source and destinations, move the existing folders to Trash with a checked batch `remove`, then run a checked non-forced batch `sync` | Move the added copy to Trash and restore its exact previous `trash_path` |
| Several rows at once | `POST /api/batch/preview`, `POST /api/batch/execute` for the relevant checked operations above | One Undo for confirmed results with verified recovery evidence |
| Edit | `PATCH /api/skills/<name>?scope=` per place, with expected folder and content hash | `POST /api/trash/<name>?snapshot=<id>&scope=` with the returned hash and exact snapshot ID |
| Save an edited copy to a missing place | `POST /api/sync` with edit fields, the observed source folder and document hash, and the observed destination roots | `DELETE /api/skills/<name>?scope=` with the returned folder and tree hash, moving the copy to Trash |
| Create | `POST /api/skills?preview=1` returns the serialized file without writing; `POST /api/skills?scope=` writes per chosen place | Move to Trash |
| Move to Trash | `DELETE /api/skills/<name>?scope=&purge=0` | `POST /api/trash/<name>?scope=` |
| Delete forever | `DELETE /api/skills/<name>?scope=&purge=1` | None: say so first |
| Restore | `POST /api/trash/<name>[?scope=]` (+ `trash_path`) | Move to Trash again |
| Empty library trash | `POST /api/trash/purge` | The confirmation explains that the deletion is permanent |
| Library backup / load | `GET /api/export[?full=1]`, `PUT /api/import?filename=&force=&full=&preview=1`, then the same import with `plan_id` in place of `preview` | Load requires a reviewed plan |
| Tracking | `PUT /api/tracking` (whole document, `revision`) | PUT the previous document |
| Check a folder | `POST /api/tracking/check-folder` | Read-only |
| AI tools | the existing `/api/ai/*` routes | Per tool (snapshot provenance for applied edits) |

**[SPEC]** Every JSON `POST` sends `Content-Type: application/json`, even with no
body (415 otherwise). Errors are one shape `{error, code}`; show `error` in
plain words and put `code` under "Technical details". A 409 from tracking is
"These settings changed in another window. Reload to see them."

**[SPEC]** For S1 and S2, re-read the confirmed on-disk state after a write.
Use the batch plans to check the source and destination evidence before
changing the folders. Compare the installed tree before offering a copy Undo.
If the result cannot be verified, ask the user to refresh and check Trash.
Independent filesystem writers can still change a folder between checks.

**[SPEC]** For S4, edited Sync stages the source tree and its edited document
before publishing it into an empty destination. The checked tree allows up
to 256 entries, depth 16, 4 MiB per file and 16 MiB overall, and rejects
links and special files. An occupied destination is refused, including one
created during the save. The undo check covers the document, supporting
files, directory entries and permissions under the destination write lock.

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
| Agents without a settings reader (Cursor, custom agents) | Square rules 7–8 cannot fire; they show On with "settings aren't checked" in the panel (Q1, decided 2026-11-27) | No (frontend rule) |
| "Actually loaded" | Always Unknown with the fixed explanation (S6) | No |
| Undo for a Recent changes row | Library history rows have no exact snapshot or operation identifier. The history list is read-only. Known text snapshots can be restored under History and text snapshots. | No |
| Latest library backup date and size | Store the date and size in browser `localStorage` after Jackfield gives the download to the browser. | No |
| Text size and date format | Browser preferences (`preferences.js`), as today | No |
| A cheap "has anything changed" call | Use the existing list call with `body=0`; add nothing | No; a fingerprint route would need approval |
