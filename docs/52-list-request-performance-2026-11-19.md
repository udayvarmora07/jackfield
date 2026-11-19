# List Request Performance — 2026-11-19

**Version 0.1.0**

**AI manifest**: Profile and behavior-preserving speed-ups for
`GET /api/skills?scope=all&body=0`, the request v2 Home waits on before first
paint. Records what was measured, what changed, what was rejected and why, and
how equivalence is pinned. Builds on the Doctor/hygiene scan work in
@docs/50-rust-size-and-performance-assessment-2026-11-17.md. Raw numbers:
@benchmarks/list-request-2026-11-19.json. Method and tool:
@benchmarks/list_perf.py. Delivery receipt: @docs/06-progress-log.md.

## Outcome

**[SPEC]** The response contract is unchanged: same fields, same values, same
order, same `X-Total-Count`, same headers. On the same synthetic fixtures the
parsed JSON is identical before and after at 1,000 and 10,000 records. Paired
medians of the full HTTP request (before → after):

| Fixture | Before, ms | After, ms | Median reduction |
|---|---:|---:|---:|
| 1,000 records, root 6 path components deep | 212.3 | 128.4 | 39.5% |
| 1,000 records, root 10 components deep | 270.4 | 138.0 | 49.0% |
| 10,000 records, root 10 components deep | 3,947.8 | 2,790.3 | 29.3% |

**[NOTE]** Seven paired rounds of nine requests at 1,000 records, three
rounds of three at 10,000; each cell is the median of round medians, variants
alternating order. The scratchpad root is deeper than a real `~/.claude/skills`
(about 5–6 components), and the saving scales with depth, so the 6-component
row is the honest estimate for a normal home and the 10-component rows are the
upper end. The user's 2,085-record library was not read or copied; its 0.6 s is
the reporter's number and this fixture is not a prediction of it. The host was
shared (load average 3–8), warm-cache and loopback-only. No p95 is claimed.

## Where the time was

**[NOTE]** `cProfile` of the handler's work at 1,000 records (inflated by the
profiler, so read shares, not seconds): 0.66 s total. `scan_dir` was 0.45 s
of it; `path_safety.contained_entry_under` alone 0.20 s (30%), almost all
`os.path.realpath` walking every component of an absolute path with one `lstat`
each; `scopes._physical_path` another 0.07 s doing the same walk again for the
same row; `Store`'s per-row global path re-resolved its root 125 times. JSON
encoding was 0.016 s (about 2%). The per-document parse, hash and cache work
that docs/24 §D1 already optimised was not the bottleneck any more.

## What changed

**[SPEC]** Each change returns the same answer by a cheaper route and defers to
the old route whenever it cannot be certain.

| Change | Why it is the same answer |
|---|---|
| `path_safety._lexical_below` used by `contained_entry_under` / `contained_path_under` | Below an already-resolved root, a path with no symlink resolves to itself, so one `lstat` per component replaces `realpath`'s walk of the whole path. Any link, missing or unreadable component, `.`/`..`/empty/multi-component part or non-POSIX host returns `None` and the original `realpath` + containment check runs. |
| `scopes._memoized_realpath` behind `_physical_path` | The rows of one scope share a parent whose resolution is computed once per scan; the row itself is still `lstat`ed and a link takes the original `realpath`. The memo is local to one scan. |
| `_global_row_path` takes the scan's resolved root | The global scan already resolved `<data>/skills`; `safe_skill_path` resolved it again per row. Name rule and containment check are unchanged. |
| `validator._RESERVED_DEVICE_NAMES` | The 19-member set was rebuilt on every call (once per row); now a module constant. |
| `loader._probe_document` uses `os.path.isfile` for the other-document check | Same regular-file question with one `stat`; consistent on Python 3.10–3.14 (unlike `Path.is_file` before 3.14). |
| `registry._locate_sidecar` | The common "no sidecar" answer is one `lstat` of a string path instead of two `Path` objects. A leading `~` keeps the original `expanduser` route. |
| `json_bytes(..., compact=True)` for list pages only | Drops padding after `,` and `:`. Parses to the same value; about 30% less encoder time and 4% fewer bytes. All other responses keep the default spelling. |

## Rejected

**[NOTE]** **gzip.** Compressing the 2.5 MB list at level 1 cost about 10.6 ms
of server CPU and 3.7 ms to decompress (in-process, 1,000 records) to save
2.2 MB on a socket that never leaves loopback. That is a net loss, so no
`Accept-Encoding` handling was added. Revisit only if the UI is ever served
beyond loopback, which the locked constraints forbid.

**[NOTE]** **`ensure_ascii=False`.** Smaller for non-ASCII text, but a lone
surrogate in a decoded string raises on `.encode("utf-8")`; the default escapes
it. Not worth a new failure mode.

**[NOTE]** **Trimming fields.** `portable_frontmatter` is 17% of the bytes and
unused by both UIs, but removing or renaming fields is an API change reserved
for the maintainer. Untouched.

**[NOTE]** **Caching the response.** The filesystem is the source of truth and
a stale list is a correctness bug; request-level coalescing already exists.

## Equivalence and tests

**[SPEC]** `tests/test_list_perf_equivalence.py` pins each shortcut against its
definition on a tree with in-root links, dangling and escaping links, a
symlinked scope root, recursive nested roots, disabled and conflicting
documents: `_memoized_realpath` and `_lexical_below` equal `os.path.realpath`
or defer; the named entry and escape rejection survive; the HTTP response
parses to exactly the library's rows minus `body`, is compact, pages, and
reports the same `Content-Length` for `HEAD`. A deliberate mutation (the
symlink check disabled) fails five of its tests.

**[NOTE]** Reproduce: `python3 benchmarks/list_perf.py build ROOT --skills N`,
then `PYTHONPATH=<tree> python3 benchmarks/list_perf.py time ROOT` for each
source tree, and `dump` to diff the parsed response.

## Not verified

**[?]** Windows and macOS: the shortcuts are POSIX-only by design and fall back
to the old code elsewhere, but neither host was run here. Browser-side time to parse and render the JSON.
A cold-cache first request. Real-library timing.
