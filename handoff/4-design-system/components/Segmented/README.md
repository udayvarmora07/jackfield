# Segmented

A small switch between two or three views of the same thing: Read / File text on the skill page, Write / Preview in the editor, Light / Dark / Match my computer in Settings.

Wrap `sm-btn` buttons in `<div class="sm-seg" role="group" aria-label="View">`; the current one has `aria-pressed="true"` (accent outline on `accent-soft`). It switches what is shown, never changes files, so it needs no Undo. The theme switch shows sun, moon and monitor icons (`data-i`) beside its words. Keep labels to one or two words and never more than three options; for more, use a select.
