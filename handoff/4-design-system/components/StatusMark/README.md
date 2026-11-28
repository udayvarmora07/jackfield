# StatusMark

The six statuses of a skill in one agent, each a shape plus a word: On, Off, Off in settings, Different, Can't read, Not here.

Use `<span class="sm-status is-on"><span class="sm-mk"></span>On</span>` with one of `is-on`, `is-off`, `is-settings`, `is-different`, `is-unreadable`, `is-missing`. The mark is `aria-hidden` decoration; the word carries the meaning. Shapes differ (dot, ring, dashed ring, diamond, cross, dash) so the set works without colour. "Off in settings" must never look like On. When a fact can't be checked, write "unknown" instead of using a mark.
