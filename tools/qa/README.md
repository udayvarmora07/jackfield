# HTTP regression checks

Run from the repository with Python 3.11 or later and a trusted Hurl 8.1.0
executable. Each `.hurl` file names one feature. Its response assertions
identify the request and field that broke. The runner creates new synthetic
skills, a temporary data directory, and an unauthenticated server bound to
`127.0.0.1` on a free port. The loopback binding is the server's only
security boundary. The runner shuts down the server and removes its fixtures
after the test. [Hurl installation](https://hurl.dev/docs/installation.html)

```sh
python3 tools/qa/run_http.py --hurl hurl --output-dir /absolute/path/to/qa-evidence
python3 tools/qa/summarize.py /absolute/path/to/qa-evidence/http-RUN/junit.xml
```

The runner prints the generated report path. Failures return a nonzero exit
code. The summary shows failed files, source locations, and actual and expected
values when Hurl supplies them. GitHub CI runs the contracts with the
hash-verified Hurl 8.1.0 release binary and attaches `http-contract-failures`
when a run produces a failing JUnit report. The report covers Library,
project discovery, enable/disable, and Recovery. The standard unit suite
remains available through `python3 -m unittest discover -s tests`.
The browser suites under `tools/e2e_v2` and `tools/e2e_classic` cover UI flows.

## Keploy results

Keploy's JUnit output can be read by the same summary tool. The example uses
the bundled synthetic saved run with the Keploy v3.7.13 open-source binary.
For another recorded run, pass the project directory containing
`keploy/reports/` to `keploy report --path`. Run it from a disposable project
directory because Keploy may generate a config file there.
[Keploy v3.7.13 report flags](https://github.com/keploy/keploy/blob/v3.7.13/cli/provider/cmd.go)

```sh
fixture=$(mktemp -d)
cp -R tools/qa/fixtures/keploy "$fixture/"
(cd "$fixture" && keploy report --format junit --path . > report.xml)
python3 tools/qa/summarize.py --keploy "$fixture/report.xml"
```

The summary exits with status 1 and reports `restore-skill` as the single
failure with HTTP 200 expected and 404 observed. `--keploy` accepts the known
startup warning that v3.7.13 can print before the XML if it cannot see cgroup
v2. Exporting this saved report needs no running server, account, or capture
privileges. Linux capture uses privileged eBPF. The hosted workflow documented
by Keploy uses an account and uploads reports and mocks.
[Keploy open-source workflows](https://github.com/keploy/keploy/blob/v3.7.13/AGENTS.md)
[Keploy hosted workflow](https://keploy.io/docs/server/install/)

## Agent Scan assessment

Snyk Agent Scan is relevant for reviewing skills and MCP configurations.
Its scan sends skill content and component metadata to its analysis service,
and the project describes the CLI output schema as experimental. The default
QA checks keep content local. Skills Manager's existing local risk patterns
and optional SkillSpector integration remain the skill review entry points.
[Agent Scan data handling](https://github.com/snyk/agent-scan#analysis-and-validation)
