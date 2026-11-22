# AI UX integration patterns for the Skills Manager (research, 2026-11-22)

Read-only research. Fetched content treated as untrusted data. Claims marked [?] were not confirmed on a primary page in this pass.

## Evidence quality (read first)

- **Fetched and read on a primary page:** Linear Triage Intelligence docs (linear.app/docs/triage-intelligence); Cursor docs (cursor.com/docs/inline-edit/overview, which says Cmd+K "used to open inline edit" and was replaced by Agent); shapeof.ai pattern list (names only; fetched via the site, categories as returned); GitHub changelog entries for Copilot coding agent and code review (via search snippets, dated 2025-2026); Raycast manual (local models, BYOK); Zed docs (inline assistant, edit prediction; via search snippets).
- **Search snippets only:** Apple Writing Tools (Apple newsroom and third-party summaries); Obsidian plugin listings (developer-written, not reviews); v0 / Figma Make (third-party comparison sites).
- **Not verified:** Microsoft HAX 18 guideline list (the fetched page does not enumerate them; only the four stages are confirmed). Google PAIR chapter and pattern names (fetch returned only the title; treat the chapter names below as [?]). NN/g primary AI articles (not reached). Notion AI, Copilot Workspace, JetBrains AI, Warp, Grammarly, Figma AI, Raycast AI Commands, Zed agent panel: not fetched. Cursor inline-edit mechanics: the docs fetch did not describe ghost text or diff controls, and forum posts conflict on whether Cmd+K accept/reject still exists [?].

## Pattern catalog

For each: products, when it works, pitfalls, and application to the Skills Manager.

### 1. Inline ghost suggestion (predict as you type)
- **Products:** Zed Edit Prediction (https://zed.dev/docs/ai/edit-prediction). Two display modes: "eager" (inline unless it conflicts with LSP completions) and "subtle" (only while a modifier key is held). Tab accepts; alt-tab on all platforms.
- **Works when:** the suggestion is cheap to ignore and cheap to accept. Zed frames it as automatic and context-inferred, versus the explicit Inline Assistant.
- **Pitfalls:** constant flicker and noise; conflicts with other completions. Subtle mode exists because eager mode annoys people [?].
- **Skills Manager:** in the SKILL.md editor, ghost-suggest a `description:` line from the body, or a missing "When to use" heading. Default to subtle mode. Ghost text must never write to disk until accepted.

### 2. Selection → inline action (explicit, prompt-driven edit)
- **Products:** Zed Inline Assistant (https://zed.dev/docs/ai/inline-assistant.md): ctrl-enter, can produce several changes at once and send one prompt to several models. Cursor Cmd+K historically (see Cursor docs above; now routed to Agent).
- **Works when:** the scope is a selection the user can see.
- **Pitfalls:** users lose track of what was changed; Cursor's move from inline diff to Agent session review drew complaints in its forums (search snippets, [?] representative).
- **Skills Manager:** select a paragraph in a skill body → "tighten", "add an example", "make the trigger more specific". Scope to the selection, never the whole file.

### 3. Diff with per-hunk accept/reject (review before write)
- **Products:** Cursor Agent diff with per-change keep/undo and "Restore Checkpoint" (https://cursor.com/docs/inline-edit/overview, Agent section); GitHub Copilot coding agent review (https://github.blog/changelog/2025-08-05-copilot-coding-agent-improved-pull-request-review-experience).
- **Works when:** changes are small and reviewable.
- **Pitfalls:** per-change controls disappeared in some Cursor builds; users reported AI edits applying without an approval UI (forum threads, [?]).
- **Skills Manager:** every AI edit to SKILL.md becomes a diff. Accept per hunk. Write only on accept. Keep the filesystem as source of truth: the write is the accept, not a staged buffer in SQLite.

### 4. Undo / version restore for AI changes (provenance + checkpoint)
- **Products:** Cursor "Restore Checkpoint" (docs above); GitHub Copilot session logs: commits carry an `Agent-Logs-Url` trailer back to the session (https://github.blog/changelog/2026-03-20-trace-any-copilot-coding-agent-commit-to-its-session-logs).
- **Works when:** each AI change is one restorable unit tied to the prompt that produced it.
- **Pitfalls:** "Undo All" without per-change undo is a common complaint [?].
- **Skills Manager:** the existing history feature gets an "AI" entry type: prompt, model, accepted hunks, timestamp. One-click restore uses the same path as a manual edit. Store provenance in the history record, not in SKILL.md frontmatter, unless the frontmatter schema change is approved [?].

### 5. Natural-language command bar that maps to app actions, with preview
- **Products:** Linear Cmd/Ctrl+K "Find Suggestions" and triage rules (https://linear.app/docs/triage-intelligence); Raycast AI Commands (https://manual.raycast.com/ai/local-models.md for the local-model path).
- **Works when:** the intent maps to a small set of actions and the result is shown before it runs.
- **Pitfalls:** free-text commands that execute immediately are dangerous. Users struggle to phrase requests (the "articulation barrier", secondhand NN/g [?]).
- **Skills Manager:** "disable every codex skill that mentions Docker" → preview list of affected skills and scopes → confirm. Never execute a bulk mutation from NL without the preview. Offer 3-5 example commands as suggestions.

### 6. Suggested next actions and explain-this
- **Products:** Linear suggestions with reasoning on hover or in a side window (Triage Intelligence docs above); Apple Writing Tools Proofread shows an explanation with each edit (newsroom, search snippet).
- **Works when:** the suggestion comes with a short "why" the user can check in one glance.
- **Pitfalls:** explanations that are generic or wrong. Linear's suggestions take 1-4 minutes to appear on Business plans [from docs].
- **Skills Manager:** Trash view: "Explain what deleting these 5 skills would remove" (what references, which agent scopes, whether a backup exists). Trash is restorable, so say so in the explanation. Validate view: "Why does this skill fail validation?" beside each error.

### 7. Bulk operations by description
- **Products:** Linear triage routing and auto-apply per property, with per-team show/hide/auto-apply (Triage Intelligence docs). Shape of AI "Auto-fill" and "Chained action" (shapeof.ai).
- **Works when:** each affected item is listed and the user can exclude items.
- **Pitfalls:** auto-apply is off by default in most teams [?]; wrong bulk changes are hard to spot.
- **Skills Manager:** "find skills that duplicate this one" → list with similarity reason → per-row accept. Sync or registry install of many skills gets a preview with counts.

### 8. Streaming output
- **Products:** v0 streaming generation with autofixers (Vercel blog, search snippet, [?] details). Zed Agent panel streams tool calls.
- **Works when:** the user can stop or act on partial output.
- **Pitfalls:** partial markdown is written to disk by accident if the save path is wired to the stream.
- **Skills Manager:** stream into a preview pane only. Write nothing until the final diff is accepted. Show a Stop control.

### 9. Cost / time estimate before a run
- **Products:** Shape of AI "Cost estimates" and "Draft mode" (shapeof.ai Governors). Raycast caps local context at 64k tokens (manual).
- **Works when:** the estimate is shown before the spend, and cheaper drafts are available.
- **Pitfalls:** estimates that are wrong. Local models have no per-token cost but do have time cost [?].
- **Skills Manager:** before a multi-skill AI pass, show "N skills, ~X tokens, provider Y, about Z seconds". Offer a dry run that drafts only one skill.

### 10. Provenance labels, disclosure, and citations
- **Products:** Shape of AI "Disclosure", "Footprints", "Citations", "Watermark" (shapeof.ai Trust builders); Copilot agent commits (Agent-Logs-Url).
- **Works when:** the label is per item and visible in lists, not only in detail views.
- **Pitfalls:** a label users learn to ignore. Badges on every row become noise.
- **Skills Manager:** an "AI-drafted" marker on a skill row and in history, plus the source prompt. Citations: when the AI derives content from another skill or registry entry, link to it.

### 11. Confidence and "why this suggestion"
- **Products:** Linear reasoning on hover; PAIR Explainability + Trust chapter [?] (fetch failed; chapter title confirmed only).
- **Works when:** shown as a short reason, not a percentage.
- **Pitfalls:** fake precision. Percent scores users cannot act on.
- **Skills Manager:** duplicate or conflict suggestions show the matching phrase ("both match 'deploy to staging'").

### 12. Feedback (accept/dismiss signals and thumbs)
- **Products:** Linear says suggestions improve as users accept or dismiss them (Product Intelligence preview, Aug 2025, changelog snippet). Thumbs on Copilot review comments (Copilot review overview, [?]).
- **Works when:** the signal is one click and the loop is visible.
- **Pitfalls:** feedback that goes nowhere; signals that are used for training without consent.
- **Skills Manager:** per-suggestion accept/dismiss, stored locally, used only to rank future suggestions on this machine. Say so in the UI.

### 13. Empty-state generation
- **Products:** v0 and Figma Make are prompt-first (search snippets); Shape of AI "Templates" and "Initial CTA" (shapeof.ai Wayfinders).
- **Works when:** the user has a concrete goal and can refine.
- **Pitfalls:** blank-canvas prompt boxes that stall.
- **Skills Manager:** the empty library shows "Create a skill from a description" with three templates (research, code review, deploy). Import from a registry or a folder is the other option.

### 14. Background agent tasks with notifications
- **Products:** GitHub Copilot cloud agent sessions with logs and draft PRs (changelog entries, 2026); Linear agent sessions triggered by mention (Linear changelog, Sept 2025).
- **Works when:** the task is long and has a clear finish state.
- **Pitfalls:** users forget running jobs; notifications are noisy.
- **Skills Manager:** backup, registry refresh, or a bulk AI review runs as a background job. Show a single notification with a link to the result. Email-style notifications are out of scope.

### 15. Local / private model toggle and data-flow indicator
- **Products:** Raycast local models through Ollama; requests go straight to the local server; BYOK changes in v2 require Pro (manual.raycast.com). Obsidian plugin listings warn that a local URL does not make a remote model private, and that a remote base URL sends prompts (listings, developer-written).
- **Works when:** the indicator says where the data goes, per action.
- **Pitfalls:** a "local" label that points to a remote host. Users assume privacy.
- **Skills Manager:** a per-feature provider setting that shows "local (127.0.0.1:11434)" or "remote (host)". Refuse to send skill bodies to a remote host without the user choosing it for that action. Note that the local web UI is unauthenticated on 127.0.0.1, so the localhost binding is the only boundary; any model endpoint it calls must not be exposed.

### 16. AI off switch and graceful degradation
- **Products:** Shape of AI "Controls" (Governors); Linear's setting is per workspace and per team (Triage Intelligence docs).
- **Works when:** one switch hides every AI affordance and nothing breaks.
- **Pitfalls:** AI-only features with no non-AI path.
- **Skills Manager:** a global AI toggle in settings. With it off, every AI button disappears and deterministic features (search, validate, diff) still work.

### 17. Inline AI in a text editor as an overlay on existing controls (no separate AI page)
- **Products:** Apple Writing Tools appear in the system text menu across apps (newsroom); Grammarly and Obsidian plugins use the same pattern [?].
- **Works when:** the AI affordance sits where the user already works.
- **Pitfalls:** a separate chat page is where people go to forget the feature exists.
- **Skills Manager:** AI actions live in each existing view's toolbar: list (bulk), editor (selection), trash (explain), history (restore), search (NL query), install (preview). No new top-level AI page.

## Design-guidance anchors

- **Microsoft HAX Guidelines for Human-AI Interaction** (CHI 2019): 18 guidelines in four stages, confirmed: initial interaction, during interaction, when the system is wrong, over time (https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/). Confirmed by search snippet: G1 make clear what the system can do; G14 update cautiously; G15 granular feedback; G16 convey consequences of actions; G17 global controls; G18 notify users about changes. Other numbers: [?]. The HAX Design Library is at https://www.microsoft.com/en-us/haxtoolkit/library/.
- **Google PAIR People + AI Guidebook:** chapters include Explainability + Trust and Feedback + Control (https://pair.withgoogle.com/guidebook/). Specific patterns: [?].
- **Shape of AI** (https://www.shapeof.ai): six categories, confirmed from the fetched page: Wayfinders, Inputs, Tuners, Governors, Trust builders, Identifiers. Governors include Action plan, Cost estimates, Draft mode, Stream of Thought, Verification, Variations, Footprints, Controls.
- **NN/g:** primary AI articles not reached. Secondhand claim: waits over about 10 seconds need a progress indicator [?].

## Constraints from this repo (AGENTS.md)

- Adding a new CLI command, a Store method, or a SQLite schema change needs approval. An AI feature that needs its own endpoint or stored suggestions therefore needs a decision first.
- Stdlib only; no new runtime deps. A provider call must be a stdlib HTTP client or a local Ollama call.
- Filesystem is the source of truth. AI results are proposals until written.

## Suggested order

1. Diff + per-hunk accept + history provenance (patterns 3, 4). Highest value, no new dependencies.
2. Explain-this in Trash and Validate (6).
3. NL command bar with preview, read-only first (5).
4. Local/remote indicator and global off switch (15, 16) before any remote call.
5. Background bulk review (14), last.
