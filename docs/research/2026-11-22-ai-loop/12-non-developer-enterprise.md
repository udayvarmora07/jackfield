# Round-2 research: non-developer and enterprise users of AI "skills"

Date: 2026-11-22. Scope: knowledge workers and admins using Skills in Claude.ai / Desktop / Cowork, ChatGPT Skills, Copilot agents, Gemini Gems, custom GPTs, Notion custom agents; team and enterprise governance.

Prior context read: `docs/59-ai-everywhere-research-2026-11-22.md` (F1 to F15). Already covered there: sprawl and library health, model-upgrade recheck, honest eval statistics, per-hunk accept with provenance, draft from transcripts, judge calibration, security scanning, agent-authored write gate. Items below are checked against that list and marked NEW or KNOWN.

## Method log

| Source | Method | Result |
|---|---|---|
| opencli doctor | Health check | Daemon and extension connected (v2.0.3). |
| reddit (6 searches: r/ClaudeAI x2, r/ChatGPTPro, r/Office365, r/productivity, r/sysadmin) | `opencli reddit search` | **All 6 blocked** by Reddit network security (HTTP 403, SECURITY_BLOCK). Not retried around the block. No Reddit evidence in this pass. |
| youtube search (2 queries) | `opencli youtube search` | 15 + 15 results. |
| youtube comments (2 videos, public) | `opencli youtube comments` | 5 and about 25 comments read. Few comments, so anecdotal only. |
| substack search (2 queries) | `opencli substack search` | 20 + 20 posts. Mostly listicles. |
| medium search (2 queries) | `opencli medium search` | 10 + 10 posts. Mostly listicles and enterprise pitch posts. |
| producthunt browse | `opencli producthunt browse` | Failed (no network capture in 5s). |
| producthunt posts (ai-agents) | `opencli producthunt posts` | 20 launches, none about skill governance. |
| linkedin | Help checked | Only `search` is jobs. No public-post search exists, so not used. |
| WebSearch and WebFetch | Vendor docs | Anthropic admin article (WebFetch, "Updated this week"); OpenAI Skills help (WebFetch); Anthropic custom skills help (search); Microsoft Copilot agent governance (search); Google Gems sharing admin (search); Notion custom agents (search). |

Raw outputs are in the scratchpad as `r3-*.json`.

Limits: Reddit missing is the largest gap. Product Hunt gave no relevant content. YouTube and Substack counts are view or listing counts, not sentiment. Vendor pages were partly search snippets, not full reads.

## Ranked themes

Confidence: H = primary vendor doc read or quoted; M = two or more sources, or vendor doc via search snippet; L = one source or content-volume signal only.

### 1. Admins gate what reaches the team (approval and publishing modes). NEW for Skills Manager. Confidence H.
- Anthropic admin article (support.claude.com/en/articles/13119606, WebFetch, undated "Updated this week"). Publishing has three modes: Requires review, Open, Off. Owners can turn off user-created skills so members use only provisioned ones. A Requests tab shows the exact submitted version for approve or request changes.
- ChatGPT Skills help (help.openai.com/en/articles/20001066, WebFetch). Skills are scanned on upload and marked "Needs Review" or "Blocked". Admins set which roles can upload, share, publish or install.
- Copilot (Microsoft Learn, agent-builder share and manage, search snippet). Where sharing is restricted, an admin must approve and deploy before org-wide use.
- Paraphrase: teams want a gate between "I made it" and "everyone has it".

### 2. Confusion about visibility and what "shared" means. NEW. Confidence H.
- Anthropic: custom skills are per user and "cannot be centrally managed by admins" (search snippet, 12512198). Admin doc does not say plainly that personal skills are hidden. Sharing or publishing is what makes them visible.
- Google Gems: turning sharing off stops new shares, but already-shared Gems stay shareable in Drive. Drive rules also decide external sharing.
- Microsoft: changing admin sharing settings applies only to new sharing actions. Existing shares need a separate review.
- Anthropic: turning publishing off hides older org-wide shares from everyone except authors.
- Paraphrase: admins and users both misread what a change revokes.

### 3. Plain-language "which one do I use?" confusion (Gems vs Projects vs GPTs vs Skills). NEW as an onboarding feature. Confidence M.
- YouTube: "Custom GPT vs Projects vs Gems: which should your team use?" (Sharebench, 10 days old, 4 views). Similar comparison titles on about 6 videos in the Gems and GPT search.
- Medium: "Claude Chat vs Code vs Cowork vs Projects vs Skills: Everything you need to know."
- Anthropic and Microsoft docs both split always-on guidance from opt-in skill. Users need that split explained in the product.

### 4. Turning their own SOP or real work into a skill. Partly KNOWN (F5), but "SOP document" is NEW. Confidence M, mostly titles.
- Substack, 2026-11-11: "Your Best AI Skills Are Hiding in the Work You've Already Done." Title only.
- Substack, 2026-11-17: "The Most Underrated Tool: Recording Skills With Claude." Title only.
- Anthropic guidance: start from markdown instructions, include example inputs and outputs, make the description say when to trigger (help center, search snippet).
- Paraphrase: people have procedures in Word or Notion, not in SKILL.md. The gap is conversion, not authoring.

### 5. Starter packs by job role, and curated catalogues for teams. NEW. Confidence M, but a content-volume signal.
- YouTube "Claude Skills" search: 15 results; about 8 have over 100k views. Several are "top N skills" videos.
- Substack: about 15 of 20 results are "N Claude skills for ..." listicles, several role-specific (real estate, business owners, design, content).
- Copilot and Gems: both sell role-specific agents or Gems as the team default.
- Paraphrase: people want to start from "skills for a sales ops person", not a blank editor.

### 6. Sharing and updating across a team without git. Partly KNOWN (source-update, F13). Confidence M.
- YouTube "How to Share (and Update) Claude Skills Across Your Team" (8,584 views). Comment from a company owner: they moved to Teams and want a "team of real people" setup.
- Anthropic: approved updates reach users automatically; until approval, users stay on the current version. Users cannot delete provisioned skills, only turn them off.
- Paraphrase: versioning should be visible to people who have never used git. Version pinning and "what changed" are wanted.

### 7. Usage and cost visibility for managers. NEW for Skills Manager (F1 covers the individual's own library, not the team). Confidence H.
- ChatGPT admin Skills page: owner, access, users, invocations over 30 days, created and updated dates.
- Notion custom agents (Notion release page, search snippet): per-agent credit caps, workspace-wide cap for Enterprise, admin approval for higher limits, auto-pause on unusual spend.
- Anthropic: audit log records share events, not skill contents.
- Paraphrase: managers want to know which skill is used, by whom, and what it costs, without reading transcripts.

### 8. Audit, compliance and PII. NEW. Confidence H.
- ChatGPT: Compliance Logs Platform support for skill activity.
- Notion: every run is logged with trigger, actions and reason.
- Anthropic: HIPAA readiness turns skills off until an owner re-enables them. Scanning and duplicate checks are unavailable for HIPAA and CMEK configurations.
- Paraphrase: regulated teams need "who changed this skill and what did it contain", plus a PII check before a skill is shared.

### 9. Security scan states users cannot interpret. Mostly KNOWN (doc 59 security). Confidence M.
- ChatGPT: "Needs Review" and "Blocked" states, with the note that a scan does not replace your own review.
- Anthropic: scanning is Enterprise-only.
- NEW angle: a plain-language reason for a block, and who can override it (Anthropic: uploaders cannot override a blocked skill unless owner or library manager).

### 10. Testing for non-developers. Partly KNOWN (trigger tests, F3). NEW as plain-language cases. Confidence M.
- Anthropic help: test by asking Claude to evaluate the skill, and check the description matches when it should trigger (search snippet).
- Paraphrase: non-developers test by chatting. They need a "try these three example inputs" checklist, not eval statistics.

### 11. Surface fragmentation. Confidence L.
- YouTube comment: Claude Code cannot read Claude Desktop threads, and the reverse. A commenter asks whether one run covers both Cowork and Code.
- Anthropic: skills sync to Claude Code for signed-in users, and admins can stop that sync.
- Paraphrase: people do not know where a skill runs.

## Feature ideas implied (NEW items first)

1. Team approval queue with Requires-review and Open modes, showing the exact submitted version.
2. Visibility panel: who can see each skill now, and what a revoke will and will not remove.
3. "Which should I use?" explainer that compares rule, skill, project and custom agent.
4. SOP to skill converter: upload a Word or Notion procedure, output a draft plus three example inputs and outputs. Reuses F5 redaction.
5. Role starter packs: curated, reviewed starter skill sets per job role.
6. Team catalogue with version pinning, "what changed", and default for new members.
7. Manager usage report: uses over 30 days, owner, last change, cost estimate.
8. Compliance export: change history with contents, plus PII scan before sharing.
9. Plain-language block and review reasons, with a clear next step.
10. Non-developer test script: three example inputs, expected behaviour, pass or fail by reading.
11. Location labels: show where each skill runs (desktop, Code, admin-provisioned).

## Known vs new summary

- KNOWN and reinforced: sprawl (F1), grounding from real work (F5), security scanning (F15), source update review (F13), trigger tests (F3).
- NEW: approval and publishing gates, visibility and revoke clarity, role starter packs, SOP conversion, manager usage report, compliance export with contents, plain-language testing, surface labels, "which tool" explainer.

## Caveats

- Reddit was blocked on every search, so the non-developer voice is mostly from vendor docs and YouTube and Substack content. That is a weak substitute for user complaints.
- Medium and Substack listicles reflect content supply, not user demand.
- The OpenAI page (WebFetch) reports that Skills are off by default for Enterprise and Edu. A search snippet also mentioned a July 23, 2026 default-on date from one Spanish page. Treated as [?].
- Notion's "Notion 3.7: Agent skills for your whole team" release headline could not be read in full. Skills governance there is [?].
- Vendor pages change often. Dates on Anthropic's admin page were not shown.
