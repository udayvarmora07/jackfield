# Command Code GOAT Provider API — 2026-11-17

**Version 0.1.0**

**AI manifest**: Dated primary-source notes for using Command Code GOAT through its Provider API. Covers endpoints, model selection, authentication, credit and rolling-window limits, and documented usage reporting. This is not a live account or credential check.

**[SPEC]** Findings below were checked against Command Code’s first-party documentation, official provider integration, and the public model catalog on 2026-11-17. Plan allowances, model availability, and model IDs may change; fetch the model catalog when running a study.

## API contract

**[SPEC]** GOAT and higher paid plans can use the Provider API. Command Code documents OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages compatibility. GOAT requests consume the plan’s own credits and per-model access. The separate Provider plan is the pay-as-you-go plan built for API traffic; those are distinct billing arrangements. The $1 Go plan has no Provider API access. See the [Provider API reference](https://commandcode.ai/docs/provider) and [GOAT plan](https://commandcode.ai/docs/plans/goat).

| Use | URL or path | Notes |
|---|---|---|
| OpenAI-compatible base | `https://api.commandcode.ai/provider/v1` | Use `/chat/completions` or `/responses` as supported by the selected model. |
| Anthropic-compatible SDK base | `https://api.commandcode.ai/provider` | The official Command Code Pi integration uses this root because the Anthropic SDK appends `/v1/messages`. |
| Anthropic Messages route | `https://api.commandcode.ai/provider/v1/messages` | Claude models use this route only. |
| Models catalog | `https://api.commandcode.ai/provider/v1/models` | Each model includes its exact `id` and `supported_endpoints`; select a route from this field. |

Sources: [Provider API routes and schemas](https://commandcode.ai/docs/provider), [official Command Code Pi provider](https://github.com/CommandCodeAI/pi-commandcode-provider).

**[SPEC]** Use the model’s exact API `id`, not a marketing label or a model ID guessed from another vendor. The Provider API documentation’s request example uses `claude-sonnet-4-6`. The first-party model registry lists `claude-haiku-5-5` as the CLI ID and the model profile gives its provider label as `anthropic/claude-haiku-5-5`; the current authenticated API catalog should supply the exact request ID and `supported_endpoints` for a run. Claude Haiku 5.5 and Sonnet 5.5 model pages both state that they are available on GOAT and above; the GOAT plan page assigns Haiku 5.5 $20 and Sonnet 5.5 $10 in monthly model credits. See [Available Models](https://commandcode.ai/docs/reference/cli/models), [Haiku 5.5 model page](https://commandcode.ai/models/claude-haiku-5-5), [Sonnet 5.5 model page](https://commandcode.ai/models/claude-sonnet-5-5), [GOAT model allowances](https://commandcode.ai/docs/plans/goat), and [Provider API model routing](https://commandcode.ai/docs/provider).

**[SPEC]** Authentication uses the same Studio API key as the Command Code CLI. Send `Authorization: Bearer <API_KEY>` on API routes. The provider docs also accept `x-api-key: <API_KEY>` on Anthropic `/messages` requests. No credential was read, copied, or stored during this research.

## Credits and limits

**[SPEC]** The GOAT plan is $10/month and advertises up to $100 of model usage credits per monthly cycle. The phrase “up to” matters: each model has a separate allowance, and the value represented by a credit varies with the model’s usage multiplier. At the time checked, GOAT’s page listed Claude Sonnet 5.5 with $10 and Claude Haiku 5.5 with $20 in monthly model credits; their official model pages state GOAT is an eligible plan. These are model-specific usage allowances, not an additional subscription charge. The Haiku page lists standard-band rates of $0.10/M input, $0.50/M output, and $0.01/M cache read, with higher rates above 100K context. The user's noted DeepSeek V4.1 Flash model is listed as available on Go and above; its page lists off-peak rates of $0.15/M input, $0.60/M output, and $0.003/M cache read, with weekday peak prices of $0.30/M, $1.20/M, and $0.006/M respectively. These are published model pricing references, not a prediction of request cost or cash billing; actual cost depends on tokens, context band, time, caching, and plan-credit rules.

**[SPEC]** Included GOAT credits are paced by rolling windows. The current [Usage Limits page](https://commandcode.ai/docs/resources/usage-limits) states a 5-hour cap of up to $20 of model usage and a 7-day cap of up to $50 of model usage, drawn from the monthly credits. It separately describes these as 14 and 35 GOAT credits across models; a credit’s model-usage value depends on the model. Each window starts with the first request and resets 5 hours or 7 days later. Extra pay-as-you-go credits are outside those plan windows and are not blocked by them. The exact number of requests or cash spend allowed in a window therefore cannot be inferred from the headline dollar equivalents.

**[NOTE]** A 429 response can indicate upstream rate limiting. The reviewed docs do not provide a fixed request-per-minute quota for GOAT; its published subscription constraints are the model-credit and rolling-window limits above. Upstream rate limits remain an operational possibility.

Sources: [GOAT plan and per-model allowances](https://commandcode.ai/docs/plans/goat), [rolling usage limits](https://commandcode.ai/docs/resources/usage-limits), [Provider API errors and plan access](https://commandcode.ai/docs/provider).

## Usage reporting

**[SPEC]** The Provider API documentation says streaming responses include per-request token usage at the end of each stream: final `usage` chunk for Chat Completions, usage on `response.completed` for Responses, and usage in Anthropic’s `message_delta`. No opt-in is required. This reports tokens in the response stream; the documentation does not describe it as a cost ledger.

**[SPEC]** Command Code Studio’s Usage page reports cost and token totals for each request and provides request details. The CLI `/usage` command reports live progress against the 5-hour and weekly windows and the reset times. In the official API reference and linked usage pages reviewed for this note, no supported Provider API endpoint for usage history, credit balances, or window reporting is documented. Treat that as “not documented in reviewed sources,” not proof that no private or future endpoint exists.

Sources: [Provider API streaming usage](https://commandcode.ai/docs/provider), [Studio Usage page](https://commandcode.ai/docs/studio), [Usage Limits and `/usage`](https://commandcode.ai/docs/resources/usage-limits).

## Practical implication for a fidelity study

**[SPEC]** General API setup remains as described above, but the authorized live study has since been narrowed to `deepseek/deepseek-v4.1-flash` and `meta/muse-ember`. The user explicitly restricts all further test model calls to those two IDs. The authenticated catalog observed by the coordinating agent listed `/chat/completions` and `/responses` for both and did not list `/messages`; use the OpenAI-compatible root `https://api.commandcode.ai/provider/v1` with only a catalog-supported path. These live catalog details are coordinator-reported; this research agent made no authenticated request and no model call.

**[SPEC]** The existing native Claude CLI harness cannot provide a same-model comparison for these GOAT runs through Anthropic Messages: neither authorized model exposes `/messages` in the observed catalog. Any comparison to previously collected native Claude observations is cross-model and must be labeled as such. No additional Claude or Haiku model request is authorized for this study. The Anthropic endpoint instructions above remain reference documentation only, not a recommendation to call Claude.

**[SPEC]** Official Command Code headless documentation names `COMMAND_CODE_API_KEY` as the CLI environment variable for noninteractive authentication; it takes precedence over `~/.commandcode/auth.json`. The CLI settings reference says `HOME`/`USERPROFILE` is used to resolve `~/.commandcode`, so a temporary home can isolate user-level CLI configuration and stored auth files. That does not isolate project configuration: project `.commandcode/settings.json` and `.commandcode/settings.local.json` have higher precedence, and project skill discovery also remains active. The docs do not list `CMD_API_KEY` as a `cmd` CLI auth variable; its occurrence in Command Code’s first-party Pi provider extension is specific to that integration and is not evidence for the CLI.

**[NOTE]** `cmd -p ... --output-format json` emits NDJSON event frames, including `tool_running` with `toolCallId` and `toolName`, followed by a result frame. This can evidence that a named tool was called when such an event appears. The Skills docs describe skill activation as loading the skill’s `SKILL.md` into context, but do not document an AgentEvent that proves this activation or instruction loading. JSON tool events alone therefore do not reliably prove a skill was invoked or followed.

Sources: [Headless authentication and JSON output](https://commandcode.ai/docs/headless), [Settings environment variables and precedence](https://commandcode.ai/docs/settings), [Agent Skills activation and invocation](https://commandcode.ai/docs/skills), [official Pi provider extension](https://github.com/CommandCodeAI/pi-commandcode-provider).

## Claude CLI gateway compatibility observation

**[NOTE]** The coordinating agent reports a direct test of Claude Code CLI 2.1.325 against GOAT Anthropic Messages using `claude-haiku-5-5` failed with HTTP 400: `Invalid discriminator value. Expected user | assistant at messages.1.role`. The same agent reports six direct Anthropic API calls for that model through GOAT succeeded. Those are coordinator-reported runtime observations; this research agent did not make requests. The currently authorized DeepSeek/Muse study must not make additional Claude or Haiku requests.

**[NOTE]** Anthropic’s current Claude Code environment-variable documentation supports `ANTHROPIC_BASE_URL` for a proxy or gateway. Anthropic’s public CLI issue tracker contains user-reported failures where system-role messages were rejected by Anthropic-compatible gateways; one report identifies a regression after a version update and one issue includes a request showing `system` among the message roles. These reports show that third-party gateways can encounter role-schema incompatibilities, but do not establish that this GOAT error has the same cause. The reviewed 2.1.325 changelog does not document a fix or compatibility change for this exact failure. No official Claude CLI documentation or issue confirmed a GOAT-specific setting that resolves the observed error.

Sources: [Claude Code environment variables](https://code.claude.com/docs/en/env-vars), [Claude Code 2.1.325 changelog](https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md), [Anthropic issue #63366](https://github.com/anthropics/claude-code/issues/63366), [Anthropic issue #63457](https://github.com/anthropics/claude-code/issues/63457).

**[?]** The current authenticated catalog, GOAT account entitlements, and request success for DeepSeek V4.1 Flash or Muse Ember are outside this document agent’s verification; current catalog details above are explicitly reported by the coordinating agent. The exact serialization cause of the Claude Code 2.1.325 error is also unconfirmed by the reviewed primary sources.
