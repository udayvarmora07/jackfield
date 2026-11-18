# GOAT HTTP Routing Study — 2026-11-17

**Version 0.2.0**

**AI manifest**: Dated synthetic experiment using the product's actual provider
HTTP transport, with a reproduced reasoning-budget defect and its correction.
The 36/36 result is agreement with authored labels, not native-agent fidelity.
Inputs, results, metadata and hashes are retained in
@tools/ai_fidelity/evidence/2026-11-17/. Vendor setup and constraints:
@docs/47-commandcode-goat-api-2026-11-17.md.

## Method and result

**[SPEC]** The maintainer authorized the Command Code GOAT key from their CLI
configuration, then limited subsequent live model testing to DeepSeek V4.1
Flash or Muse Ember. The final run used `deepseek/deepseek-v4.1-flash` via the
OpenAI-compatible endpoint, configured with the existing `openai` provider and
base `https://api.commandcode.ai/provider/v1`. The key stayed in the study's
process environment; no new settings file or evidence artifact contains it.
Personal skill data was not used.

A private temporary HOME/data fixture contained four handwritten, non-executable
skills: haiku, rhyming couplet, measurement conversion and ISO date formatting.
Eight positive prompts and four near misses were saved through
`ai_skills.save_prompt_set`. The actual `ai_skills.trigger_test` path scanned
that library, captured its listing, ran its normal no-send preflight and sent
the routing requests through `AiRun`. There was no CLI simulator adapter and
no fake provider in this run. Three passes used seed 20261117 and successive
listing permutations; two batches per pass made six HTTP requests.

| Observed quantity | Result |
|---|---|
| Prompts / passes / observations | 12 / 3 / 36 |
| Matches to authored labels | 36 / 36 |
| Missing / invalid answers | 0 / 0 |
| Provider-reported input / output tokens | 3,087 / 1,815 |
| Cache-read tokens (included in input total) | 256 |
| Planned allowance including reasoning | 28,863 tokens |
| Configured run / day caps | 50,000 / 80,000 tokens |
| Native fidelity rate | Unavailable |

**[NOTE]** These token counts cover the final successful DeepSeek experiment.
They exclude earlier canaries and failed attempts. Actual plan-credit charges
were not independently checked in Command Code Studio. The product's existing
day admission policy counts completed input usage plus in-flight reservations;
the reservation now includes the full output allowance, including thinking.
No claim about a cash bill or total study cost follows from these counts.

## Defect reproduced and corrected

**[SPEC]** Before the correction, the first 10-prompt DeepSeek batch allowed
510 completion tokens. Captured response metadata showed `finish_reason:
length`, zero answer text and all 510 completion tokens attributed to
reasoning. A tiny Muse Ember canary likewise reported 174 reasoning tokens
within 188 completion tokens for an 11-character JSON answer. The retained
metadata contains lengths and counts, not reasoning text.

`skillsmgr.ai` now gives these two exact model IDs, when configured through
the `openai` provider, an additional 4,096-token allowance. No undocumented
effort setting is sent for them. One shared calculation supplies both the
wire limit and preflight/run/day-reservation estimates, also correcting the
existing GPT/Claude headroom admission gap. Thinking-only failures now record
the provider's usage before raising the clear error and releasing the
reservation, so that failure path does not erase recorded input usage.
Unknown model/provider combinations keep their prior request behavior.

Regressions cover the wire allowance, no-send estimate, refusal before a
request when caps are too small, usage retained on thinking-only failure,
subsequent day-cap admission and reservation cleanup. The current-tree
verification receipt is in @docs/06-progress-log.md.

## Native comparison and limits

**[NOTE]** Before the maintainer's model restriction, an initial Haiku HTTP
simulation completed with the same synthetic corpus. Its native Claude CLI
comparison produced 24 inconclusive cases and no agreement denominator.
A separate canary with each CLI version, 2.1.325 and 2.1.319, observed GOAT's
message-role schema rejection. The first direct HTTP attempt also used an
extra `/v1` and returned 404; its base URL was corrected before successful
simulation. These are setup/compatibility outcomes, not routing results.

After the model restriction, neither permitted model advertises Anthropic
Messages in the observed GOAT catalog. The existing native Claude harness
therefore cannot produce a same-model comparison through that service.
Command Code's documented JSON tool events do not themselves prove skill
activation. No further Claude/Haiku model request was made, and no model's
prose was used as native-invocation evidence.

The sample is small, authored and synthetic. It does not measure ordinary
interactive sessions, real libraries, other models, larger distractor sets,
body compliance or participant outcomes. Native listing/configuration equality
was not established. The broader fidelity task remains open for a supported,
observable native comparison; the product HTTP simulation portion is complete.

## 2026-11-18 — OpenCode observation feasibility

**[NOTE]** OpenCode 2.3.2 emitted a completed `tool_use` record with
`part.tool=skill` and `part.state.input.id=unit-fixture` when a fake
Chat Completions provider deliberately requested a synthetic skill. The next
request to the stub contained the skill's synthetic instruction marker.
There were three stub requests in total, including an initial request without
tools or a skill listing. The probe used `--standalone --format json`, a
private project and home, and a Linux network namespace with only loopback.
The script and sanitized summary are in
`/tmp/skillsmgr-remaining-20261118/opencode-probe.py` and
`/tmp/skillsmgr-remaining-20261118/opencode.vq650vre/summary.json`.

**[SPEC]** The tagged source shows that `run --format json` emits terminal
tool status for ordinary tool calls. The separate `session.skill.activated`
event belongs to explicit session activation and carries the skill body.
The model-facing listing filters denied, undescribed and manual-only skills.
The generic skill-list API provides registered skills. A future attended
comparison must capture the listing actually sent to the model, count and
bound all provider requests, and keep full bodies and raw streams out of its
retained evidence.
[Run event mapping](https://github.com/anomalyco/opencode/blob/v2.3.2/packages/cli/src/run/noninteractive.ts#L479-L594)
[Skill execution](https://github.com/anomalyco/opencode/blob/v2.3.2/packages/core/src/tool/plugin/skill.ts#L31-L64)
[Session activation](https://github.com/anomalyco/opencode/blob/v2.3.2/packages/core/src/session/session.ts#L233-L254)
[Model-facing listing](https://github.com/anomalyco/opencode/blob/v2.3.2/packages/core/src/skill/instructions.ts#L48-L72)

**[?]** GOAT interoperability and native routing agreement remain unmeasured.
The stub chose the tool call. An attended OpenCode study would measure
OpenCode's routing for the permitted model and listing, with Claude Code and
Command Code fidelity still unknown.
