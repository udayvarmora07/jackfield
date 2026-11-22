# V2 Mobbin community and comparison research

**Version 0.1.0**

**AI manifest**: 21 November 2026 reference loop for narrow-screen comparison,
selected-copy context and recovery states. Goes with
@docs/56-v2-reference-selection-loop-2026-11-21.md and the
[editable Draw.io comparison board](design/v2-reference-study/skills-manager-mobbin-comparison.drawio).

## Decision

**[NOTE]** Use Pierre Diffs as the lead for the **text comparison** in Sync map
and Inbox. Offer side-by-side where both panes can be read and default to one
wrapped column on a phone. Use Kaleidoscope and Meld to inform a separate,
file-level view of supporting evidence. Keep Playwright Trace Viewer for retaining
the selected item as evidence changes, and GitButler for the history-to-preview
sequence. See @docs/56-v2-reference-selection-loop-2026-11-21.md.

For Skills and Sync map, carry the typed query when changing the browsing view.
Mobbin documents that interaction. Intercom's community capture adds a useful
layout reference for keeping a selected item and its details in view together.
Apply this with fewer columns and keep the exact copy legible.
[Mobbin changelog](https://mobbin.com/changelog) ·
[Intercom capture](https://mobbin.com/screens/6651eeee-af04-4b98-a423-cd75800b43f1).

## Pass 1 · Discover through libraries and communities

**[NOTE]** The public [Mobbin Mobile community](https://mobbin.com/community/mobile/featured)
and [Mobbin Web community](https://mobbin.com/community/web/featured) showed
member-curated collections without a login. The [Recent view](https://mobbin.com/community/web/recent)
showed a different set of collections from Featured. Several collections and individual
screen previews opened anonymously. Public profiles, such as
[Rachel How's](https://mobbin.com/@rachelhow), help trace who curated a collection.
Mobbin describes the public-profile and collection features in its
[community launch announcement](https://www.linkedin.com/posts/mobbin_introducing-mobbincomcommunity-a-new-activity-7245009516273008640-OQSR).

| Public collection or source | Why it was reviewed | What it contributes |
| --- | --- | --- |
| [Side Panel](https://mobbin.com/collections/55f71e9c-5eff-470c-9fd6-3afdcd7d2234/web/screens) and its [Intercom example](https://mobbin.com/screens/6651eeee-af04-4b98-a423-cd75800b43f1) | Preserve context as a user moves between same-named copies | The selected row and a labeled Details panel remain visible together in the desktop capture. Preserve the selected copy's scope and path on phones by putting its identity immediately above the evidence. |
| [HoneyBook notification center](https://mobbin.com/screens/2bdc9813-1e97-42d2-a80e-82ab82e151a7) in Side Panel | Compare a quick jump to recent events with the full Recovery workspace | The panel gives events an action and a time while leaving the main view in place. This could inform a compact entry point. Restoration still needs space to review an exact target, any existing destination and the files covered. |
| [Critical States](https://mobbin.com/collections/599a2ca5-ca4c-4c99-be6b-3cdc4ee7f080/mobile/screens), curated by Anamol Rajbhandari | Find a small-screen response to a failed read | The [Philips Hue capture](https://mobbin.com/screens/50c83129-f5b4-4418-b2ee-bb5067095bcc) says that no bridge was found, explains the issue, and pairs help with retry. A recovery read failure needs similar action order plus the affected scope or path. |
| [Loading...](https://mobbin.com/collections/16714ce5-51fd-45b5-82aa-e5573487dc33/mobile/screens), curated by Inès Gruhier | Check whether wait copy says what is happening | Two mymind previews show distinct activity messages for saving and categorization. For Skills Manager, keep the compared paths visible during a real read, then show the observed result. Full-screen waiting treatments would make it harder to retain context. |
| [AI Empty States](https://mobbin.com/collections/27bdf774-4620-49de-b919-313cad1d6a43/mobile/screens), curated by Rachel How | Check discovery from an empty library | The collection is discoverable via a public profile. Empty prompts were a poor fit for deciding whether existing files were readable or inspected. |

These are captured product states. The collection views did not provide live
Intercom, HoneyBook or Philips Hue workflows. This pass used the stills to assess
hierarchy, context and wording.

The public [Mobbin changelog](https://mobbin-marketing.framer.website/changelog)
describes preserving a query between Screens and Flows. The free
[onboarding study](https://mobbin.com/blog/the-long-onboarding-a-study-of-1-460-flows)
illustrates a different reason to review sequences. Screens establish what a
product showed during recording. A study of the task and participants would be
needed to establish which interaction works better in Skills Manager.

Mobbin's published Free account plan lists limited library and copy, download
and history features, and a three-collection limit. Library search, flows,
animations and MCP are paid features. Public member collections and paid
team-shared collections are separate features. We browsed anonymously and did
not create an account. [Official plan details](https://mobbin.com/pricing.md).

[Refero's public guide](https://refero.design/how-it-works) helped compare the
roles of tags, text and source-product filters. [Page Flows](https://pageflows.com/)
was reviewed as a discovery library for sequences. The walkthroughs in Pass 2
provided more directly applicable evidence for exact-copy review.

## Pass 2 · Exercise comparison in Chrome and inspect source

**[NOTE]** Used isolated `agent-browser` Chrome sessions. Measured CSS pixels at
1440, 390 and 320 px in Pierre's public demo. Diffchecker received invented
Markdown text. The study used no real skill content, and did not save or share a
diff.

| Candidate | Observation | Design decision |
| --- | --- | --- |
| [Pierre Diffs layout demo](https://diffs.com/#layout) | Split displayed two panes for the same file. At 390 px each pane was 173 px wide with 501 px and 540 px of scroll content. Stacked gave the same file one 348 px pane. That pane still scrolled to 540 px with the sample's static layout settings. At 320 px the page itself measured 329 px and the stacked pane 278 px. | Take the single-column layout at narrow widths and make wrapping the default there. Keep layout and wrap separate so users can inspect alignment when needed. Test the host page for overflow too. |
| [Pierre Diffs change styles](https://diffs.com/#styles) and [Apache-2.0 FileDiff source](https://github.com/pierrecomputer/pierre/blob/4100176d8a3fe58f7c8e5fddf27dde64dc688ea1/packages/diffs/src/components/FileDiff.ts) | The separate styling demo rendered `data-overflow=wrap` and switched to `data-indicators=classic` on selection. Pinned source shows layout and overflow as separate options and enables scroll synchronization for split mode with scrolling. Keyboard and screen-reader behavior were outside this check. | Use textual addition and deletion indicators alongside color, preserve the current selection across presentation changes, and make it possible to see the two exact scope/path labels in either mode. The source is an implementation reference for native Vue/CSS. |
| [diff2html demo](https://diff2html.xyz/demo) and [MIT repository](https://github.com/rtfpessoa/diff2html/tree/72331ff5d13a8d4d1f11256a7b554dd0d69d7014) | The public PR demo switched from Line by Line to Side by Side. At a 390 px viewport its wrapper was 342 px while the demo document measured 1627 px. Split gave the first file 170 px per pane with considerable inner overflow. | Keep its file-summary idea as a supporting reference for a multi-file view. Pierre is the clearer presentation reference for the default phone layout. |
| [Diffchecker](https://www.diffchecker.com/) | An invented original and changed document produced a result with both changed lines and a newly added line. The desktop result exposed Split, Unified, wrapping and jump to first change. At 390 px the document stayed within the viewport while the desktop Split and Unified controls had no visible width. | Keep a visible jump to the first change if needed. Place the layout control at the diff instead of relying on a desktop settings rail. |
| [Kaleidoscope folder comparison](https://kaleidoscope.app/help/docs/comparing-folders) and [folder-versus-file explanation](https://blog.kaleidoscope.app/2025/01/20/folder-vs-file-changes-why-are-there-differences/) | Official captures show a paired tree and filters by file state and name. The vendor explains that folder and file results may use different criteria. | Show which parts of the folder were inspected and the scope of any equality statement. A matching skill document gives only text evidence. |
| [Meld folder mode](https://gnome.pages.gitlab.gnome.org/meld/help/folder-mode.html) | Its official guide documents opening the selected file comparison with Enter from a folder comparison. | Reuse the navigation principle of opening the selected file from its evidence row. Make it possible to return with that row and position intact. |

The controls in the Pierre and diff2html demos and the Diffchecker fixture were
exercised live. Kaleidoscope and Meld were reviewed through published docs.
Neither their native apps nor actual restoration operations were exercised.

## Pass 3 · Recheck against Skills Manager tasks

**[NOTE]** These are design directions for a later UI pass.

1. **Find the intended copy.** Search for a skill with copies in Codex and
   another scope. Keep the query when switching the discovery view. In the
   comparison show the selected scope and concrete path with an explicit
   source and target. Return focus to the selected item when the details close.
2. **Read the difference on a phone.** Start with a wrapped single column at
   320 and 390 px. Use long prose, an unbroken path and a change that starts
   below the fold. Show an addition/deletion label and original/changed line
   numbers where applicable. Switching to split and back should let a person
   return to the same changed block with the same selected files.
3. **Tell what was inspected.** Use examples with identical `SKILL.md` text and
   different supporting files, an unreadable file, and a missing destination.
   Text equality, observed file differences and incomplete evidence need
   distinct states. A retry should say which read failed without opening up a
   write action or inferring the whole folder's integrity.
4. **Recover one exact item.** Choose between two same-named Recovery entries.
   Preserve time, scope, path and entry identity while previewing. Make known
   restore coverage legible before action. The product currently uses Inbox
   Undo for the skill document and on/off state and handles full folder
   recovery with the exact earlier Recovery entry. See @docs/08-web-ui.md.

The first comparison, failure, retry and restore path still needs a usability
walkthrough in Skills Manager with test fixtures, keyboard and a screen reader.
The evidence on this board supports choosing the UI patterns to prototype.
