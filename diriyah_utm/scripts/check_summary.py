"""Recalculate a workbook with LibreOffice and check every Summary formula cell against the Python value build_final2.py saved.
Usage: python3 scripts/check_summary.py <workbook.xlsx> <expected.json> [--replace]
  --replace: overwrite the workbook with the recalculated copy (so viewers that do not recalculate show the numbers)."""
import sys, os, json, subprocess, tempfile, shutil
import openpyxl
X, E = sys.argv[1], sys.argv[2]
exp = json.load(open(E))
d = tempfile.mkdtemp()
r = subprocess.run(['soffice', '--headless', '--calc', '--convert-to', 'xlsx', '--outdir', d, X], capture_output=True, text=True, timeout=900)
out = os.path.join(d, os.path.basename(X))
if not os.path.exists(out): sys.exit('LibreOffice did not produce a file: ' + r.stdout + r.stderr)
ws = openpyxl.load_workbook(out, data_only=True)['Summary']
bad = []
for cell, v in exp.items():
    got = ws[cell].value
    if got is None or abs(float(got) - float(v)) > 1e-9: bad.append((cell, v, got))
print(f'checked {len(exp)} Summary cells: {len(exp) - len(bad)} match, {len(bad)} differ')
for b in bad[:30]: print('  MISMATCH', b)
if '--replace' in sys.argv and not bad: shutil.copy(out, X); print('workbook replaced with the recalculated copy')
sys.exit(1 if bad else 0)
