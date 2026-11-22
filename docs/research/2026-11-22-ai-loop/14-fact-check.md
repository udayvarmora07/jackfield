# Round 3 fact-check: 30 high-weight claims (2026-11-22)

Scope: 30 claims picked from the seven r2/r3 research reports for weight (large numbers, strong statements, version and star facts). Each was checked against its primary source on 2026-11-22. The reports were not edited.

Verdict key: CONFIRMED = the stated fact matches the source. PARTLY = the source supports the core point but a figure, qualifier or label is wrong or missing (correction given). WRONG = the source contradicts the claim. UNREACHABLE = the source could not be read.

Tolerance for live counters (stars, points, comments): a difference of 5 or fewer points, or within 5%, is treated as timing drift and not as an error. Comment counts are not returned by `opencli reddit read`, so they are reported as "not reconciled" and do not change a verdict on their own.

Evidence files: `scratchpad/factcheck/` (rd_*.json = opencli Reddit reads, hn_*.json = HN Algolia item JSON, body_*.txt = GitHub issue bodies, cisco_readme.md, plugin_evals.html, support_admin.html).

## Results

| # | Report file : line | Claim as stated | What the source says | Verdict | Date checked | Source |
|---|---|---|---|---|---|---|
| 1 | r2-github-hn.md:12 | claude-code #31005 "+649" (AGENTS.md/.agents/skills) | Total reactions 649, but +1 alone is 492. Open, 38 comments, created 2026-03-05. The "+N" in the report is the all-emoji total. | PARTLY: label should say total reactions (+1 = 492) | 2026-11-22 | https://github.com/anthropics/claude-code/issues/31005 |
| 2 | r2-github-hn.md:12 | claude-code #6235 "+6693", AGENTS.md only | Total reactions 6,693 (+1 = 5,194). Title "Feature Request: Support AGENTS.md." Closed 2026-08-17, 409 comments. | PARTLY: +6,693 is total of all reactions, not +1 | 2026-11-22 | https://github.com/anthropics/claude-code/issues/6235 |
| 3 | r2-github-hn.md:23 | claude-code #35319 "+43, 8 comments, closed"; org went from 67 to 183 skills in a month | Total 43 (+1 = 43), 8 comments, closed 2026-08-17. Body: "Our org went from 67 to 183 skills in under a month." | CONFIRMED | 2026-11-22 | https://github.com/anthropics/claude-code/issues/35319 |
| 4 | r2-github-hn.md:12, :60 | claude-code #28729 "+160"; 39 comments | Total 160 (+1 = 100), 39 comments, created 2026-02-25, open. | PARTLY: +160 is total of all reactions, not +1 | 2026-11-22 | https://github.com/anthropics/claude-code/issues/28729 |
| 5 | r2-github-hn.md:30 | codex #19679: +40, 21 comments; fixed 2% budget | 40 reactions (+1 = 40), 21 comments, created 2026-04-26. Title: "instead of hardcoded 2%." | CONFIRMED | 2026-11-22 | https://github.com/openai/codex/issues/19679 |
| 6 | r2-github-hn.md:72 | anthropics/skills #492: 46 comments; 6 of 580+ skills with Bash allowed | 46 comments. Body: "audit of 580+ installed Claude Code skills, we found 6 skills placed under ~/.claude/skills/anthropic/", each listed with Bash. | CONFIRMED | 2026-11-22 | https://github.com/anthropics/skills/issues/492 |
| 7 | r2-github-hn.md:84 | xingkongliang/skills-manager 7,681 stars | 7,681 stars, created 2026-03-02. | CONFIRMED | 2026-11-22 | https://github.com/xingkongliang/skills-manager |
| 8 | r2-github-hn.md:90 | NVIDIA/SkillSpector 27,209 stars (flagged as anomalous) | 27,210 stars (1 star drift), created 2026-03-21. The report's doubt about the figure is reasonable but the figure is accurate. | CONFIRMED | 2026-11-22 | https://github.com/NVIDIA/SkillSpector |
| 9 | r2-github-hn.md:92 | alchaincyf/darwin-skill 7,024 stars | 7,024 stars, created 2026-04-13. | CONFIRMED | 2026-11-22 | https://github.com/alchaincyf/darwin-skill |
| 10 | r2-github-hn.md:104 | lawrence3699/agent-skills-corpus: 55,698 public skills, 4 stars | Description: "55,698 public Agent Skills"; 4 stars; created 2026-07-18. | CONFIRMED | 2026-11-22 | https://github.com/lawrence3699/agent-skills-corpus |
| 11 | r2-products.md:99 | microsoft/SkillOpt 19k stars | 19,179 stars, created 2026-05-08. | CONFIRMED | 2026-11-22 | https://github.com/microsoft/SkillOpt |
| 12 | r2-github-hn.md:39 | opencode #65485 (2026-11-21): receipts, pins, rollback | Created 2026-11-21, open, 1 comment. Title: "Managed skill installation receipts, pins and rollback." Body not read, so the list of fields is unchecked. | CONFIRMED (date and title; body not checked) | 2026-11-22 | https://github.com/anomalyco/opencode/issues/65485 |
| 13 | r2-github-hn.md:45 | HN "AGENTS.md outperforms skills in our agent evals", 524 pts, 196 comments; skill never invoked in 56% of cases | 524 points, 196 comments, 2026-01-29. A comment quotes the post: "In 56% of eval cases, the skill was never invoked." | CONFIRMED | 2026-11-22 | https://news.ycombinator.com/item?id=46809708 |
| 14 | r2-github-hn.md:46 | HN "Agent Skills", 544 pts, 260 comments | 544 points, 260 comments, 2026-02-03. | CONFIRMED | 2026-11-22 | https://news.ycombinator.com/item?id=46871173 |
| 15 | r2-github-hn.md:41 | HN "Dockerhub for Skill.md", 49 pts: "no versioning, no update, no author verification" | 49 points, 26 comments. The commenter wrote "You have no versioning, no automated or simplified update, no way to verify the authors." The report's quote drops words without marking the cut. | PARTLY: quote is abridged but presented as verbatim; meaning intact | 2026-11-22 | https://news.ycombinator.com/item?id=46692692 |
| 16 | r3-opencli-social.md:46 | HN Ask HN "How do you evaluate the skills your AI agents use?", 26 pts, 8 comments | 26 points, 8 comments, 2026-11-09. Commenter: skill behaviour changes "with each new model". | CONFIRMED | 2026-11-22 | https://news.ycombinator.com/item?id=50426070 |
| 17 | r2-github-hn.md:75 | HN "Claude Code now reads AGENTS.md if no CLAUDE.md", 741 pts, 285 comments, 2026-09-18 | 741 points, 285 comments, 2026-09-18. Title reads "if there is no Claude.md." Changelog quote in a comment: version 2.1.277. | CONFIRMED | 2026-11-22 | https://news.ycombinator.com/item?id=49760187 |
| 18 | r2-github-hn.md:31 | HN paper thread: ceiling is about 100 reliably triggerable skills; least-invoked lose descriptions first | Comment by the thread's apparent author (meame2010, 2026-08-17): "the ceiling is about 100 reliably triggerable skills, and eviction starts with the ones you have invoked least." Single self-reported claim, not independently tested. | CONFIRMED as a quote; the 100 figure is unverified as fact | 2026-11-22 | https://news.ycombinator.com/item?id=49335376 |
| 19 | r2-reddit.md:28 | r/ClaudeAI 1v5mhhl: 1,560 pts, 80+ comments; Anthropic cut about 80% of the system prompt; top comment 319 "Use progressive disclosure" | Post score 1,562. Post says "cut 80% of Claude Code's system prompt." Mod summary: "after 80 comments." Top comment 322: "Use progressive disclosure." Post date not returned by opencli. | CONFIRMED (date unverified) | 2026-11-22 | https://www.reddit.com/r/ClaudeAI/comments/1v5mhhl/ |
| 20 | r2-reddit.md:87 | r/ClaudeAI "Teach Claude a skill": 2,734 pts, 129 comments; "factory workers assembling the robots" | Post titled "New: Teach Claude a skill", score 2,727. Comment with score 345: "factory workers assembling the robots that replace them." Comment count not reconciled. | CONFIRMED (score drift -7; comment count not reconciled) | 2026-11-22 | https://www.reddit.com/r/ClaudeAI/comments/1v2qdct/ |
| 21 | r2-reddit.md:58 | Placebo test: 9 popular skills vs same-length sugar pill; 2 beat it; 1 worse (80% vs 100%); 26 pts / 18 comments | Post titled "I gave the 9 most popular Claude Code skills a sugar pill. 2 beat it, 1 did worse than the pill." 80% vs 100% confirmed. Score 24 (drift 2). 16 comment items returned vs 18 claimed. | CONFIRMED (headline figures match; minor drift) | 2026-11-22 | https://www.reddit.com/r/ClaudeAI/comments/1wz4rfz/ |
| 22 | r2-reddit.md:44 | "104 skills installed, 42 never used"; counts skill calls from logs; hook-fired skills show as never used | Post: "[Free] 104 skills installed, 42 never used." Tool named Loadout. Author confirms a hook-fired skill "lands in the 'never used' bucket." Score 75. The subreddit is not shown in the output. | CONFIRMED (the "MCP wrapper" sub-claim is not found in the fetched comments) | 2026-11-22 | https://www.reddit.com/r/claudeskills/comments/1vxhbch/ |
| 23 | r2-reddit.md:51 | r/ClaudeCode 35K to 13K startup tokens; MCP tools/list 44KB, 26KB outputSchema; 76 pts | Post: "~35K tokens" down to "~13K." Comment: tools/list "at 44KB, and 26KB of that was outputSchema." Score 74 (drift 2). | CONFIRMED | 2026-11-22 | https://www.reddit.com/r/ClaudeCode/comments/1vklbtg/ |
| 24 | r2-reddit.md:52 | r/opencodeCLI: 2,004 skills; startup context 80K to about 255 tokens; 151 pts | Post: "2,004 AI skills installed", "~80K tokens" to "~255 tokens (99.7% reduction)", score 151. | CONFIRMED | 2026-11-22 | https://www.reddit.com/r/opencodeCLI/comments/1rfwlzk/ |
| 25 | r2-reddit.md:79 | r/ClaudeCode: CLAUDE.md of 800 lines split into 27 files; top answer is subfolder CLAUDE.md or .claude/rules/ with paths:; 327 pts / 97 comments | 800 lines and 27 files confirmed. Top answer confirmed (score 26: subfolder files and ".claude/rules/ directory with paths: frontmatter"). Post score 361, which is 34 points off the report. Comment count not reconciled. | PARTLY: score stale by 34 points (about 10%); comment count not reconciled | 2026-11-22 | https://www.reddit.com/r/ClaudeCode/comments/1rhe89z/ |
| 26 | r2-reddit.md:62 | r/claudeskills UiPath: baseline activation recall 46% across 20 skills; same on Codex; daily sample of 20 prompts per skill | "Baseline recall started at 46%" and 20 skills confirmed. Daily 20-per-skill stratified sample confirmed. Commenter: "Already ran it on Codex... Same shape." Score 12 (report 14). | CONFIRMED | 2026-11-22 | https://www.reddit.com/r/claudeskills/comments/1waq4j9/ |
| 27 | r2-reddit.md:75 | r/ClaudeAI 2026-10-20: 6,309 public skills; 5.4% threat verdict; about 70% carry at least one risky capability | 6,309 and 5.4% confirmed. The post says 70% carry "at least one capability worth knowing about" (shell 50%, file writes, ...). The word "risky" is not in the post. | PARTLY: the post says "worth knowing about", not "risky" | 2026-11-22 | https://www.reddit.com/r/ClaudeAI/comments/1xb2eyh/ |
| 28 | r2-products.md:45 | Cisco skill-scanner: rules alone catch 7.7% of malicious skills at 4.0% FPR; with judge 66.7% reach review at MEDIUM+ (15.4% FPR) | README: "Rules alone catch 7.7% of malicious skills at HIGH, at a 4.0% false-positive rate." Judge figure: 66.7% at MEDIUM+ with 15.4% FPR, using the balanced preset and a Gemma 4 26B judge. Numbers match, but the report drops "at HIGH" for the rules-only figure. | PARTLY: rules-only figure is at HIGH severity; judge figure needs its preset and model | 2026-11-22 | https://github.com/cisco-ai-defense/skill-scanner |
| 29 | r2-github-hn.md:49 | Anthropic `claude plugin eval`: cases x runs (default 3, up to 50); plugin and no-plugin arms; six grader types incl. regex, tool_used, rubric; verdict improved/flat/regressed; CI gate | Docs: "each case runs three times by default"; `--runs` 1 to 50; baseline (no-plugin) arm; verdict line "improved 2, flat 1, regressed 0 of 3 cases"; "Run evals in CI." Grader names found: contains, file_exists, mock_calls, regex, rubric, tool_used (six). | CONFIRMED | 2026-11-22 | https://code.claude.com/docs/en/plugin-evals |
| 30 | r3-nondev-enterprise.md:31 | Anthropic admin article: publishing has three modes, Requires review, Open, Off | Publishing choices are "Requires review," "Open," and "Off," under Organization settings > Plugins & skills > Policy. | CONFIRMED | 2026-11-22 | https://support.claude.com/en/articles/13119606 |

## Verdict counts

- CONFIRMED: 23
- PARTLY: 7 (rows 1, 2, 4, 15, 25, 27, 28)
- WRONG: 0
- UNREACHABLE: 0

## Error patterns

1. **Reaction labels.** Three GitHub figures are written as "+N" but are totals across all emoji reactions. The +1 counts are lower (492, 5,194, 100). A reader would take them as thumbs-up counts. Use "total reactions" or give the +1 count.
2. **Dropped qualifiers.** Two cases lose a qualifier that changes the meaning. Cisco's rules-only 7.7% applies at HIGH severity only. The Reddit "risky" label replaces the post's softer "worth knowing about."
3. **Quote cuts not marked.** An HN quote is shortened with no ellipsis. The meaning holds, but the text is presented as verbatim.
4. **Stale live counters.** Scores drifted from 2 to 34 points between fetch and check, most on fast-moving Reddit threads. Only row 25 is outside tolerance. Reports should timestamp scores.
5. **Unreconciled counts.** Reddit comment totals and post dates are not returned by `opencli reddit read`. Those figures are unverified here, not wrong.

Overall: the GitHub, HN and vendor-doc numbers held up closely. Most errors are in Reddit figures, where reports paraphrase or attach a label the post does not use.

## Not checked

- Outside the 30, the Bilibili BV1L7xm64EHP figures in r3-chinese.md:70 were also checked and confirmed: 1,186,692 views, 54,736 likes, 95,271 favourites.
- Tessl's "1.44x" headline, skills.sh install totals and the YouTube view counts were not checked. The live pages were not fetched.
- Reddit post dates (rows 19-27) could not be checked because opencli does not return them.
- The opencode #65485 body (row 12) and the Anthropic admin "Requests tab" sub-claim (row 30) were not read in full.
