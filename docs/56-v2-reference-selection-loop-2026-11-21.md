# Skills Manager v2 Reference Selection Loop

**Version 1.0.0**

**AI manifest**: The second selection of UI and frontend references, requested
after the first references were rejected. Start here for the current shortlist,
primary-source checks and limits on which patterns transfer to the local app.

[Editable Draw.io shortlist](design/v2-reference-study/skills-manager-reference-shortlist.drawio).

## Shortlist

**[NOTE]** Zed Extensions is the visual lead for the skill shelf and registry.
Obsidian Community's Importer page supplies the install-review information
hierarchy. Playwright Trace Viewer supplies the evidence interaction for Quality
and Sync map. GitButler Operations History supplies the Recovery composition.
Each reference solves a specific task. Skills Manager's existing warm-paper
theme, typography and contrast decisions remain the product baseline.
[Current v2 interface](08-web-ui.md#the-interface-).
[Prior styling decisions](53-apm-and-interface-decisions-2026-11-20.md).

| Reference | What earned its place | Work it informs |
|---|---|---|
| [Zed Extensions](https://zed.dev/extensions?query=docker) | A distinctive developer-facing visual language with visible search, familiar category names, compact entries and a recoverable empty result | Skills shelf, registry search and tool browse |
| [Obsidian Community Importer](https://community.obsidian.md/plugins/obsidian-importer) | Identity and origin remain visible while users switch between overview, evidence and release history | Skill reader and install/update review |
| [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer) | Selecting one event anchors the corresponding evidence, including the actual states before and after it | Quality findings and exact-copy comparison |
| [GitButler Operations History](https://docs.gitbutler.com/features/timeline) | Dated events, a stable preview pane and a deliberate restore action give history a concrete purpose | Recovery and whole-folder snapshots |

## Pass 1 — Find candidates close to the job

**[NOTE]** On 2026-11-21, searched five task families rather than one visual
style: find by name or intent, inspect before adding, separate missing and
partial evidence, compare two files, and recover an exact item. Screened
public product UIs, official captures and source repositories. The
gallery searches focused on these workflows. Kept a candidate in the loop
only if it solved one of the tasks or exposed a design tradeoff worth testing.

| Discovery source | What was inspected | Decision |
|---|---|---|
| [Awwwards](https://www.awwwards.com/) | MCP productivity search results skewed toward brand and portfolio sites | Useful for composition leads. The returned results did not qualify as operational references |
| [Godly / Recent Design](https://recent.design/i/qvrzk65-css-anchor-filter-dot) | MCP filter search and Petr Knoll's filter-indicator clip | Useful for seeing whether a category stays visibly selected. A short concept clip cannot establish keyboard behavior, empty states or mobile overflow |
| [Inspo](https://inspomcp.dev/about) | MCP search surfaced captures including daisyUI and Tailwind UI | Useful for typography and spacing comparisons. Landing captures provided weaker workflow evidence than the live directories |
| [Refero](https://refero.design/) | Public research page and its Filter & Sorting collection entry | Useful for finding comparable screens. This pass did not verify a complete selected flow from the collection |
| [Component Gallery](https://component.gallery/components/empty-state/) | Public empty-state examples, usage guidance and filters for implementation evidence | Useful for comparing the wording and available next action for different empty states |
| [Mobbin](https://mobbin.com/explore/web/latest) | Public library entry point | No particular Mobbin flow was verified, so no selection claim rests on it |

## Pass 2 — Walk through the workflows

**[NOTE]** Desktop and phone evidence came from isolated agent-browser
sessions using installed Chrome 158. Desktop inspections used widths around
1440 CSS px, and phone observations below used 390 CSS px. Comparisons refer
to the exact page and state exercised. These are browser walkthroughs and
design judgments. They do not measure user task success.

### Zed Extensions — Visual direction for the skill shelf

Zed's search for `docker` preserved the query in the URL. The first view
kept category choices beside search, and cards placed name, description,
author and a download indicator on separate lines. At 390px those
categories wrapped within the page instead of moving into a horizontal
strip. The search began around 279px from the top and the result cards
were visible in the first viewport. An unmatched query echoed the search
term and retained the clear affordance. The light canvas, fine rules,
blue focus and compact lettering give a useful comparison against the
project's warm-paper palette. The duplicate Search control and long
intro consume vertical room on mobile. Adopt the local hierarchy
rather than the storefront top section.
[Live directory](https://zed.dev/extensions?query=docker).
[Zed editor extension UI at the reviewed revision](https://github.com/zed-industries/zed/blob/2f808b3c2de049ecfdbad0fdb26763cebfcaa3b4/crates/extensions_ui/src/extensions_ui.rs).

**Transfer.** The first view of Skills should surface a query and a real
row quickly, with explicit ways to clear the query and reset other
filters. A skill's name, purpose and local state deserve a stable row
order. Add registry metadata only where it informs the task. Zed's
GitHub code here is its native editor implementation, which separately
tracks categories and installed state. The live screenshot is its public
website. Neither a download count nor a catalog slug establishes the
identity of a local copy.

### Obsidian Community — Details before installation

Opened the published Importer item and switched from Overview to Scorecard.
The header kept the name, author and add action in place. The adjacent
evidence tabs gave distinct homes to readme content, evaluation
information and update history. The Scorecard itself disclosed that the
evaluations are still being developed and displayed concrete inputs such
as hygiene and maintenance activity. The tested scorecard fit the phone
viewport. Mozilla Add-ons had a stronger explicit split between required
and optional browser permissions. Obsidian's Markdown-heavy detail
and compact metadata rail fit the skill-reader task more directly.
[Importer detail](https://community.obsidian.md/plugins/obsidian-importer).
[Mozilla Tree Style Tab listing](https://addons.mozilla.org/en-US/firefox/addon/tree-style-tab/).

**Transfer.** Keep package identity, origin, exact local destination and
review action together while the user opens the skill document, validation
findings or file list. Preserve the distinction between advisory scanner
findings and an explicit approval bound to a reviewed artifact. Use
worded observations for unknown, partial and unavailable states. Mozilla's
required/optional grouping is helpful when a source independently declares
different effects. The directory's editorial review and browser permission
model are specific to browser extensions.

### Playwright Trace Viewer — Selected event anchors evidence

The hosted example did not render an inspectable trace in the initial
browser session. Used the installed open-source viewer with a synthetic
comparison trace on an isolated loopback preview. The action list
contained a recorded Compare copies event. Selecting it and switching
between Before and After retained the selected action. The fixture's
comparison result appeared in After only. The source binds Action,
Before and After views to the selected action and includes explicit
fallback logic for missing snapshots. That implementation is a useful
example of keeping a selected object stable while its detail tabs change.
The full three-pane inspector is intentionally dense.
[Trace Viewer guide](https://playwright.dev/docs/trace-viewer).
[Action list source](https://github.com/microsoft/playwright/blob/049226728d2da8054db18b04782a9848b755855e/packages/trace-viewer/src/ui/actionList.tsx).
[Snapshot panel source](https://github.com/microsoft/playwright/blob/049226728d2da8054db18b04782a9848b755855e/packages/trace-viewer/src/ui/snapshotTab.tsx).

**Transfer.** Put findings and filter status early in Quality. Selecting a
finding should keep the identity, scope and coverage visible while the user
looks at the evidence or opens the exact copy. On a phone, retain a visible
return to results and preserve prior filters and focus. For Sync map, show
current target and incoming source together, with explicit states for an
ambiguous source, unreadable text or uninspected files. Use the document
and folder evidence actually available from each Skills Manager workflow.

### GitButler Operations History — Select, preview and then restore

The official capture shows dates and ordered events on the left and a
dedicated content preview. The published restore capture illustrates the
consequential action separately. The GitHub history route wires the selected
snapshot to a selected-file diff, and references a snapshot commit ID
when restoring. That supports the information structure shown in the
capture. This pass used first-party captures and source, and did not
exercise a GitButler restore.
[Operations History](https://docs.gitbutler.com/features/timeline).
[GitButler history route at the reviewed revision](https://github.com/gitbutlerapp/gitbutler/blob/9939b47318d59d91c482d44974d26b186c319d16/apps/desktop/src/routes/%5BprojectId%5D/history/%2Bpage.svelte).

**Transfer.** Lead with the exact recoverable item, its date, its agent
scope and destination. Place its content preview and action next to that
identity. Make the selected action visible to keyboard and touch users.
Use history to find the desired copy, while keeping text snapshots,
whole-folder snapshots and full archives clearly identifiable. GitButler's
project restore refers to a whole Git state before an operation. Skills
Manager's sync Undo restores text and on/off state. Earlier supporting
files are recovered through the appropriate retained folder.

## Pass 3 — Try to displace the shortlist

**[NOTE]** A separate review challenged the strongest picks against
similar products and current Skills Manager constraints. The table
records the candidates screened at this stage and the limits of their
evidence. These judgments rank fit to this project.

| Candidate | Evidence checked | Selection outcome |
|---|---|---|
| [Mozilla Add-ons](https://addons.mozilla.org/en-US/firefox/search/?q=tree%20style%20tab) | Live results, visible filter/relevance controls, actual detail with required and optional permissions | Keep the trust-disclosure mechanic as support. Obsidian is closer to a skill document reader |
| [n8n workflow templates](https://n8n.io/workflows/) | Live directory, category shortcuts, author metadata, phone search and filter reset | Useful for exploratory discovery. Editorial promotion makes the first view less suited to managing installed copies |
| [Glama MCP directory](https://glama.ai/mcp/servers) | Live `drawio` query with separate server, connector and tool results | Useful when multiple result types genuinely share a search. Zed has a calmer collection scan for one library |
| [skills.sh](https://www.skills.sh/) and [Smithery](https://www.smithery.ai/servers) | Public registries and search surfaces, ranked skills and source identifiers | Useful domain comparisons. Popularity and hosted connector actions answer different questions from local scope, file state and review |
| [Sentry Sandbox](https://sandbox.sentry.io/) | Issue feed visible behind an email gate on the public route | Insufficient evidence for a completed detailed inspection, so Playwright leads |
| [FreeFileSync](https://freefilesync.org/screenshots.php) | Official desktop captures of explicit left/right comparison and direction | Keep the source/target lesson for Sync map. Its densely icon-driven chrome has lower fit for the browser workflow |
| [Backrest snapshot browser](https://github.com/garethgeorge/backrest/blob/148ba12c12a7a4fef6d3c6c8e675ca2c5e7d3635/webui/src/features/repositories/SnapshotBrowser.tsx) | Source carries snapshot ID and path into a restore dialog, including a suggested alternate destination | Strong check on destination clarity. Weaker as a visual lead because the populated UI was not independently opened |
| [Kopia](https://kopia.io/docs/features/) and [Syncthing](https://docs.syncthing.net/users/versioning.html) | Official backup and file-versioning documentation | Useful recovery semantics to check for confusion. Their workflow and available evidence did not displace GitButler's history composition |

The GitHub pass inspected Zed's GPL/Apache-marked editor code, Mozilla's
MPL-2.0 search/filter frontend, Playwright's Apache-2.0 trace UI and
Backrest's GPL-3.0 snapshot browser. GitButler was used as a supplementary
source-available reference under its FSL 1.1 MIT Future license. These
are implementation references for reading and comparison, without
importing dependencies or reusing source here.
[Zed licenses](https://github.com/zed-industries/zed/blob/2f808b3c2de049ecfdbad0fdb26763cebfcaa3b4/README.md#licensing).
[Mozilla search filters](https://github.com/mozilla/addons-frontend/blob/b7bce0b408c994181c027145b042215fd66c9064/src/amo/components/SearchFilters/index.js).
[Playwright license](https://github.com/microsoft/playwright/blob/049226728d2da8054db18b04782a9848b755855e/LICENSE).
[Backrest license](https://github.com/garethgeorge/backrest/blob/148ba12c12a7a4fef6d3c6c8e675ca2c5e7d3635/LICENSE).
[GitButler license](https://github.com/gitbutlerapp/gitbutler/blob/9939b47318d59d91c482d44974d26b186c319d16/LICENSE.md).

## What would prove the transfer

**[NOTE]** The next design comparison has three measurable tasks.

- **Library.** Find a skill by intent, filter by agent, then open the correct
  copy. Compare time to the first meaningful row, wrong-copy openings and
  whether Back preserves the filtered view.
- **Evidence.** Explain why a partial Quality report cannot claim a clean
  library, then open a finding. Check that the selected project and local
  copy remain visible as the evidence changes.
- **Recovery.** Identify which of two same-named items a restore will
  affect, what it can replace, and where any earlier supporting files
  are retained. Test an occupied destination and a missing preview.

Run with keyboard navigation, 320px and 390px widths, larger text and
both themes. Include no results, one item, duplicate names, partial
evidence and a long list. The research loop ended after the second set
of challengers and source checks did not displace the four picks.
