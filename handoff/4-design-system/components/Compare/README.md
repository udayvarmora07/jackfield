# Compare

Two versions side by side, so a person decides before anything changes.

- **Now / Suggested** (`sm-compare` with two `sm-compare__side`, the new one `sm-compare__side--new`): for a proposed change such as an AI-shortened description. Each side has a caption ("Now", "Suggested") and the full text. The action under it names the target ("Use it for code-review") and ends in Undo.
- **Choose a version** (`<button class="sm-choice" aria-pressed>` with a `sm-choice__snip`): for different copies. Each choice says where it is used and what happens to the other ("Used in 3 places. Codex's change goes to Trash."), with a few lines of the text that differs. **Nothing is preselected**: the action button stays disabled and says "Choose a version first" until a choice is made.

The losing copy always goes to Trash, never away for good.
