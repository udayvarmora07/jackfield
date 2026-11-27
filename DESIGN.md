# Jackfield design system

Jackfield uses the approved Paper design. Its canonical values live in
[design/tokens.json](design/tokens.json). Regenerate the shipped sheet with
`python3 tools/gen_tokens.py`. The web UI loads that sheet, the approved v13
component bundle, and the layout stylesheet, then the existing page styles.
Use the wire-up and screen decisions in the
[redesign spec](docs/61-redesign-build-spec-2026-11-27.md).

## Voice and status

- Use plain verbs and say which agent or folder an action affects.
- Use the one accent for On, focus and primary actions. Use warning and error
  colors alongside a word or shape. The faint shape token is for marks only.
- Distinguish Off, Off in settings, Not here, Different, Can't read and
  Unknown. Report what the file and known settings establish.
- For changes to another copy, show the effect before the change and use the
  Undo bar when undo is available.

## Components and type

- Use the `sm-*` components described in the
  [component spec](docs/redesign-build/03-components.md).
- Use local IBM Plex Sans for interface text and IBM Plex Mono for paths,
  keycaps and exact file contents. Keep focus visible and check both themes.
- Agent marks are monochrome and decorative. Put the agent name beside its mark.
- During migration, existing pages resolve their previous CSS property names
  through aliases. Use canonical tokens for new work. Phase 7 removes the
  migration aliases.
