# GOAT HTTP routing experiment — 2026-11-17

The product's HTTP trigger simulator, using `deepseek/deepseek-v4.1-flash`
through Command Code GOAT, matched all 36 authored labels (12 synthetic prompts,
three listing permutations). This is simulation evidence; there is no native
fidelity rate. Method, accounting fix and limits:
@docs/48-ai-http-study-2026-11-17.md.

- `deepseek-fixture.json`: four trusted skill descriptions and bodies, model,
  seed and repetition settings.
- `deepseek-prompts.json`: eight positive cases and four near misses.
- `deepseek-estimate.json`: no-send estimate including reasoning allowance.
- `deepseek-simulation.json`: actual saved-prompt product result and usage.
- `reasoning-canaries.json`, `deepseek-before-fix.json`: response metadata only,
  showing thinking tokens consume the output allowance. No reasoning text.
- `prior-haiku-simulation.json`, `prior-native-round-*.json`: earlier attempts
  before the model restriction; native results are entirely inconclusive.
- `summary.json`: metric, token usage and limitations.
- `sha256.json`: SHA-256 of each other JSON artifact.

No key, account identifier, raw transcript or provider reasoning is included.
Hash integrity and prompt/listing joins can be checked offline. An attended
reproduction must use the permitted model and the product's normal
`ai_skills.trigger_test`/`AiRun` path with temporary HOME/data, env-only auth,
the preserved skills/prompts, three repeats and seed 20261117. It must start
with `estimate: true` and enforce the recorded 50,000-run / 80,000-day token
caps. The current native Claude harness has no same-model GOAT route for
DeepSeek or Muse Ember; do not count simulation choices as native invocations.
