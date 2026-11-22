# Instagram and Quora pass through the user's browser

**Version 0.1.0**

**AI manifest**: Raw research report (round 4) for @docs/60-ai-features-research-loop-2026-11-22.md. Evidence, not decisions.

Date: 2026-11-22. Read only. Nothing liked, commented, followed, saved, upvoted, answered, shared or typed. Page text treated as data. No handles of private individuals recorded. No CAPTCHA or block page appeared.

## Method and coverage

| Platform | Step | Result |
|---|---|---|
| Instagram | `opencli browser open/extract` on `explore/search/keyword/?q=...` through the user's Chrome | Worked, unlike rounds 2 and 3 (HTTP 404). But each keyword page returned only 3 post links; scrolling 4 times did not load more. |
| Instagram | 22 keyword queries (the 7 requested plus claude code, claude code tips, claude skill, skills.md, claude code workflow, cursor ai, ai agents, agents.md, vibe coding, claude code plugins, custom instructions, mcp claude, prompt engineering claude, codex openai, claude code for non coders) | "claude.md" returned zero posts. Others 3 each, with overlap, giving 46 unique post URLs. |
| Instagram | Opened and extracted all 46 post pages | Captions read for about 42. Several had empty or hashtag-only captions. Comments are mostly emoji or "send me the link" bait. A few useful comments. |
| Quora | `search?q=...&type=question`, 12 queries | Worked while signed in. Result lists are noisy (slide rules, martial arts, "cursor" CSS). Many relevant questions are unanswered. |
| Quora | Opened 18 question pages | Only 3 had substantive on-topic answers. Others were unanswered, with unrelated "related answers" and ads. |

Gaps: the target of 15 or more Quora questions was met for pages opened (18) but not for answered, relevant ones (about 4). Engagement numbers on Instagram are concatenated strings (likes, comments, shares) that I could not split reliably, so any figure below is [?]. Post ages are relative ("34w") and approximate. Instagram evidence is almost entirely creator marketing with comment-for-DM funnels; it shows what is popular, not what users struggle with.

## Findings by goal

### G1: remove a skill or section and check whether results get worse

- No post or answer describes ablation or "does removing this make output worse". Direct evidence: none.
- Weak adjacent signal, developers: a Quora answerer (https://www.quora.com/What-is-the-biggest-problem-with-using-Claude-skills, 160 views) advises counting which skills fired last month and uninstalling the rest, and says narrow packs cost less than wide ones (a 14-skill pack about 546 tokens, a 42-playbook pack about 6,700). This is a manual version of "which skills are worth keeping", with no tool to measure it.
- Instagram creators rank skills by installs rather than by effect (https://www.instagram.com/p/Dd4Ama8mnza/), and one says "don't install all 30, pick one row" (https://www.instagram.com/p/DfBQ1AgOC1S/). Selection is by popularity, not evidence. Supports the need for a measured keep or remove signal [inference].

### G2: contradictions between instruction files and skills

- Cursor rules tutorial reel (https://www.instagram.com/p/DeG9pQKhrh7/, 42 [?]): a commenter asks which rule wins when a glob-scoped rule and an always-on rule conflict on the same file. The creator did not answer in the visible thread. Developers, direct but a single comment.
- Quora, unanswered: "How do I stop Cursor AI from hallucinating or ignoring custom rules?" (https://www.quora.com/unanswered/How-do-I-stop-Cursor-AI-from-hallucinating-or-ignoring-custom-rules). Shows the question exists; no answer and no contradiction diagnosis.
- Quora, unanswered: best directory structure for Cursor rules; how a CLAUDE.md should look; an AGENTS.md interpreter setting not being honoured by the Claude Code extension in Cursor. Developers; point to multiple instruction files with unclear precedence.
- A creator cheatsheet post (https://www.instagram.com/p/DWS197EjtKr/) says CLAUDE.md rules are about 70% followed while hooks are 100% [unverified claim]. Implies rules silently not applying.

### G3: skills that never trigger, or descriptions that get cut

- Same cheatsheet post advises "write skill descriptions that actually trigger" and "adding skills that trigger correctly". A commenter says treating skills as scoped knowledge packs keeps Claude consistent. Developers; confirms trigger quality is a known worry, with no method offered.
- Quora (same biggest-problem answer): every installed skill's name and description is loaded at session start; the answerer measured 162 skills at about 78,000 characters, roughly 19,500 tokens before the first prompt. Cost of descriptions is concrete here. Single answerer, self-reported [?]. No mention of truncation of long descriptions.
- Cursor rules reel comment: rules only help if they load before the edit. Weak signal on load timing.

### New ideas and pain points

- Install overload and trust: a creator warns to read what a plugin is allowed to do before installing (https://www.instagram.com/p/DfBQ1AgOC1S/); another says "read a skill's files before you install it" (https://www.instagram.com/p/DfrvfEtHP8j/). The Quora answer cites an audit finding about 37 percent of roughly 4,000 marketplace skills with a security flaw [? secondary claim, not checked].
- "Find skills" and "skill creator" are promoted as the beginner entry (https://www.instagram.com/p/DaN0yYtPzjY/, https://www.instagram.com/p/DfrvfEtHP8j/): people want a skill made in their own voice from three example posts.
- Self-correction memory: a skill that keeps a notebook of the model's own mistakes (https://www.instagram.com/p/Df3zpIzyFVA/).
- Code-size and discipline rules distributed as one CLAUDE.md (a Karpathy-based file, https://www.instagram.com/p/DewhNn1AZGQ/, claimed 220K stars [?]); a skills pack from Addy Osmani with 25 skills (https://www.instagram.com/p/Ddl772hDREy/, 37522 likes [?]). Popular instruction packs are shared as files, so imports will arrive with unknown conflicts.
- Custom-instruction snippets for ChatGPT go very viral (https://www.instagram.com/p/DT-jNe7j7i8/, large counts [?], https://www.instagram.com/p/DQANUyuksOP/). Non-developers paste a "human tone" prompt into settings and wonder if it works; no way to test it.
- Rule-pack carousels for Cursor (https://www.instagram.com/p/DclpZe9ikxo/) and prompt carousels for Claude Code (https://www.instagram.com/p/DbaV_gtEXuj/): the format is "comment a word, get a DM", meaning people collect files without a way to organise them.
- Skill token cost framed as "rent": a feature request to evict used skills from context reportedly closed as not planned (Quora answer, single source [?]).

## Findings by audience

Developers
- Cost of descriptions in context (Quora, measured), trigger anxiety (cheatsheet), precedence between rules (reel comment, Quora unanswered), memory of past mistakes, security of third-party skills.

Non-developers and creators
- Claude Code for non-coders and business use (https://www.instagram.com/p/DU33oyLDnAN/, 783 likes [?]); a commenter says the real value is analysts and ops people. A product manager using Cursor (https://www.instagram.com/p/DVNMrvlkwpo/). A beginner list of five skills because beginners "won't know which to install" (https://www.instagram.com/p/Df3zpIzyFVA/).
- Beginners learn Git as a safety net (https://www.instagram.com/p/DfVpRJEmVAI/, 40.2K [?]); commenters recommend committing before every agent change. Suggests a want for undo or restore around skill edits.
- Marketing creators want skills that remove AI tells from copy (https://www.instagram.com/p/DfrvfEtHP8j/).

## Ten strongest new signals

1. Description cost is a felt problem: a measured 162 skills and about 19,500 tokens at session start (Quora biggest-problem answer). Supports G3 and a "cost per skill" view.
2. Advice to "count what you fired last month and uninstall the rest" is done by hand today. Supports G1 with usage data.
3. Which rule wins when scoped and always-on rules conflict is asked and unanswered (Instagram DeG9pQKhrh7). Supports G2.
4. "Ignoring custom rules" is an open Quora question with no answer (Cursor). Supports G2 and G3.
5. "Write skill descriptions that actually trigger" is repeated advice with no way to check (DWS197EjtKr). Supports G3.
6. Claim that CLAUDE.md rules are about 70% followed (same post): users want to see whether a rule was followed [unverified].
7. Beginners do not know which skills to install; lists rank by installs, not effect (Df3zpIzyFVA, Dd4Ama8mnza).
8. Third-party skills are warned about for security; users are told to read files first (DfBQ1AgOC1S, DfrvfEtHP8j, Quora).
9. Viral instruction snippets for ChatGPT custom instructions show a very large non-developer audience that cannot test them (DT-jNe7j7i8).
10. Commit-before-agent-change habit among vibe coders (DfVpRJEmVAI) points to a want for easy restore around AI edits.

## Caveats

- Instagram yield is promotional; comments are mostly bait. Treat all as popularity, not pain.
- No evidence found for G1 ablation as a stated want. G2 and G3 have thin, mostly indirect support.
- All numbers marked [?] were not independently checked.
