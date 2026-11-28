# Button

Buttons start an action; there are six kinds, and a screen has exactly one primary.

- **Primary** (`sm-btn sm-btn--primary`): the one action the screen exists for — the side panel's "Turn off in Codex". Full width of its panel, `control-lg` tall, `accent` with `on-accent`. May carry its keycap ("Space").
- **Accent** (`sm-btn sm-btn--accent`): the compact form of primary, for a page whose main action sits in a title row, a card or a page footer — "Edit", "Save to 3 places", "Create in 2 places", "Go to Skills". Same colours as Primary, normal width. Use it only where no side panel primary is on screen.
- **Default** (`sm-btn`): outlined, for everyday secondary actions — New skill, filters, Show 50 more, Restore, Check again. Use `aria-pressed` for toggles such as "Show only these".
- **Dark** (`sm-btn sm-btn--dark`): a strong secondary that starts a flow outside this screen — "Fix one by one" in the attention banner. At most one per area.
- **Quiet** (`sm-btn sm-btn--quiet`): text only, for rare or risky actions that should not draw the eye — "Move to Trash", "Empty trash…". Still a real button with a visible focus ring.
- **Icon** (`sm-btn sm-btn--icon`): icon-only, always with `aria-label`. 34px on desktop, 44px on phones.

## Sizes

| Where | Height | How |
|---|---|---|
| Title row or page footer (New skill, Edit, Save, Create, Go to Skills) | `control-page` 38px | add `sm-btn--page` |
| Inside a card, panel, list row or toolbar | `control` 36px | the default |
| The side panel's main action | `control-lg` 46px | `sm-btn--primary` |
| Anything on a phone | at least `touch` 44px | |

Rules: labels start with a verb and name the agent or count when one is involved ("Save to 3 places"). Never two primaries on one screen. A disabled button says why nearby, in words ("Fix the name to continue"). When a button only moves to another page, it can be an `<a class="sm-btn">`. Standard actions carry a 15px icon left of the label (download, upload, restore, refresh, copy, plug, bin), as listed in Iconography. Everyday verbs stay text-only.
