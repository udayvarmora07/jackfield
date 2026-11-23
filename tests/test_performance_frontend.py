"""Behavioral regressions for frontend performance changes."""

from __future__ import annotations

import json
import subprocess
import unittest


def run_frontend(script: str) -> dict:
    capture_error = "process.on('uncaughtException',e=>{console.error('CAUGHT '+e.name+': '+e.message);process.exitCode=1}); process.on('unhandledRejection',e=>{console.error('CAUGHT '+e.name+': '+e.message);process.exitCode=1});\n"
    result = subprocess.run(["node", "-e", capture_error + script], capture_output=True, encoding="utf-8", timeout=30)
    if result.returncode:
        lines = [line for line in result.stderr.splitlines() if len(line) < 1000]
        raise AssertionError("\n".join(lines[-8:]))
    return json.loads(result.stdout)


class FrontendPerformanceBehaviorTests(unittest.TestCase):

    def test_real_domain_formatters_preserve_locale_output_and_bound_cache(self):
        result = run_frontend(r'''
const fs = require('fs'), vm = require('vm');
const NativeNumber = Intl.NumberFormat, NativeDate = Intl.DateTimeFormat;
let numberBuilds = 0, dateBuilds = 0;
class CountedNumber extends NativeNumber { constructor(...args){ super(...args); numberBuilds++; } }
class CountedDate extends NativeDate { constructor(...args){ super(...args); dateBuilds++; } }
const sandbox = {window:{}, Intl:{NumberFormat:CountedNumber,DateTimeFormat:CountedDate}};
const context=vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('skillsmgr/webui/domain.js','utf8'), context);
const d = sandbox.window.SkillManagerDomain;
const first = d.numberFormatter('en-IN').format(1234567);
const second = d.numberFormatter('en-IN').format(1234567);
const reusedAfterRepeat = numberBuilds;
const usDefault = d.numberFormatter('en-US').format(1234567);
const usFixed = d.numberFormatter('en-US',{minimumFractionDigits:2}).format(1234567);
const date1 = d.dateFormatter('en-GB',{dateStyle:'medium',timeStyle:'short'}).format(new Date('2026-09-22T13:45:00Z'));
const date2 = d.dateFormatter('en-GB',{dateStyle:'medium',timeStyle:'short'}).format(new Date('2026-09-22T13:45:00Z'));
const reusedDate = dateBuilds;
for (let i=0;i<70;i++) d.numberFormatter('en-US',{
  minimumFractionDigits:i%21,
  signDisplay:['auto','never','always','exceptZero'][Math.floor(i/21)]
}).format(7);
// The cache is capped at 64 entries; after its reset the oldest key must be
// reconstructed, while repeated current keys above reuse the same instance.
d.numberFormatter('en-US',{minimumFractionDigits:0,signDisplay:'auto'}).format(7);
console.log(JSON.stringify({first,second,usDefault,usFixed,date1,date2,reusedAfterRepeat,reusedDate,numberBuilds,dateBuilds}));
''')
        self.assertEqual(result["first"], "12,34,567")
        self.assertEqual(result["second"], result["first"])
        self.assertEqual(result["reusedAfterRepeat"], 1)
        self.assertEqual(result["usDefault"], "1,234,567")
        self.assertEqual(result["usFixed"], "1,234,567.00")
        self.assertEqual(result["date2"], result["date1"])
        self.assertEqual(result["reusedDate"], 1)
        self.assertEqual(result["dateBuilds"], 1)
        self.assertEqual(result["numberBuilds"], 74)


if __name__ == "__main__":
    unittest.main()
