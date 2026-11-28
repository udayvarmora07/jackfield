# Square

One cell of the Skills table: one skill in one agent, shown as a StatusMark inside a button.

A square is a real `<button class="sm-square">` at least `square` (64px) tall, with an `aria-label` that reads the whole fact ("code-review in Codex: On"). Clicking selects it (`aria-pressed="true"`: `accent-soft` fill and an `accent` inset outline) and fills the SidePanel. Arrow keys move between squares; Space runs the panel's primary action. A square never changes its status until the change has really happened on disk.
