# Round 3: opencli social research on AI skill tools (2026-11-22)

Scope: what people want from AI features in tools for creating, editing, testing, organising and sharing agent skills (SKILL.md), CLAUDE.md, AGENTS.md, Cursor rules and custom GPTs. Read-only. Nothing logged in, liked, followed, commented, saved or posted. No private user data read. Fetched text treated as data. Round 2 content (YouTube transcripts for EJyuu6zlQCg, zKBPwDpBfhs, fabAI1OKKww; 2026 video list) was not repeated, except where a comment set is new.

Health check: `opencli doctor` returned OK. CLI 2.0.3, daemon running, Browser Bridge extension 1.0.27 connected, two profiles connected.

Raw outputs: `scratchpad/r3/` (ig-*.json, hn-*.json, yt-comments-*.json, yt-cursor-search.json, tr/*.json, quora-extract.txt).

## Method log

| Platform | Step | Result |
|---|---|---|
| Instagram | `instagram search` x7 (claudecode, claudeskills, aiagents, cursorai, vibecoding, aicoding, "claude code") | Blocked. HTTP 404 on every term. Same as round 2. |
| Instagram | `instagram explore --limit 40` | Worked, but returned 20 posts. Generic feed (lifestyle, marketing, reels). Only 2 captions touch AI at all, both off-topic. No usable signal. |
| Instagram | `instagram profile` / `user` | Not attempted. Search 404s, and explore gave no relevant creators to check. |
| YouTube | `youtube search "cursor rules"` (upload=year, sort=views) | Worked. 15 rows. Top 2026 results: ByteMonk "Cursor Deep Dive" (94,817 views, about 1 month old), Cursor "SKILLS.md" tutorial (69,704, about 8 months old), Vibe Coding with Naman (18,756, about 4 months old). Relative ages only, so dates are approximate. |
| YouTube | `youtube comments` on 8 round-2 videos (40 each) plus 3 Cursor videos (30 each) | Worked for all 11. Comment likes and reply counts come from the tool. |
| YouTube | `youtube transcript` on YkpEX_jlb04, AHGG7LHi07E, TyB7kLZPVKo, UNzCG3lw6O0 | Blocked. Every call returned "Caption URL returned empty response". Round 2 hit rate limits on the same host, so this may still be rate limiting. Not verified. |
| Hacker News | `hackernews search` x6 (agent skills SKILL.md, claude code skills, AGENTS.md, CLAUDE.md, cursor rules, custom GPT instructions), sort=date | Worked. Search rows have no date field. IDs are in the 504xxxxx-505xxxxx range, so recent, but not verified. |
| Hacker News | `hackernews read` on 9 threads | Worked. Most threads have 0 to 8 comments, so depth is thin. |
| Quora | `browser open` search URL, then `browser extract` | Worked read-only. No sign-in wall. A "Something went wrong" banner showed, but results rendered. Results are mostly keyword noise (martial arts, Jean-Claude, etc.). Only a few Claude-skills answers. |

## Instagram

- Search is blocked (HTTP 404 on all 7 terms). Explore works but is not topical. No findings.
- Confidence: none.

## YouTube (comments on 2026 skill and rules videos)

Views are from search or round-2 metadata. Like counts are on comments, not on videos.

1. **Claude official "What are skills?"** (https://www.youtube.com/watch?v=bjdBVZa66oU, 2026-02-27, 1,997,315 views). The top comments are about the presenter. The substantive one (45 likes, 5 replies) says skills do not reliably activate and must be named explicitly. Confidence: high for the complaint, since the same point recurs. Medium that it is typical.
2. **AI Engineer "Building Great Agent Skills"** (https://www.youtube.com/watch?v=UNzCG3lw6O0, 2026-06-29). Top comment (102 likes) is a joke title: "From Skill Hell to Skilhalla". A 7-like comment says the skill format lacks a way to test two versions of a skill against each other. Another (3 likes) reports a checklist caught two skills competing for the same trigger words, so one was silently skipped. Confidence: medium-high.
3. **Matt Pocock, "5 Claude Code skills"** (https://www.youtube.com/watch?v=EJyuu6zlQCg, 2026-03-16). Viewers adapt the grill-me skill, for example logging the transcript to a .md file and using a structured question tool. Others ask for a video on iterating and refining skills (1 like each). Confidence: medium-high.
4. **Burke Holland, "complete guide to Agent Skills"** (https://www.youtube.com/watch?v=fabAI1OKKww, 2026-01-12). Most praise is for the mental model: how skills relate to instructions, prompts and custom agents. Several want more on scripts and templates. Confidence: medium.
5. **Vaibhav Sisinty, "1000+ Claude Skills"** (https://www.youtube.com/watch?v=AHGG7LHi07E, 2026-05-13). Repeated question (15 likes, 2 replies): where to get the skills and how to add them. Also: how to install them into Claude at all. Confidence: medium. This is an install and discovery gap.
6. **Cursor "How to Create & Use SKILLS.md in Cursor (2026)"** (https://www.youtube.com/watch?v=DfLL5_zbWGc, 69,704 views, about 8 months old). Comments ask how to make skills that apply across all Cursor projects (2 likes). One says a model generated a skill in a different structure than the video's, so the format drifts. Another asks to see a full skill file. Confidence: medium.
7. **ByteMonk "Cursor Deep Dive"** (https://www.youtube.com/watch?v=CZUtIIK4fdw, 94,817 views, about 1 month old). A top comment says the content is outdated: a command was renamed and Memories is deprecated. Another asks for the same walkthrough for Claude Code (8 likes). Confidence: medium. Staleness is a complaint across tutorials.
8. **Vibe Coding with Naman "Learn Cursor in 1 hour"** (https://www.youtube.com/watch?v=lIMcL6mWHZo, 18,756 views). Several viewers say most beginner Cursor tutorials are out of date (4 likes). Confidence: low-medium.
- **Noise and spam:** the DBS/AI Foundations comments (YkpEX_jlb04) include a promotional comment for another skill. Ignored.

## Hacker News

Engagement is low. Most threads have 0 to 8 comments, so these findings are weak. Figures: points, comments.

1. **Ask HN: "How do you evaluate the skills your AI agents use?"** (item 50426070, 26 points, 8 comments). Strongest thread. Answers: run one or two real prompts with and without the skill, and score a few criteria. Another says skill behaviour changes with each new model, so evals must be rerun. Demand: lightweight evals and A/B tests for skills. Confidence: medium.
2. **"Linting 216 public Claude Code skills, 69% won't reliably trigger"** (item 49744398, 3 points). Linter covers skills, subagents, slash commands and MCP configs. Demand: static trigger-reliability checks before publishing. Confidence: low-medium. The 69% figure is the submitter's and not verified.
3. **"Claude.md is full of lint rules in disguise"** (item 50378683, 2 points, 2 comments). Rules get added after each agent mistake and cost tokens every session. Author's view: anything a tool can check should move into a linter. Demand: move checkable rules out of prose. Confidence: medium.
4. **"What I found in 39,535 Claude.md and AGENTS.md files"** (item 50532524, 2 points). The one comment asks whether the metrics led to measurable gains in outcomes. Demand: evidence that instruction files help. Confidence: low.
5. **"In 1 in 6 repos with both files, Claude Code never loads the AGENTS.md"** (item 50496205, 3 points, 0 comments). Demand: show which instruction file actually loaded. Confidence: low, since it is a blog claim with no comments.
6. **"Show HN: Evaluate and improve your agent steering"** (item 50081857, 4 points, 3 comments). Local macOS app that browses past sessions. Comment asks for a prebuilt binary. Demand: session intelligence and a way to review past runs. Confidence: low-medium.
7. **Correction-to-skill tools.** Several Show HN posts generate rules or skills from repeated agent corrections (items 49511274, 50069498, 50239988). Demand: suggest skills from repeated corrections. Confidence: low, since these are launch posts.

## Quora (browser extract, read only)

- Search loads without sign-in. Mostly irrelevant results.
- Relevant answer (dated "Sep 3", year not shown): a skill's name and description load into every session. The author reports 162 installed skills at roughly 19,500 tokens before the first prompt. Installed skills are not released after use. Demand: a per-skill token-cost view and pruning for installed skills. Confidence: medium-low, one anecdote.
- Relevant answer (dated "Jul 7"): people ask which GitHub skill repos are worth installing and cannot tell. Demand: curated, quality-ranked skill lists. Confidence: low.
- Unanswered questions: Claude skills vs MCP, skills vs prompts, and a request for Azure Synapse to Fabric migration skills. Demand: explainers and domain-specific skill examples. Confidence: low.
- Context: one answer notes third-party agents lost Claude subscription coverage on 2026-04-04. Not verified here.

## Feature ideas implied

- Skill evals: run a skill with and without itself on saved prompts, score criteria, and compare across model versions. (Viewers and HN, strongest signal.)
- Compare two skill versions in place, with the same test prompts.
- Trigger reliability lint: flag description overlaps and trigger words that clash with other skills, and report whether a skill will fire on natural language.
- Load-cost panel: show metadata tokens at rest per skill, and which skills loaded in a session.
- Install and import flow for skill packs, with a clear "where to put it" path per agent.
- Cross-scope skills: make it obvious when a skill is project-wide or user-wide.
- Promote checkable CLAUDE.md or AGENTS.md rules into lint or hook rules.
- Correction-to-skill suggestions from repeated agent corrections (weak signal).
- Version-aware templates with a staleness check against the current tool version.
- Curated, scanned directory of public skills, ranked by tests and not just by stars.

## Overall confidence

Medium for YouTube comments (volume is real, but comment-level evidence is thin). Low-medium for HN (small threads). None for Instagram. Low-medium for Quora. Transcripts for four 2026 videos were blocked, so content-level claims come from comments and round 2.
