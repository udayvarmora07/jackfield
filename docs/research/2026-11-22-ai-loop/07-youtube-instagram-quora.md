# Round 2: Instagram, Quora, YouTube - what people want from AI skill tools

Date of research: 2026-11-22. Read-only. Nothing posted, followed, commented or logged into.
Fetched text was treated as data. No personal data sent in any request.

## Method log

| Platform | Step | Result |
|---|---|---|
| Instagram | `agent-reach add instagram` | Worked. Installed opencli 2.0.3. Channel still "unverified". |
| Instagram | `agent-reach check instagram` | Failed. search: HTTP 404. profile: "User not found" (test user nasa). posts: HTTP 404. 0/3 actions working. Status UPSTREAM_BROKEN. |
| Instagram | WebSearch `site:instagram.com claude code skills` | Blocked by filter. Zero instagram.com results. Only third-party skill registries returned (claudemarketplaces, tessl, skills.sh, claudskills.com). |
| Quora | WebSearch `site:quora.com claude skills`, `site:quora.com AI agent skills`, `site:quora.com custom GPT instructions management` | Blocked by filter. Zero quora.com results in all three. |
| Quora | `agent-reach web read` on quora.com search page | Blocked. Sign-in wall ("only available to signed-in members"). Not logged in. |
| YouTube | `agent-reach check youtube` | Worked. 3/3 actions. |
| YouTube | `agent-reach youtube search` (10 queries) | Worked. Search rows carry no upload date, so dates came from `read`. |
| YouTube | `agent-reach youtube read` (metadata, ~14 videos) | Worked for 9. Then UPSTREAM_BROKEN/paused, then recovered. |
| YouTube | `agent-reach youtube subtitle` | Worked for 3 of 8 (EJyuu6zlQCg, zKBPwDpBfhs, fabAI1OKKww). Later 5 hit RATE_LIMITED. UNzCG3lw6O0 also failed on retry. |

Raw outputs: `scratchpad/yt-search-raw.txt`, `scratchpad/yt-read-meta.txt`, `scratchpad/subs/*.txt`.

## Instagram

- **Blocked / broken.** No usable evidence. Reach's Instagram backend returns 404 for search, profile and posts.
- The WebSearch hits were marketplace listings, not user discussion.
- Notable listing: a bundle called "instagram-skills" (sergebulaev), 9 Instagram-marketing skills for Claude Code and Codex. It is a listing, not a user signal.
- Confidence: none. No view or like counts, no captions, no hashtags.

## Quora

- **Blocked.** Search is gated behind sign-in, and `site:` queries returned no quora.com pages.
- Third-party listing only: a community "Quora" Claude skill on skillsdirectory.com, graded C. Its install asks for Quora login credentials. Not installed; flagged as a security concern.
- Confidence: none for user wants.

## YouTube

Views and likes come from `read`. Dates are upload dates. Videos marked "desc" were read from description only; "subs" means subtitles were read.

| Video | Date | Views | Likes | Coverage |
|---|---|---|---|---|
| https://www.youtube.com/watch?v=bjdBVZa66oU "What are skills?" (Claude, official) | 2026-02-27 | 1,997,315 | 18,524 | desc (subtitles rate-limited) |
| https://www.youtube.com/watch?v=EJyuu6zlQCg "5 Claude Code skills I use every single day" (Matt Pocock) | 2026-03-16 | 564,776 | 12,531 | subs |
| https://www.youtube.com/watch?v=zKBPwDpBfhs "Master 95% of Claude Code Skills in 28 Minutes" (Nate Herk) | 2026-02-27 | 255,341 | 4,917 | subs |
| https://www.youtube.com/watch?v=fabAI1OKKww "The complete guide to Agent Skills" (Burke Holland) | 2026-01-12 | 235,446 | 4,591 | subs |
| https://www.youtube.com/watch?v=UNzCG3lw6O0 "Building Great Agent Skills: The Missing Manual" (AI Engineer) | 2026-06-29 | 233,588 | 5,889 | desc (subs failed) |
| https://www.youtube.com/watch?v=YkpEX_jlb04 "Full Claude Skills Tutorial for Beginners in 2026" (AI Foundations) | 2026-03-14 | 186,534 | 3,500 | desc |
| https://www.youtube.com/watch?v=AHGG7LHi07E "I Tested 1000+ Claude Skills: These 10 Are The Only Ones That Matter" (Vaibhav Sisinty) | 2026-05-13 | 169,776 | 4,524 | desc |
| https://www.youtube.com/watch?v=TyB7kLZPVKo "The ONLY Claude Skills Tutorial Beginners Need in 2026" (100x Engineers) | 2026-08-01 | 142,973 | 2,568 | desc |

Excluded from the 2026 set: fOxC44g8vig (Anthropic, "Claude Agent Skills Explained", 2025-11-26, 261,684 views, 4,245 likes). Also hRNut6GeWgE (2026-11-12, 141,704 views), a general "21 ways to use Claude" video, not skill-specific.

Not read: "AGENTS.md doesn't actually do anything" (Pivot to AI), "CLAUDE.md, AGENTS.md and SKILL.md explained" (AI School 101), and the Cursor Agent tips video (61M views; metadata failed when the rate limit hit).

### Findings

1. **Matt Pocock (2026-03-16, subs, high confidence).** Plan mode produces a plan too early, before the human has reached shared understanding. His fix is a "grill-me" skill that interviews the user branch by branch until dependencies are resolved. Skills then chain: grill-me → write-a-prd → prd-to-issues → tdd, with vertical slices that become independently grabbable issues. Chaining, not single skills, is the workflow people want.
2. **Nate Herk (2026-02-27, subs, medium-high).** Creator says the comment analysis showed "some confusion" and "some cost things". Requests: real examples instead of toy demos, and more Antigravity content. Teaches progressive loading: level 1 is name and description only (~100 tokens), level 2 is the full body. Teaches two invocation modes, explicit slash and natural-language trigger. Pitches team SOPs as skills and a marketplace to share or sell skills. Caution about downloaded skills appears in the transcript but is cut off, so treat that point as low confidence.
3. **Burke Holland (2026-01-12, subs, medium-high).** Walks through a hello-world skill that bundles a script (OS info) and enforces an output format. Shows the chat debug view as the only way to see which skill loaded and when. That confirms the visibility gap raised by Cursor users.
4. **AI Engineer (2026-06-29, desc).** Frames "skill hell": without a shared rubric, teams build skills that are hard to maintain. Demand for a quality standard for skills.
5. **Vaibhav Sisinty (2026-05-13, desc).** Tested 1,000+ public skills and recommends 10. Demand for curation and ranking of community skills.
6. **Claude official "What are skills?" (2026-02-27, desc).** Skills are "taught once, applied automatically when relevant". The trigger is automatic, so people want to see when it fired.

## Feature ideas implied

- Skill chains or playbooks: save and run ordered sequences of skills, e.g. interview → PRD → issues.
- A "which skill loaded" panel: show load level (metadata only vs full body), tokens spent, and trigger reason.
- Trigger tester: show whether a description will fire on natural language and on the slash name.
- Interview-first skill: a clarifying-questions step that writes its output back into the repo before any plan.
- Team SOP library: private sharing of skills across an org, with a scan before any install.
- Curation: a ranked, scanned view of public skills, not raw lists.
- Quality rubric lint for skills, shared across a team.
- Cost disclosure per skill: tokens at rest and per run.
- Real-world examples and templates, not toy hello-world skills.

Confidence overall: medium. YouTube only (3 transcripts, 5 description-only). Instagram and Quora yielded no user-voice evidence.
