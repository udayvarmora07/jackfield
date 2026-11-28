# Chip

A toggle with a tick, for short, filter-like choices. Choosing places is not done with chips: the New skill page and the Editor both use checkbox rows (see Field). They show each place's mark, name and folder, line up for 5–8 places and leave room for a note.

Use a real `<button class="sm-chip" aria-pressed="true|false">` with a `sm-chip__box` holding a tick icon, then the place's 14px mark (`agm` with `data-a`) and name. Pressed: `accent` box with an `on-accent` tick, `accent-soft` fill, `ink` text. A chip can carry a short tag after the name in `warn` when a place needs care ("· different copy"). Chips sit in a group with a visible label (`role="group"` + `aria-labelledby`). They are 36px tall on desktop and 44px on phones. When each place needs its own note, use Field's checkbox rows instead.
