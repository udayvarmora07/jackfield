#!/usr/bin/env python3
"""Run sandboxed local browser regression checks; see --help."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from browser_harness import _chrome, _node
from skillsmgr.launcher_security import trusted_executable


def _fixture_environment(root, home, data):
    """Keep provider credentials and host agent settings out of fixture processes."""
    env = {name: os.environ[name] for name in ('SYSTEMROOT', 'LANG', 'LC_ALL') if name in os.environ}
    temp = root / 'tmp'
    temp.mkdir(mode=0o700)
    env.update(
        HOME=str(home), USERPROFILE=str(home), PATH=os.defpath,
        TMPDIR=str(temp), TMP=str(temp), TEMP=str(temp),
        XDG_CONFIG_HOME=str(home / '.config'), XDG_DATA_HOME=str(home / '.local/share'),
        XDG_CACHE_HOME=str(home / '.cache'), XDG_STATE_HOME=str(home / '.local/state'),
        SKILLS_MANAGER_DATA=str(data), PYTHONDONTWRITEBYTECODE='1',
        CLAUDE_CONFIG_DIR=str(home / '.claude'), CODEX_HOME=str(home / '.codex'),
        GEMINI_CLI_SYSTEM_DEFAULTS_PATH=str(home / 'gemini-system-defaults.json'),
        GEMINI_CLI_SYSTEM_SETTINGS_PATH=str(home / 'gemini-system-settings.json'),
        BROWSER_TEST_ROOT=str(root),
    )
    return env


def _browser_environment(root, home, engine):
    env = dict(os.environ, BROWSER_TEST_ROOT=str(root), BROWSER_TEST_HOME=str(home),
               BROWSER_TEST_ENGINE=engine)
    if engine == 'chromium':
        requested = env.get('CHROME_BIN')
        chrome = trusted_executable('chrome', which=lambda _: requested) if requested else _chrome()
        if not chrome:
            raise RuntimeError('CHROME_BIN must identify a trusted Chrome executable')
        env['CHROME_BIN'] = chrome
    return env


def main():
    parser = argparse.ArgumentParser(description='Create isolated fixtures and run the optional Playwright browser suite.')
    parser.add_argument('--output-dir', required=True, type=Path, help='Existing or new directory for a fresh private run folder and evidence')
    parser.add_argument('--browser', choices=('chromium', 'firefox'), default='chromium',
                        help='Use trusted system Chrome (default) or Playwright-managed Firefox')
    parser.add_argument('--pilot', action='store_true',
                        help='Keep the seeded loopback fixture open for a moderated walkthrough until Ctrl-C')
    args = parser.parse_args()
    args.output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='skillsmgr-e2e-', dir=args.output_dir.resolve()))
    root.chmod(0o700)
    home, data = root / ('home-' + 'long-path-' * 16), root / 'data'
    for p in (home, data): p.mkdir(mode=0o700)
    roots = { 'claude': home/'.claude/skills', 'codex': home/'.codex/skills', 'opencode': home/'.config/opencode/skills', 'agents': home/'.agents/skills' }
    for p in roots.values(): p.mkdir(parents=True)
    def doc(name, text): return f'---\nname: {name}\ndescription: Use this fixture for browser testing.\n---\n# {name}\n\n{text}\n'
    def put(scope, name, body):
        d = roots[scope]/name; d.mkdir(); (d/'SKILL.md').write_text(doc(name, body))
    for scope in roots:
        put(scope, 'same-everywhere', 'Identical text.')
        put(scope, 'majority-minor', 'Different text.' if scope == 'codex' else 'Majority text.')
        put(scope, 'split-even', 'First text.' if scope in ('claude', 'codex') else 'Second text.')
    for scope in ('claude', 'opencode', 'agents'): put(scope, 'damaged-one', 'Readable text.')
    d = roots['codex']/'damaged-one'; d.mkdir(); (d/'SKILL.md').write_bytes(b'\xff\xfe')
    for name, disabled_scope in (('target-disabled', 'codex'), ('source-disabled', 'claude')):
        for scope in ('claude', 'codex'):
            put(scope, name, scope + ' original text')
        d = roots[disabled_scope]/name
        (d/'SKILL.md').rename(d/'SKILL.md.disabled')
    put('claude', 'sole-copy', 'A single fixture copy.')
    put('claude', 'markdown-reader', (
        '## Results\n\n'
        'Input | Result | Notes | Owner | Date | Status\n'
        ':--- | ---: | :---: | --- | --- | ---\n'
        '`a\\|b` | **Passed** | [Docs](https://example.test/Foo_(bar)) | A | Today | Ready\n\n'
        '- [x] Checked\n  - Nested detail\n\n'
        '~~~sh\nprintf "<tag>"\n~~~\n\n'
        '<img src=x onerror="window.fixtureAttack=1">\n\n'
        '![External image](https://example.test/should-not-load.png)'
    ))
    for scope in ('claude', 'codex', 'agents'):
        put(scope, 'share-three', 'A fixture awaiting its fourth agent copy.')
    for scope in ('claude', 'codex'):
        put(scope, 'damaged-fm', 'Readable text.')
    (roots['codex']/'damaged-fm/SKILL.md').write_text('---\nname: [broken\n---\n')
    (roots['claude']/'.system').mkdir()
    (home/'.claude/settings.json').write_text(json.dumps({'skillOverrides': {'same-everywhere': 'off'}}))
    (home/'.config/opencode/opencode.json').write_text(json.dumps({'permission': {'skill': {'same-everywhere': 'deny'}}}))
    if args.pilot:
        (roots['codex'] / 'majority-minor' / 'codex-checklist.txt').write_text(
            'Previous Codex copy only.\n', encoding='utf-8')
    server_env = _fixture_environment(root, home, data)
    browser_env = None if args.pilot else _browser_environment(root, home, args.browser)
    subprocess.run([sys.executable, '-m', 'skillsmgr', 'create', 'library-fixture', '-d',
                    'Use this for browser recovery checks.', '--body', 'Fixture body.'],
                   cwd=REPO, env=server_env, check=True, stdout=subprocess.DEVNULL)
    server_code = (
        'import os; from pathlib import Path; '
        'from skillsmgr.store import Store; from skillsmgr.webapp import WebAppServer; '
        'from skillsmgr.atomic_io import atomic_write_text; '
        'server=WebAppServer(Store(), host="127.0.0.1", port=0); '
        'atomic_write_text(Path(os.environ["BROWSER_TEST_ROOT"], "server-url.txt"), '
        '"http://127.0.0.1:"+str(server.port)); server.serve_forever()'
    )
    print(f'Fixture and evidence directory: {root}', flush=True)
    print('The localhost binding is the unauthenticated test server\'s only security boundary.', flush=True)
    local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with (root/'server.log').open('w') as log:
        server = subprocess.Popen([sys.executable, '-c', server_code], cwd=REPO, env=server_env,
                                  stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                if server.poll() is not None: raise RuntimeError('Server exited; inspect server.log')
                try:
                    url = (root/'server-url.txt').read_text()
                    with local_http.open(url+'/', timeout=.25): break
                except OSError: time.sleep(.1)
            else: raise RuntimeError('Server did not start; inspect server.log')
            if args.pilot:
                print(f'Open {url}/ in a fresh browser profile. Press Ctrl-C here when finished.', flush=True)
                return server.wait()
            browser_env['BROWSER_TEST_BASE'] = url
            result = subprocess.run([_node(), str(Path(__file__).with_name('browser.cjs'))],
                                    cwd=REPO, env=browser_env, timeout=360)
            return result.returncode
        except KeyboardInterrupt:
            return 130
        finally:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill(); server.wait()

if __name__ == '__main__': sys.exit(main())
