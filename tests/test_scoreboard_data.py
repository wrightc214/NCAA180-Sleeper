"""Independent Python/JS scoring parity, metadata, and immutable export checks.
Run: python -m unittest discover -s tests -p 'test_scoreboard*.py'
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, 'scripts')
from scoreboard_data import normalized, player_map, standard_settings


class ScoreboardTests(unittest.TestCase):
    def test_majority_and_explicit_standard(self):
        self.assertEqual(standard_settings({'a':{'x':1},'b':{'x':1,'zero':0},'c':{'x':2}},{'xp':0}),{'x':1,'xp':0})
        with self.assertRaises(ValueError):
            standard_settings({'a':{'x':1},'b':{'x':2}},{})

    def test_missing_and_multiple_positions_survive(self):
        p=player_map()
        self.assertIn('12015',p)
        self.assertIn('WR',p['12530']['positions'])
        self.assertIn('5086',p)

    def test_python_javascript_parity(self):
        # Independent sum: projection feeds already expose scoring categories;
        # test current and every saved game-time week against all league rules.
        scoring=json.loads(Path('data/projections/2026/scoring.json').read_text())
        cases=[]
        for file in sorted(Path('data/projections/2026/gametime').glob('*_proj.csv')):
            with file.open(newline='') as f:
                for r in csv.DictReader(f):
                    stats=json.loads(r['Stats'] or '{}')
                    for rules in scoring.values():
                        expected=round(sum(float(stats.get(k,0) or 0)*v for k,v in rules.items()),2)
                        cases.append([stats,rules,expected])
        script="const C=require('./reports/assets/scoreboard-core.js');let b='';process.stdin.on('data',x=>b+=x);process.stdin.on('end',()=>{const c=JSON.parse(b);const bad=c.filter(([s,r,v])=>Math.abs(C.score(s,r)-v)>.011);console.log(JSON.stringify({cases:c.length,bad:bad.length}));if(bad.length){console.log(JSON.stringify(bad.slice(0,1)));process.exit(1);}});"
        result=subprocess.run(['node','-e',script],input=json.dumps(cases),capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,0,result.stdout[:2000]);report=json.loads(result.stdout)
        self.assertGreater(report['cases'],50000)
        print('Independent Python/JS parity:',report)

    def test_exports_are_immutable_on_rebuild(self):
        files=list(Path('data/scoreboard/2026').glob('week-*.json'))
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        subprocess.run([sys.executable,'scripts/scoreboard_data.py','--offline'],check=True,capture_output=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


if __name__=='__main__':unittest.main()
