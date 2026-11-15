# runs Hisn on the 100 independent test cases and prints the results
# run it with: python tests/run_benchmark.py
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import hisn

hisn.check_pwned = lambda password: 0   # no internet needed

# these are tips not patterns so they don't count as "detected"
NOT_PATTERNS = ("Missing character types", "Too short", "Breach check")

rows = []
with open(Path(__file__).parent / "benchmark_100.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows.append(row)

tp = tn = fp = fn = 0
same_level = 0
for row in rows:
    result = hisn.analyze(row["password"])
    patterns = []
    for f in result["findings"]:
        if f["severity"] != "blue" and not f["en"].startswith(NOT_PATTERNS):
            patterns.append(f["en"])

    detected = len(patterns) > 0
    expected = row["should_detect"] == "نعم"
    if detected and expected:
        tp += 1
    elif detected and not expected:
        fp += 1
        print("False alarm:", row["password"], "->", patterns)
    elif expected:
        fn += 1
        print("Missed:", row["password"], "->", row["category"])
    else:
        tn += 1

    if result["level"] == row["expected_level"]:
        same_level += 1

print()
print("cases:", len(rows), " TP:", tp, " TN:", tn, " FP:", fp, " FN:", fn)
print("precision:", round(tp / (tp + fp), 3))
print("recall:", round(tp / (tp + fn), 3))
print("accuracy:", round((tp + tn) / len(rows), 3))
print("same level as expected:", same_level, "of", len(rows))
