---
name: context-sweep
description: Use when asked to audit repository instructions, plans, task statuses, or TODOs for stale guidance and conflicting product intent.
---

# Context sweep

Run an evidence-only review and return findings before any authorized edits.

1. Start with the requested area. With no area specified, review `AGENTS.md`,
   the live part of `task.md`, the latest progress receipt and the current
   section of the nearest owning doc. Use targeted searches through tracked
   project files. Read an archived document only to answer a named historical
   question. Keep reads within the checkout, excluding user settings,
   installed skills and session memory.
2. For each candidate, record its location, claim and status. Check the
   current entry point, implementation and relevant test or direct
   observation. Use local Git history or an explicit decision to establish
   whether the claim was superseded, resolved or kept intentionally.
3. Mark a **stale fact** only when current evidence disproves a factual claim
   and history or the owning contract establishes which behavior applies.
   Mark an **intent conflict** when active requirements disagree or intent
   is unclear. Record **insufficient evidence** when source, tests or history
   are missing. An unfinished implementation may match its task status.
4. Have an independent read-only reviewer check the candidate claims when
   available. Give the reviewer the exact claim and scope without your
   verdict or suggested fix. Ask for supporting and contrary evidence,
   including relevant history. Otherwise make a separate evidence pass and
   label the result self-checked.
5. Return a short report with location, claim, disposition, current evidence,
   history or decision, and a proposed action. Include coverage limits and
   any unresolved conflict. Apply any already-authorized corrections after
   the review. Follow the repo's approval rules for archive moves and
   preserve retained history and its links.
