# compares Hisn with zxcvbn (the most famous password meter) on the same test cases
# needs: pip install zxcvbn
# run it with: python tests/compare_zxcvbn.py
import csv
import sys
from pathlib import Path

from zxcvbn import zxcvbn

sys.path.insert(0, str(Path(__file__).parent.parent))
import hisn

hisn.check_pwned = lambda password: 0


def zxcvbn_level(score):
    # zxcvbn gives 0 to 4 so I turn it into my 3 levels
    if score <= 1:
        return "ضعيفة"
    if score == 2:
        return "متوسطة"
    return "قوية"


rows = []
with open(Path(__file__).parent / "benchmark_100.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows.append(row)

hisn_same = 0
zx_same = 0
patterns = 0
zx_strong = 0
hisn_weak = 0
for row in rows:
    h = hisn.analyze(row["password"])["level"]
    z = zxcvbn_level(zxcvbn(row["password"])["score"])
    if h == row["expected_level"]:
        hisn_same += 1
    if z == row["expected_level"]:
        zx_same += 1
    # passwords that have a Saudi pattern inside
    if row["should_detect"] == "نعم":
        patterns += 1
        if z == "قوية":
            zx_strong += 1
            if h == "ضعيفة":
                hisn_weak += 1

print("same level as expected: Hisn", hisn_same, "zxcvbn", zx_same, "of", len(rows))
print("passwords with a Saudi pattern:", patterns)
print("zxcvbn called them strong:", zx_strong, "and Hisn called", hisn_weak, "of those weak")
