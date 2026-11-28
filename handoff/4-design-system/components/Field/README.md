# Field

Inputs for the table filter and for forms: a single-line field, multi-line text, checkboxes and live rules.

- **Single line** (`label.sm-field`): wrap the input in the label with a visually hidden name (`sm-sr`) so the whole box is clickable and announced. The focus ring wraps the whole field. Placeholders give an example ("Filter by name or what it does"), never the only label.
- **Form label and hint** (`sm-label`, `sm-hint`): every form field has a visible label and, when useful, one hint sentence under it ("Agents read this to decide when to pick the skill."), linked with `aria-describedby`.
- **Multi-line** (`sm-textarea`): descriptions. Show a count when there is a limit ("120 of 1,024 characters").
- **File text** (`sm-textarea sm-textarea--file`): the skill's content as it is written in the file, in `file-text` mono. Spell check off.
- **Place rows** (`sm-checkbox` in a label row): the one pattern for choosing places, used by "Save to" in the Editor and "Add it to" on New skill. Each row has a native checkbox, the agent tile, the name, and one line under it: the folder it will write to, or a note on what happens there. Rows stack vertically, because a vertical list scans faster and still lines up at 8 places.
- **Live rules** (`sm-rule`, with `is-ok` / `is-fail`): rules that update as you type, each a short sentence with a tick or cross icon and a hidden "Done:" / "Not yet:" for screen readers. Offer a one-click fix when there is one ("Use explain-code instead").

Errors appear directly under the field in words, never only as a red border.
