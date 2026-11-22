# Skills Manager v2 UI Reference Study

**Version 1.0.0**

**AI manifest**: Read before changing tool discovery, Quality report navigation,
Inbox review, scope selection or Recovery. Records reference walkthroughs,
source strength, current v2 observations and proposed task checks.

[Editable Draw.io board](design/v2-reference-study/skills-manager-reference-board.drawio) ·
[Browser-viewable board](design/v2-reference-study/skills-manager-reference-board.html).
The published boards link each third-party capture to its source.

## What to carry forward

**[NOTE]**

Quality has the clearest usability gap. A developer looking for a broken
document can jump to findings, yet those findings are still the third major
evidence block in reading order. A search and severity summary near the top
would make the main diagnosis task easier to discover. GitHub Issues shows how
to keep the active query, result list and recovery from an empty search
together. Linear's documentation adds a distinction between filtering records
and choosing how much metadata each row displays. Keep project identity and
partial evidence visible whenever a report is filtered.
[GitHub Issues](https://github.com/withastro/astro/issues),
[Linear display options](https://linear.app/docs/display-options).

Recovery benefits most from context at the decision point. A recovered name
does not identify an exact copy. Show the selected entry, readable time, scope,
location and replacement effects together before an operation that can replace
files. Let the user inspect the comparison when one exists and see what was
actually restored afterwards. Apple treats recovery as an action on a known
location, Google treats it as a decision about a selected version, and GitHub
Desktop turns a long history into an inspectable file-level diff.
[Apple Time Machine](https://support.apple.com/en-au/guide/mac-help/mh11422/mac),
[Google Docs version history](https://support.google.com/docs/answer/190843?hl=en),
[GitHub Desktop diff review](https://docs.github.com/en/desktop/making-changes-in-a-branch/committing-and-reviewing-changes-to-your-project-in-github-desktop).

Tools already has a searchable directory and a command palette. The next
discovery question is whether a person can reach the same destination with
different words, from the directory, the palette or the relevant skill.
Raycast demonstrates the difference between browsing a marketplace and
invoking a known action. Astro demonstrates the difference between navigation
across the app and navigation within a long page. Those distinctions are more
valuable here than either product's branding.
[Raycast Store](https://www.raycast.com/store),
[Raycast launcher manual](https://manual.raycast.com/search-bar),
[Astro Docs](https://docs.astro.build/en/basics/astro-pages/).

## Method and baseline

**[NOTE]**

On 2026-11-21, the study used the Awwwards, Godly/Recent Design and Inspo MCP
servers to retrieve reference entries, then used agent-browser to examine
public workflows and official product documentation to study native or
signed-in flows. The interactions below identify which method established each
finding. Chrome rendered the local v2 working tree using the repository's
synthetic pilot inventory. Earlier measured typography and contrast decisions
remain the basis for v2 styling. A gallery capture or an official document
describes a reference, while the upgrade ideas below are hypotheses about this
product. [Current v2 interface](08-web-ui.md#default-v2-interface-v2),
[Prior interface decisions](53-apm-and-interface-decisions-2026-11-20.md).

| Local task at 390 × 844 CSS px | Observed starting position | What it implies |
|---|---|---|
| Find an unfamiliar tool | Directory search starts 219px from the document top, AI Assist starts at 1,021px | Search removes the need to scan the long list when the user knows a likely term |
| Find a Quality issue | Findings shortcut starts at 398px, the Findings heading is at 3,105px, and search at 3,194px | The shortcut helps, while direct scroll and sequential reading still encounter baseline and listing evidence first |
| Load from a backup | The shortcut starts at 287px, the section heading at 1,056px, and the file picker at 1,156px | The shortcut has a concrete benefit. The next decision is about destination and replace mode |
| Find a skill on the shelf | Search starts at 327px, and the first populated alphabetical heading at 901px | A known-item search and a browse session begin with different priorities. Test the filter block and first result in compact and comfortable modes |
| Review cross-agent differences | Search starts at 203px, the review-only filter at 261px, and the agent panel heading at 894px | The search and filter appear early. Selecting and verifying the exact target still requires a clear handoff to the comparison |
| Triage an Inbox item | The current issue starts at 240px and the rest of the queue at 716px | The focused task has useful prominence. Access to the queue becomes a separate concern on a short screen |

Values are rounded document coordinates from one populated synthetic fixture in
standard text size. Larger text, a smaller viewport, another inventory,
asynchronous evidence and opened disclosures can move these positions.
No usability timings were inferred from pixel counts.

## Reference walkthroughs

**[NOTE]**

### Raycast Store and launcher

**Why this reference.** A skill extension directory and a command launcher
share Skills Manager's need to support both exploration and fast retrieval.

**What I inspected.** In the public Store, Search opened a focused text input
over the catalogue. Typing `clipboard` produced rows with an extension name,
an icon and an action-oriented description, followed by a link to the full
results. Featured extensions and catalogue navigation stay available as the
browse path. The native launcher manual describes arrow-key navigation, a
primary result action, aliases and a separate action panel for the selected
item. The native launcher interaction is documented. [Raycast Store](https://www.raycast.com/store),
[Search Bar](https://manual.raycast.com/search-bar),
[Action Panel](https://manual.raycast.com/action-panel),
[Settings search](https://manual.raycast.com/settings).

**For Skills Manager.** Build vocabulary around tasks such as “check a skill,”
“find copies that differ” and “restore a deleted copy.” When opening an
existing destination from a search result, put the useful context in the
result, such as the named tool or the exact skill scope. Keep global skill
search and tool search visibly distinguishable, because their result sets
differ. A command that opens a review can be a primary search result.
Executing a file mutation directly from that list would bypass the decision
the review exists to support.

### Astro Docs and Recent Design sidebar

**Why these references.** The same page can require a stable route location
and a second hierarchy inside the content. A grouped sidebar can make the
route location clear, while a short section index keeps dense pages usable.

**What I inspected.** The Astro Pages article showed a left site navigation
and a distinct right “On this page” outline at desktop width. At 390px site
navigation appeared behind Menu and the section outline collapsed to a
roughly 49px row. I opened the outline and chose the custom 404 heading.
Astro changed the fragment, scrolled the section below the top chrome,
collapsed the outline and replaced “Overview” with the current section name.
Pranav Patel's Recent Design clip shows an expandable sidebar group and
active child styling. It is a credited interaction concept rather than a
production workflow. [Astro Pages](https://docs.astro.build/en/basics/astro-pages/),
[Pranav Patel's sidebar on Recent Design](https://recent.design/i/b6hr2e5-sidebar-sub-menu-interaction).

**For Skills Manager.** Quality and Recovery are good candidates for a
compact outline if follow-up testing shows their current visible shortcuts
wrap excessively with Large text. Keep the heading visible when the outline
closes after selection and give keyboard users a predictable focus target.
Skills Manager uses the fragment for routing, so preserve local route and
scroll semantics when adapting the pattern. Sidebar tree lines or motion are
optional cues. A current location indicator provides the functional value.

### VS Code Settings

**Why this reference.** An editor settings screen handles long lists of
technical labels alongside a scope that changes what an operation means.

**What I inspected.** Microsoft's Settings editor guide shows an in-place
search, group navigation and distinct User and Workspace views. Modified
settings carry an adjacent marker, and actions are scoped to the row.
Microsoft documents both the graphical settings view and the JSON route.
The isolated desktop launch did not yield an inspectable Settings window.
[VS Code User and Workspace Settings](https://code.visualstudio.com/docs/configure/settings).

**For Skills Manager.** Keep a selected project or agent scope close to the
control whose interpretation it changes, especially in Workspaces, Quality
and exact-copy Settings workflows. Prefer a readable scope label with a
visible path or source indication where needed. VS Code's override order is
specific to its editor. A Skills Manager report can show observed filesystem
evidence and known folder rules without making a claim about which skill an
agent loaded.

### GitHub Issues and IBM Carbon

**Why these references.** Quality and exact Instances need to support rapid
scanning of many rows, then a detailed look at one item.

**What I inspected.** In a public GitHub Issues list, I opened a query with
an intentionally unmatched word. The page retained the query, search and
clear controls and showed a specific no-match message. GitHub's documentation
also describes composing filter criteria and sharing filtered URLs. IBM
Carbon's guidance positions search and filtering in a table toolbar, offers
expandable rows for supplementary evidence and exposes batch actions in
selection context. Carbon is design-system guidance. [Public Astro issues](https://github.com/withastro/astro/issues),
[GitHub filtering documentation](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/filtering-and-searching-issues-and-pull-requests),
[IBM Carbon data-table guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines).

**For Skills Manager.** Keep four report states legible near the controls:
report unavailable, report partial, no findings observed, and no findings
match the active filters. A zero result from a partial scan cannot justify
a clean bill of health. Show a filter-clear action without dropping the
project selection. Keep exact-copy identity visible when Instances shows a
selection count, and retain the existing target review before a batch
mutation. For Sync map, give the matrix enough width to scan and test the
phone list with duplicate names.

### Linear Triage, Inbox and display options

**Why this reference.** Linear regularly moves users between inspecting a
queue, filtering it and taking a contextual action. Skills Manager's Inbox
also separates inspecting a problem from resolving it.

**What I inspected.** Official documentation shows Triage as a dedicated
intake destination, with Inbox list actions, quick search and snoozing.
Linear documents a separate control for changing visible fields and sort
order. Its Inspo entry is a marketing-page capture with an embedded product
view. It helped assess the visual rhythm of adjacent list and detail panes.
The workflow claims come from first-party documentation.
[Linear Triage](https://linear.app/docs/triage),
[Linear Inbox](https://linear.app/docs/inbox),
[Linear filters](https://linear.app/docs/filters),
[Linear display options](https://linear.app/docs/display-options),
[Inspo Linear capture](https://inspomcp.dev/d/linear-app/DESIGN.md).

**For Skills Manager.** Keep the current item's exact copy and next action
prominent, even when a queue is filterable. Give “skip for now,”
“acknowledged,” and “fixed” distinct meanings where users return to a
problem. A queue result count should remain separate from a display-density
preference. Linear's timed reminders would require product semantics beyond
the existing session-local skip behavior.

### Apple Time Machine

**Why this reference.** Recovery often starts with knowing *which thing*
went missing and approximately when, while archive formats are secondary.

**What I inspected.** Apple's guide starts from the containing Finder
location. The timeline highlights the selected backup, indicates when a
backup is loading or validating, and restores chosen items to their original
location. Spotlight can carry a Finder search into recovery. This is a
documented native flow. [Restore items](https://support.apple.com/en-au/guide/mac-help/mh11422/mac),
[Recover files with Spotlight](https://support.apple.com/en-om/guide/mac-help/-mh15136/mac).

**For Skills Manager.** If a user came from a skill reader or a sync receipt,
carry the exact copy into history or Recovery where the data supports it.
Give restore entries enough room for scope, timestamp and destination.
An occupied or changed destination needs an explicit reason drawn from the
existing restore rules. The local app has its own archive and retention
semantics.

### Google Docs version history and Drive bulk restore

**Why these references.** They show a historical source and an operation's
result as separate concepts, which matters when “restore” can affect
different parts of a skill or library.

**What I inspected.** Google Docs' guide shows a version list, selected
change evidence, a confirmed restore and a separate make-a-copy outcome.
The separate Drive bulk-restore documentation describes selecting a point
in time and seeing progress as previous versions become current. Its bulk
flow applies only within the documented beta scope and suitable file types.
These are documented workflows. [Docs version history](https://support.google.com/docs/answer/190843?hl=en),
[Drive version restore](https://support.google.com/drive/answer/16482799?hl=en).

**For Skills Manager.** Distinguish a SKILL.md text snapshot, a whole-folder
snapshot and an archive that includes manager metadata. Identify the
snapshot and the affected destination near the action. A rollback preview
should disclose whether files, enabled state, and metadata are affected
based on the specific operation. Only show a preview, progress value or
preserved post-restore version when the underlying behavior supports it.

### GitHub Desktop history and diffs

**Why this reference.** Exact-copy comparisons need to show what changed,
what stays the same and which revision is being inspected.

**What I inspected.** The official Desktop guides describe picking a commit,
picking a changed file and inspecting its changed sections. Unified and
split layouts show the same comparison in different presentations, and
users can expand surrounding lines. GitHub's comparison guide also
distinguishes file history from a broader range of commits. The native UI
was not opened. [GitHub Desktop history](https://docs.github.com/en/desktop/overview/creating-your-first-repository-using-github-desktop),
[GitHub Desktop diff settings](https://docs.github.com/en/desktop/making-changes-in-a-branch/committing-and-reviewing-changes-to-your-project-in-github-desktop),
[GitHub commit comparisons](https://docs.github.com/en/pull-requests/how-tos/commit-changes/comparing-commits).

**For Skills Manager.** Use unified or stacked comparisons on narrow
screens, and offer a readable split only when both columns fit. Identify
which side is current and which will be applied, name the scope/path,
and say when comparison context is partial. A whitespace display setting
could aid reading while byte-level identity and restore checks retain
their own meaning.

### Awwwards Viture Dashboard and the Inspo/Godly selection

**Why these references.** The galleries are useful for visual hierarchy,
surface contrast and motion examples. Comparable application workflows
were selected from first-party products for behavior.

**What I inspected.** Awwwards returned desktop and mobile images for
Viture's 2022 dashboard entry. The desktop image puts a single product
render between narrow pictographic control rails. The mobile image keeps
the same focal product and moves controls around it, with a large consent
overlay across the lower part of the composition. The subdued icons are
easy to overlook. The live destination did not establish a current
authenticated dashboard workflow. Inspo returned archived desktop
and mobile captures of the Raycast, Linear and Astro Docs landing pages.
The archive identifies their hierarchy, type and palette, while the live
walkthroughs provided the evidence about user behavior. Godly's search also
returned Rauno Freiberg's Button Pile clip, an expressive palette animation
with limited relevance to a repeat-use tool. [Viture on Awwwards](https://www.awwwards.com/sites/viture-dashboard),
[Raycast capture](https://inspomcp.dev/d/raycast-com/DESIGN.md),
[Linear capture](https://inspomcp.dev/d/linear-app/DESIGN.md),
[Astro Docs capture](https://inspomcp.dev/d/docs-astro-build/DESIGN.md),
[Button Pile on Recent Design](https://recent.design/i/9m51f1y-button-pile).

**For Skills Manager.** Take the restraint of distinct headings, sparse
accent use and a readable current state. Keep the warm paper, Newsreader
headings and contrast-tested text roles already chosen for v2. Animation and
strong overlays can detract from comparing paths and files repeatedly.
Test movement only if it clarifies an actual state change.

## Proposed follow-up checks

**[NOTE]** These are proposed usability tasks and acceptance checks.

| Priority | Prompt for a test participant | Evidence to collect |
|---|---|---|
| Quality findings | “Find out which skill document is broken, then open the affected copy.” | First action, time to first relevant finding, exact scope chosen, and whether the participant can explain a partial scan and a no-match result |
| Recovery identity | “Restore the earlier Codex copy of a skill with the same name in two agents.” | Whether scope, timestamp and destination are noticed before approval, whether a collision is understood, and whether the resulting copy is verified |
| Tool discovery | “Check which skills consume the listing budget” and “find the folder update tool.” | Success by directory and keyboard, query vocabulary, no-result recovery, and whether users can predict where an action will take them |
| Skill shelf and Sync map | “Find one named skill and compare its copies across two agents.” | Visibility of the first result, correct source/target choice, state vocabulary, and retention of search context after opening a detail |
| Inbox | “Inspect a finding, put it aside, then return to it.” | Whether the distinction between skipped, acknowledged and fixed is understood and whether selection and focus stay coherent |

Run the same tasks with an empty inventory, one copy, duplicate names and
a large fixture, at phone and desktop widths. Include keyboard-only use,
Large text, light/dark themes, slow or missing evidence, and one interrupted
restore. Measure actual task completion before claiming that a reference
pattern improved it.
