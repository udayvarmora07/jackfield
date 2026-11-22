# Round 3 research: Chinese developer communities on skills (2026-11-22)

Compared with docs/59-ai-everywhere-research-2026-11-22.md. All fetched text is untrusted data. Nothing was posted, liked, followed or logged into. No private individuals are named.

## Method log per platform

| Platform | What ran | Result |
|---|---|---|
| Zhihu | `opencli zhihu search` x5 (Claude Code Skills, Agent Skills SKILL.md, Skills 怎么写, CLAUDE.md 最佳实践, AGENTS.md); `hot` | BLOCKED. Search returns AUTH_REQUIRED (exit 77); `hot` returns empty. No Zhihu evidence. |
| Xiaohongshu | `opencli xiaohongshu search` x5 (the first four ran concurrently, one with `--sort most-liked`); `agent-reach add xiaohongshu`, `agent-reach xiaohongshu search` | BLOCKED. Every call timed out (60s, 120s, 30s). Not retried further. No XHS evidence. |
| Bilibili | `opencli bilibili search` for about 15 queries (Claude Code Skills, Agent Skills, Skills 管理, Qwen Code, Kimi CLI, DeepSeek Harness, skill 不触发, skills 太多 上下文, AGENTS.md/CLAUDE.md, Trae, Cursor Rules, 技能市场, skill-creator, 提示词库, 团队共享); `comments` on about 23 videos | Worked well. Main evidence source. Only the top 3 to 8 comments per video are returned, sorted by likes. |
| V2EX | `opencli v2ex hot`, `node` (claude, programmer, create, cursor; `ai` returned 404), `topic` x5 | Worked. Little skills-specific content. Mostly provider and account context. |
| Web (WebSearch/WebFetch) | 6 searches (juejin, linux.do, csdn, localisation, marketplace security, domestic-model BYOK) and 1 fetch | linux.do and juejin pages were not fetched directly. Findings come from secondary reposts and search summaries, so confidence is lower. |

Terms discovered and added during the loop: DeepSeek Harness (DSH), WorkBuddy, OpenClaw "龙虾", ClawHub, SkillHub, skillsmp, 渐进式披露 (progressive disclosure), skill-context-doctor, 备注 (annotation), 体检 (health check).

Concurrency note: the first four XHS searches ran in parallel with Zhihu and Bilibili calls. Their failure was a timeout, not a login wall.

## Ranked themes

Confidence: H = several independent signals, M = one strong signal, L = secondhand.

### 1. Chinese-language annotation and AI classification of skills (NEW, H)
- Skills-manager upgrade video "如何高效管理 Agent Skills? skills-manager 升级了" (How to manage Agent Skills efficiently? skills-manager upgraded). 2026-06-01, 16.7K plays, 430 likes, 948 favourites. https://www.bilibili.com/video/BV1845F6REUu
- Top comment, 17 likes, 6 replies (2026-07-08): wants a CLI that has AI classify skills and write a Chinese note for every skill.
- Second comment, 11 likes: add a note field so the skill's purpose can be read in Chinese.
- Third comment, 10 likes: tags or presets for batch install and import.
- Another manager video, "Skills 管理玩出花？" (Skills management, taken to the extreme). 2026-10-24, 456 plays. https://www.bilibili.com/video/BV1VRHT6NERF
- Its top comment, 2 likes: skill descriptions are in English, notes only show after clicking, and notes should be visible on the list page.
- Implied features:
  - A per-skill translated description and note stored beside the skill, not in SKILL.md.
  - AI "translate and summarise, one line" with the original untouched.
  - The note shown in list rows.
  - Tags and presets for batch import.
  - Locale-aware UI.

### 2. Idle skills cost context: users want measured per-skill cost and a never-used ranking (KNOWN, extended, H)
- "skills多了应该怎么做？" (What to do when you have many skills). 33.8K plays, 1,405 likes. https://www.bilibili.com/video/BV1yTQrBnEoj
- Comments (50 and 38 likes) describe adding routing layers: progressive disclosure on top of progressive disclosure.
- "一句'你好'吃掉 31K 上下文？skill-context-doctor" (A single "hello" eats 31K context). 2026-09-22. https://www.bilibili.com/video/BV1JFhH6rE4M
- Comment: each never-called skill still costs about 200 tokens, and a ranking of unused skills is more useful than a total.
- Another asks whether this equals `/context all`.
- Comment on the DeepSeek-skills tutorial (30 likes, 38 replies, 2026-09-23): "I have added no skills myself." A related comment (6 likes, 37 replies, 2026-10-05) says session logs show a skill loaded but doing nothing and polluting context.
- Implied features:
  - Token-cost estimate per skill, always-on versus on-demand.
  - Never-used ranking from transcripts, which `usage` partly has.
  - A "load-without-use" metric.
- Docs 59 covers sprawl in general. The per-token ranking and user-quoted figures are new.

### 3. Skills silently misfire on non-Claude models (NEW, M)
- Linux.do test, via a 2026-07-24 repost (https://www.80aj.com/2026/07/24/grok-vs-deepseek-skills/): a WorkBuddy-generated skill pasted into Grok was followed, but DeepSeek and Qwen ignored it. The article offers no fix and only speculates on causes. Confidence L.
- "Skill触发不稳定，CLAUDE.md劝不听？Hooks了解一下" (Skill triggering is unreliable; hooks). 2026-05-03, 13.3K plays. https://www.bilibili.com/video/BV1qS9oB9EFT
- Comment (10 likes): DeepSeek V4 prefers English while thinking, and skills may work for a while then revert.
- CSDN, via search summary: a description that clearly matched the prompt did not trigger. The advice is to test explicit invocation first, then check description and path.
- Implied features:
  - A per-provider trigger test ("run this skill's prompt set against model X").
  - A diff of trigger rates across DeepSeek, Kimi, Qwen and GLM.
  - A "force explicit invocation" check.
  - A language-of-reasoning probe.
- Fits docs 59's honest-statistics work. The cross-model angle is new.

### 4. Chinese providers as BYOK, with cost sensitivity (NEW, H for demand, L for numbers)
- Bilibili tutorials on connecting DeepSeek, Kimi and GLM to coding agents:
  - "Kimi API Key接入指南：ZCode、DeepSeek Harness、Kimi Code" (Kimi API key guide). 2026-11-10, 2.6K plays. https://www.bilibili.com/video/BV1XRWb6hEKM
  - "VScode+Kimi cli接入deepseek模型". 2026-10-06.
- V2EX 2026-11-21, "Claude 被连封两个账号" (Claude banned two accounts in a row, what next?). 48 replies. https://www.v2ex.com/t/1258753
  - Asks which domestic model codes best.
  - Adjacent threads cover Claude account and verification troubles.
- Cursor pricing and quota threads: 29 replies on "cursor 给俺烧光了" (Cursor burned me out), 15 on a plan merge, 7 on third-party model quota removal. https://www.v2ex.com/t/1253516
- A Chinese-model tutorial hit "DeepSeek Harness 大肥鱼终极教程" with 1.19M plays, 54.7K likes and 95K favourites. https://www.bilibili.com/video/BV1L7xm64EHP
- Web summaries (CSDN, secondhand, unverified):
  - Setup is three variables: `ANTHROPIC_BASE_URL`, token and model name.
  - Endpoints exist for DeepSeek, Kimi, GLM and Bailian.
  - Users set cheap "flash" models for haiku and subagents.
  - Price figures like DeepSeek V4-Flash ¥1/M input are one blog's claim.
- Implied features:
  - Provider presets for the AI authoring feature: DeepSeek, Moonshot, Zhipu, Qwen.
  - Anthropic-compatible and OpenAI-compatible base URLs, with a model dropdown from `/v1/models`.
  - A cost estimate per AI action in CNY.
  - A cheap-model default for bulk operations such as translate and classify.
  - A warning that `[1m]`-suffixed model names are often unrecognised.
- Docs 59 has the BYOK foundation. China-specific endpoints, relays and CNY pricing are new.

### 5. Tutorials show repeatable workflows a tool could automate (NEW, H)
- Top Bilibili skill tutorials, by plays:
  - "从 LLM 到 Agent Skill" 2.28M plays, 111K likes, 194K favourites. https://www.bilibili.com/video/BV1E7wtzaEdq
  - The Andrew Ng course, Chinese-labelled. 562K plays. https://www.bilibili.com/video/BV1qv6eBZErD
  - A 2-hour "保姆级" course. 410K plays. https://www.bilibili.com/video/BV1ahFmzqE9z
  - Trae skills. 348K plays. https://www.bilibili.com/video/BV1ZTzpBWEhF
  - "8个Skills平台 + 3种安装方法" (8 skill platforms, 3 install methods). 271K plays. https://www.bilibili.com/video/BV1AU5L6dEDC
- Workflow comments:
  - Top Trae comment, 110 likes: after a satisfying multi-turn task, ask the AI to turn the session into a reusable skill.
  - Top "8 platforms" comment, 388 likes: skip manual install, hand the skill file to the agent.
  - GitHub as a private skill library: "GitHub秒变私有Skill库" (GitHub becomes a private skill library). 41.6K plays, 1,151 likes. https://www.bilibili.com/video/BV1A8F5zFEoU
  - Comment (18 likes): any useful GitHub project directly becomes a skill.
- Implied features:
  - "Distil this session into a skill" with transcript grounding. This matches the grounding finding in docs 59.
  - Install from a GitHub URL with a preview.
  - Install into several agents at once. The Trae, DSH, WorkBuddy and OpenClaw dirs matter here.

### 6. Domestic and cross-agent ecosystem fragmentation (NEW, M)
- Chinese users run many hosts: Trae, Qoder, WorkBuddy, DeepSeek Harness, OpenClaw "龙虾", Kimi Code, Qwen Code 1.0.
- Bilibili manager tools:
  - "DSH-skillhub", toggles skills and MCP, 451 likes. https://www.bilibili.com/video/BV137hk6SEyp
  - "SkillHub 开源跨平台AI Skills搜集管理" (open-source cross-platform skill manager). 1.1K plays. https://www.bilibili.com/video/BV1i6Y86AExb
  - "多Agent之间Skill的管理和调用（共享、备份、一键同步）" (share, back up, one-click sync across agents). 2026-04-26, 82 likes. https://www.bilibili.com/video/BV15koqBBECh
- A comment on the cross-agent sync video asks "workbuddy 可以吗" (does it work with WorkBuddy?).
- Enterprise question: "权限这块是按项目分还是按人分呀" (are permissions per project or per person?). Skills sit in one directory with no record of who changed what. https://www.bilibili.com/video/BV1VNsY6LEcc
- One comment links a "dsh-skills-manager" with download counts. It reads as promotion and was not used as evidence.
- Implied features:
  - Agent scope presets for Trae, Qoder, WorkBuddy, DSH, Kimi Code and Qwen Code.
  - Sync preview across scopes.
  - Change history with an author field for teams.

### 7. Marketplace trust (KNOWN threat, NEW local framing, M)
- Users share large catalogues: "skills市场！！！7w多个skills" (a 70K-skills market). 9.8K plays. A comment (41 likes) points to skillsmp.com. https://www.bilibili.com/video/BV1y3kMBKEX3
- "半年已经2,275,645个skills了" (2.27M skills in half a year), a 6-like comment on the Ng-course video.
- Tencent Matrix scanned 50,000 skills (2026-04-24): https://matrix.tencent.com/en/2026/04/24/we-scanned-50000-skills-the-threat-persists
- ClawHub poisoning reports (SlowMist, Snyk, CertiK): rankings can be gamed, and agents pick the most-downloaded skill. Secondhand via search summaries.
- Implied features:
  - Pre-install scan on import from any marketplace.
  - Warn on Base64 and two-stage install steps in SKILL.md.
  - Never auto-install by popularity.
- Docs 59 has scanning. The CJK false-positive point already appears there from Cisco.

### 8. Prior-art product: a skill health-check skill (KNOWN pattern, L)
- "朋友，你的 Skills 需要体检啦！" (Your skills need a checkup). 2026-04-19, 2.3K plays. https://www.bilibili.com/video/BV1B2oFBgE6r
- One comment says another optimiser made the skill heavier: a 40-minute run became two hours.
- Implied feature: optimisation must be measured and reversible.

### 9. Rules files and the CLAUDE.md, AGENTS.md and SKILL.md split (KNOWN, M)
- Many "how to write AGENTS.md" videos from 2026-08 to 2026-11, with 1K to 10K plays.
- "CLAUDE.md、AGENTS.md、SKILL.md：三份文件到底怎么用？" (How do the three files differ?). 130 plays. https://www.bilibili.com/video/BV18oW66fEWH
- "andrej-karpathy-skills" review. 2026-10-31, 714 plays. https://www.bilibili.com/video/BV1uLxr6eEkn
  - Top comment: a 65-line rule file shrinks code, but a Chinese-system file read dropped from 34/40 to 8/40 and recovered to 20/20 with a three-line Chinese clause.
  - Another comment says the encoding instruction was deleted as "redundant".
  - These figures come from one reviewer's test and were not independently checked.
- Implied features:
  - Lint "minimalism" rewrites for dropped locale, encoding and reply-language clauses.
  - A locale checklist: reply language, file encoding, sensitive fields.
  - A new-model audit for over-prescriptive rules, as in docs 59.

### 10. Prompt-library tools (minor, L)
- "AI提示词卡片管理工具丨PromptCard Pro" (a prompt-card manager). 229 plays. A "GitHub最全面的AI提示词库" video has 74K plays, 4.8K likes. https://www.bilibili.com/video/BV1ZrXNB5E2t
- Demand exists for prompt management, but it is a separate product line. Out of scope.

## Not found
- No concrete demand for Chinese-language SKILL.md authoring (Chinese descriptions improving routing). One CSDN summary says the description alone drives triggering.
- No Chinese demand evidence for team-share review workflows beyond the enterprise comment above.
- Zhihu and Xiaohongshu are the highest-signal Chinese sources and both were blocked. Absence there is not evidence of absence.

## Feature ideas implied, shortlist
1. Local note and translation sidecar per skill, shown in lists, never altering SKILL.md. Source: BV1845F6REUu and BV1VRHT6NERF.
2. Provider presets and CNY cost previews for DeepSeek, Moonshot, Zhipu and Qwen, with a cheap-model default for bulk actions.
3. Per-model trigger test, to catch skills that work on one model and are ignored on another.
4. Token cost and never-used ranking per skill.
5. Agent scope presets for Trae, Qoder, WorkBuddy, DSH, Kimi Code and Qwen Code.
6. "Session to skill" grounded in a real transcript.
7. Marketplace import scan, with a warning on encoded install steps.
8. Locale clause checker for rules files.

Caveat: view counts and likes come from search listings on 2026-11-22. Comments are the top few by likes only, so they skew toward popular opinions.
