# Jackfield — Build progress

## Setup

The local Python server serves the existing Vue interface in
`skillsmgr/webui/`. Phase 0 uses the approved v13 export and canvas v58.
The token generator uses Python's standard library. Its CSS is checked in,
and the app loads fonts, styles and icons from local files.

## Phases

- [x] Phase 0 · Foundations implemented and verified locally. Integration
  and CI are pending.
- [ ] Phase 1 · Shell.
- [ ] Phase 2 · Skills table and side panel (hero).
- [ ] Phases 3–8 · Remaining screens, migration cleanup and acceptance.

## Findings checked in Phase 0

| Finding | Status |
| --- | --- |
| Turned off filter misses skills with a mix of enabled and disabled copies | The filter now checks a skill's copies, including the selected agent when filtered. The skill's overall status is unchanged. |
| Contradiction check misses “Always use tabs” versus “Always use spaces” | The deterministic scanner now recognises those bare directives alongside explicit indentation rules. |
| History card says no changes after an agent-scope save | The card displays library history. Agent-scope saves create snapshots. Explain and surface the correct source on the Phase 3 Skill page. |
| AI Settings says Connected after a refused connection | The legacy badge reads whether a provider is configured. Phase 5 Settings must distinguish configuration from a successful check. |

The component stylesheet comes from the approved 30,447-byte export
(SHA-256 `7d5905e50046893960685ad25170f920c5fb6d3e0d9be710bb9c611c39923296`).
The local copy references the canonical ink token in its agent-mask rule.
Existing nav and page layouts remain in use during Phase 0.

Browser checks run in an empty project folder inside the fixture home. The
checkout's installed project skills would otherwise change counts, search
matches and the targets offered by Add to agent.

## Verification

- Python 3.11–3.14 ran 2,511 tests each, with the platform-dependent skips.
- Chromium passed all 71 browser checks with the isolated fixture, including
  the responsive and theme sweeps. The desktop and phone-width previews
  showed the approved palette, lockup and agent marks.
- Store and web smoke tests passed. The documentation, token generation,
  contrast and complexity checks passed.
- The wheel and source distribution passed the package-data and clean-install
  checks using the pinned build toolchain.
