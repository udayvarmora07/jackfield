# ChecksGrid

A step-by-step answer to "why isn't this working?": checks down the side, places across the top, one result per cell.

Each cell is a `sm-chk` with an icon (`sm-chk__ic`) and a word, in four states:

| State | Class | Icon | Word |
|---|---|---|---|
| Checked and fine | `is-ok` | tick on `accent-soft` | Yes / On |
| Fails here | `is-fail` | cross on `bad-soft`, word in `bad` 600 | Turned off / No copy here |
| Unknown | `is-unknown` | dashed ring with "?" | Unknown |
| Not checked yet | `is-skip` | empty ring | — |

Order checks the way a problem flows (Found → Readable → Switched on → Settings allow it → Actually loaded); after a failure, later checks show `is-skip`. **Unknown is a real answer**: use it when the app cannot verify something, never guess and never borrow `is-ok`. Above the grid, turn the first failure into one next step with one action ("Open the settings file"). Always show the legend.
