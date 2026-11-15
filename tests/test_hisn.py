# Test cases for Hisn: each password + what Hisn should find in it.
# run them with:  python -m unittest discover -s tests
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import hisn

hisn.check_pwned = lambda password: 0   # no internet needed for tests

CASES = [
    # (password, words that must appear in the English findings, max score)
    ("A7med_1415",            ["common name -> ahmed", "year -> 1415"], 40),
    ("Hind@1426",             ["common name -> hind", "year -> 1426"], 40),
    ("3bdullah99",            ["common name -> abdullah"], 40),
    ("Hnooda@1",              ["nickname -> hnooda"], 60),
    ("Lulu@2020",             ["nickname -> lulu", "year -> 2020"], 40),
    ("Alotaibi99",            ["tribe or family name -> alotaibi"], 40),
    ("Hakami2005",            ["tribe or family name -> hakami", "year -> 2005"], 30),
    ("Bismillah2020",         ["religious phrase -> bismillah", "year -> 2020"], 50),
    ("N@ssr7",                ["football club -> nassr"], 50),
    ("AlZaeem2019",           ["football club -> alzaeem", "won the"], 30),
    ("Jeddah#123",            ["Saudi city -> jeddah", "short number sequence -> 123"], 60),
    ("Sara@987x",             ["short number sequence -> 987"], 70),
    ("12345678",              ["easy sequence"], 20),
    ("qwerty2024",            ["easy sequence", "year -> 2024"], 20),
    ("aaaa1111",              ["repeated characters"], 40),
    ("Hind0551234567",        ["Saudi phone number -> 0551234567"], 20),
    ("hgsghl",                ["English keyboard -> hgsghl"], 10),
    ("ik]2024",               ["English keyboard -> ik]", "year -> 2024"], 10),
    ("شفثقف",                 ["Arabic letters"], 20),
]

# strong passwords: nothing red, high score
STRONG = ["x9#Lm!pQ2v@Rt", "Qahwa-Sabah-Jabal-77!K"]


class TestHisn(unittest.TestCase):
    def test_weak_passwords(self):
        for password, expected, max_score in CASES:
            with self.subTest(password=password):
                result = hisn.analyze(password)
                text = " | ".join(f["en"] for f in result["findings"])
                for word in expected:
                    self.assertIn(word, text)
                self.assertLessEqual(result["score"], max_score)

    def test_strong_passwords(self):
        for password in STRONG:
            with self.subTest(password=password):
                result = hisn.analyze(password)
                self.assertGreaterEqual(result["score"], 70)

    def test_year_is_not_a_short_sequence(self):
        # 2012 has "012" inside but it's a year
        result = hisn.analyze("Mountain#2012")
        text = " | ".join(f["en"] for f in result["findings"])
        self.assertNotIn("short number sequence", text)

    def test_years_are_not_arabizi(self):
        # 2024 is a year, not "a0a4" letters
        result = hisn.analyze("Hilal@2024")
        names = [f["en"] for f in result["findings"] if "common name" in f["en"]]
        self.assertEqual(names, [])


if __name__ == "__main__":
    unittest.main()
