"""Shared square status cases run against real domain and model code."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / 'tests/fixtures/square-status-cases.json'


class SquareStatusCases(unittest.TestCase):
    def test_coverage(self):
        cases = json.loads(CASES.read_text(encoding='utf-8'))
        self.assertEqual({value for case in cases for value in case['expected'].values()},
                         {'working', 'missing', 'unreadable', 'version-1', 'version-2',
                          'different', 'off', 'settings', 'unknown', 'on'})
        self.assertTrue({'busy before missing', 'busy before unreadable',
                         'unreadable before split and off', 'split before off',
                         'different before off and settings', 'off before settings',
                         'settings before unknown'} <= {case['name'] for case in cases})

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to execute the browser model')
    def test_cases(self):
        script = r'''
const fs = require('fs'), vm = require('vm');
const sandbox = {window: {}, document: {}};
for (const f of ['domain.js', 'model.js']) vm.runInNewContext(fs.readFileSync(process.argv[1] + '/skillsmgr/webui/' + f, 'utf8'), sandbox);
const M = sandbox.window.SkillsV2Model, cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const scopes = ['a','b','c'].map(id => ({id, label:id, kind:'agent', exists:true}));
for (const c of cases) {
 const model = M.build(c.records, scopes), row = model.skills[0], busy = new Set(c.busy || []);
 for (const [id, expected] of Object.entries(c.expected)) {
  const actual = M.squareStatus(row, model.agent(id), busy);
  if (actual !== expected) throw Error(`${c.name} ${id}: ${actual} != ${expected}`);
 }
}
'''
        subprocess.run(['node', '-e', script, str(ROOT), str(CASES)], check=True,
                       capture_output=True, text=True)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to execute the browser model')
    def test_columns_camps_and_attention(self):
        script = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const ctx = {window:{}, document:{}};
for (const f of ['domain.js','model.js']) vm.runInNewContext(fs.readFileSync(process.argv[1]+'/skillsmgr/webui/'+f, 'utf8'),ctx);
const M = ctx.window.SkillsV2Model;
const scopes = [{id:'a', kind:'agent'}, {id:'b', kind:'agent'}, {id:'project-claude', kind:'project'}, {id:'project-codex', kind:'project'}];
const rec = (scope, hash, path) => ({name:'demo', scope, content_hash:hash, physical_path:path});
const model = M.build([rec('a','a','/shared'),rec('b','b','/b'),rec('project-claude','a','/shared'),rec('project-codex','a','/p')], scopes);
const row = model.skills[0], cols = M.tableAgents(model.agents);
assert.strictEqual(cols.length, 3);
assert.strictEqual(cols[2].scopes.length, 2);
assert.strictEqual(M.squareCamps(row,cols).map(g => g.length).join(','), '2,1');
assert.strictEqual(M.squareStatus(row,cols[2]), 'on');
assert.strictEqual(M.squareStatus(row,cols[1]), 'different');
assert.strictEqual(M.rowVerdict(row,cols), 'b has a different copy');
assert.strictEqual(M.attentionItems([row],cols).length, 1);
const mixed = M.build([rec('project-claude','a','/one'),rec('project-codex','b','/two')],scopes).skills[0];
assert.strictEqual(M.squareStatus(mixed,cols[2]), 'unknown');
assert.strictEqual(M.attentionItems([],cols).length, 0);
"""
        subprocess.run(['node', '-e', script, str(ROOT)], check=True,
                       capture_output=True, text=True)
