# Test cases for Hisn: each password + what Hisn should find in it
# run them with:  python -m unittest discover -s tests
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import hisn

hisn.check_pwned = lambda password: 0   # no internet needed for tests

CASES = [
    # (password words that must appear in the English findings max score)
    ("A7med_1415",            ["common name -> ahmed", "year -> 1415"], 40),
    ("Sara@1426",             ["common name -> sara", "year -> 1426"], 40),
    ("3bdullah99",            ["common name -> abdullah"], 40),
    ("Fahood@1",              ["nickname -> fahood"], 60),
    ("Lulu@2020",             ["nickname -> lulu", "year -> 2020"], 40),
    ("Alotaibi99",            ["family name -> alotaibi"], 40),
    ("Zahrani2005",           ["family name -> zahrani", "year -> 2005"], 30),
    ("Bismillah2020",         ["religious phrase -> bismillah", "year -> 2020"], 50),
    ("N@ssr7",                ["football club -> nassr"], 50),
    ("AlZaeem2019",           ["football club -> alzaeem", "won the"], 30),
    ("Jeddah#123",            ["Saudi city -> jeddah", "short number sequence -> 123"], 60),
    ("Sara@987x",             ["short number sequence -> 987"], 70),
    ("12345678",              ["easy sequence"], 20),
    ("qwerty2024",            ["easy sequence", "year -> 2024"], 20),
    ("aaaa1111",              ["repeated characters"], 40),
    ("Sara0551234567",        ["Saudi phone number -> 0551234567"], 20),
    ("hgsghl",                ["English keyboard -> hgsghl"], 10),
    ("lpl]2024",              ["English keyboard -> lpl]", "year -> 2024"], 20),
    ("شفثقف",                 ["Arabic letters"], 20),
    ("P@ssw0rd",              ["common password word"], 60),
    ("ILoveYou123",           ["common password word"], 40),
    ("Ghamdi@99",             ["family name -> ghamdi"], 60),
    ("Shehri2020",            ["family name -> shehri", "year -> 2020"], 30),
    ("Gahtani1",              ["family name -> gahtani"], 50),
    ("Hakamy99",              ["family name -> hakamy"], 50),
]

# strong passwords: nothing red high score
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

    def test_no_nickname_inside_tribe(self):
        result = hisn.analyze("Ghamdi@99")
        text = " | ".join(f["en"] for f in result["findings"])
        self.assertNotIn("nickname", text)

    def test_year_is_not_a_short_sequence(self):
        # 2012 has "012" inside but it's a year
        result = hisn.analyze("Mountain#2012")
        text = " | ".join(f["en"] for f in result["findings"])
        self.assertNotIn("short number sequence", text)

    def test_years_are_not_arabizi(self):
        # 2024 is a year not "a0a4" letters
        result = hisn.analyze("Hilal@2024")
        names = [f["en"] for f in result["findings"] if "common name" in f["en"]]
        self.assertEqual(names, [])

    # these came from people who tested Hisn for me

    def test_score_agrees_with_crack_time(self):
        # cracked in seconds = weak even if it has symbols
        self.assertEqual(hisn.analyze("Jeddah#123")["level"], "ضعيفة")
        # a long passphrase without capitals is still strong
        self.assertEqual(hisn.analyze("purple-kettle-drift-mango")["level"], "قوية")

    def test_name_must_be_a_whole_word(self):
        # mang is inside mango but it is not a name
        result = hisn.analyze("purple-kettle-drift-mango")
        text = " | ".join(f["en"] for f in result["findings"])
        self.assertNotIn("common name", text)

    def test_arabic_letters_count(self):
        # a long Arabic password is not weak just because it has no English letters
        result = hisn.analyze("قهوةالصباحالبارد")
        self.assertNotEqual(result["level"], "ضعيفة")

    def test_short_year(self):
        result = hisn.analyze("Sara05")
        text = " | ".join(f["en"] for f in result["findings"])
        self.assertIn("short year -> 05", text)

    def test_full_date(self):
        result = hisn.analyze("Noura01051426")
        text = " | ".join(f["en"] for f in result["findings"])
        self.assertIn("full date -> 01051426", text)
        self.assertIn("common name -> noura", text)

    def test_no_sequence_inside_phone(self):
        result = hisn.analyze("Sara0551234567")
        text = " | ".join(f["en"] for f in result["findings"])
        self.assertNotIn("sequence", text)

    # second review

    def test_arabizi_3_has_more_than_one_letter(self):
        # 3omar is omar and 3isa is eisa not aomar and aisa
        text = " | ".join(f["en"] for f in hisn.analyze("3omar@2001")["findings"])
        self.assertIn("omar", text)
        text = " | ".join(f["en"] for f in hisn.analyze("3isa1420")["findings"])
        self.assertIn("common name -> eisa", text)

    def test_list_words_must_be_whole_words(self):
        # abha is a city but kabhab is not abha
        text = " | ".join(f["en"] for f in hisn.analyze("Kabhab#Night!7")["findings"])
        self.assertNotIn("Saudi city", text)

    def test_three_attack_times(self):
        times = hisn.analyze("A7med_1415")["crack_times"]
        self.assertEqual(sorted(times), ["fast", "online", "slow"])

    def test_nist_2025_note(self):
        text = " | ".join(f["en"] for f in hisn.analyze("Sara@1426")["findings"])
        self.assertIn("NIST (2025): minimum 15 characters", text)


if __name__ == "__main__":
    unittest.main()
