# Microsoft APM and v2 Interface Decisions

**Version 1.0.0**

**AI manifest**: Records the 2026-11-20 decisions about Microsoft APM support
and the typography and palette proposals from the v2 design study.

## Microsoft APM

**[SPEC]** Microsoft APM owns manifest validation, dependency resolution and
package import and export. Skills Manager reports the presence of regular
`apm.yml` and `apm.lock.yaml` files in the selected project. Quality links to
APM's audit reference when either file produces a signal. The presence check
uses file metadata and works offline. The link has a fixed destination
and omits the referrer.

**[NOTE]** The formats cover different evidence. The YAML 1.2 manifest
declares intent, including APM, MCP and LSP dependencies, scripts, target
selection and extensions. The lock records resolution, hashes and deployment
ownership. Schema selection, aliases and extension preservation affect how
an APM client interprets the pair. A parser for a small subset would accept
some documents with invalid meaning and reject some valid ones. The existing
frontmatter parser is scoped to skill documents. [Manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/),
[OpenAPM specification](https://microsoft.github.io/apm/specs/openapm-v01/),
[lockfile specification](https://microsoft.github.io/apm/reference/lockfile-spec/).

| Scenario | Decision |
|---|---|
| Missing, inaccessible, linked or malformed project files | Preserve the existing containment and regular-file checks. Presence reports file metadata only. |
| Validate a manifest or compare it with a lock | Use the official APM audit from the project root. Audit includes a manifest parse check and can report lockfile, policy and deployment findings. Its flags determine whether policy discovery and drift replay run. |
| Preview dependency resolution | Use APM's own install preview when needed. Local metadata may be incomplete, and a successful preview does not establish that deployment will succeed. |
| Install or import dependencies | APM resolves and deploys packages, with effects that can include configuring MCP and writing other agent primitives. Skills Manager's existing import consumes skill folders and its own archives. |
| Export a project or a lock | Keep the APM manifest and generated lock with the project. APM's pack command owns bundle layout; mapping a local skill inventory to that format would lose dependencies, target and ownership information. |

Sources for the command behavior are the official [audit reference](https://microsoft.github.io/apm/reference/cli/audit/),
[baseline checks](https://microsoft.github.io/apm/reference/baseline-checks/),
[install reference](https://microsoft.github.io/apm/reference/cli/install/),
[lock reference](https://microsoft.github.io/apm/reference/cli/lock/) and
[bundle guide](https://microsoft.github.io/apm/producer/pack-a-bundle/).

The checksum-verified [APM 0.36.1 release](https://github.com/microsoft/apm/releases/tag/v0.36.1)
also ran against five disposable project directories using
`apm audit --ci --no-policy --no-drift --format json`. The valid manifest
passed. Missing manifest, malformed YAML, duplicate key and missing required
lock failed with the expected checks. Files and directories in those projects
were unchanged after the audit.

## v2 type size

**[SPEC]** Keep the existing scale and the Large text multiplier. Use the
current 13 px role for dense metadata and table rows. Keep the current sizes
and weights of standard controls, navigation and longer reading text.

**[NOTE]** A temporary stylesheet set the Skills page's navigation, filter
controls, view controls and header buttons to 13 px at weight 500. Chromium
measured the same toolbar heights and wrapping at 320, 390, 768, 900, 1024,
1280 and 1440 CSS px. At 1280–1440 px, the sum of the six top navigation
link widths fell from 495 to 454 px. At 768 px it fell from 403 to 382 px.
The main filter toolbar remained 42 px at 1280–1440, 96 px at 768–1024 and
238 px at 320–390. The trial measured layout with one disposable inventory
and standard text size. Participant legibility remains a human review item.

## v2 ink and borders

**[SPEC]** Keep solid foreground and control-boundary tokens. Reader section
headings and navigation group labels use the existing `--muted` token.
The Sync map search border uses `--line-strong`.

**[NOTE]** Compositing the proposed `rgb(27 29 34 / alpha)` over current
light-theme surfaces gave the following ratios. Normal text requires 4.5:1
and a necessary control boundary requires 3:1.
[Text contrast criterion](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[control contrast criterion](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).

| Background | .90 text | .62 text | .45 text | .27 text | .08 border |
|---|---:|---:|---:|---:|---:|
| White `#ffffff` | 12.53 | 4.75 | 2.84 | 1.78 | 1.17 |
| Page `#f7f5f0` | 11.67 | 4.61 | 2.79 | 1.77 | 1.17 |
| Sunken `#f1eee8` | 11.09 | 4.50 | 2.76 | 1.76 | 1.17 |
| Selected `#e3ded4` | 9.80 | 4.26 | 2.67 | 1.73 | 1.16 |

Using the same opacity levels with the existing light ink `#f4efe5` on dark
surfaces still leaves .45 opacity at 3.76–4.05:1. The .08 border reaches
1.23–1.26:1.

The actual reader group labels improve from 4.03:1 to 5.01:1 on the light
tree background. Section headings improve from 4.51:1 to 5.61:1 on the light
reader surface. The v2 contract checks both surfaces in both themes. Human
visual and spoken screen-reader sign-offs are tracked in @task.md.
