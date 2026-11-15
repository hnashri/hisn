import csv
import json
import re
from pathlib import Path

# ===== Load data =====
DATA = Path(__file__).parent / "data"

def load_names():
    names = set()

    with open(DATA / "muslim_names.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["english_name"].strip().lower()
            if len(name) >= 3:
                names.add(name)

    with open(DATA / "arabic_name_pairs.json", encoding="utf-8") as f:
        for name in json.load(f):
            name = name.strip().lower()
            if len(name) >= 3:
                names.add(name)

    return names

names = load_names()
print("Hisn loaded", len(names), "names")

arabizi = {"2": "a", "3": "a", "5": "kh", "6": "t", "7": "h", "8": "q", "9": "s"}
leet = {"@": "a", "$": "s", "0": "o", "1": "i", "!": "i"}

def normalize(text):
    # long digit runs (like 2024 or 0551234567) are numbers, not Arabizi letters
    text = re.sub(r"\d{2,}", " ", text.lower())
    for symbol, letter in leet.items():
        text = text.replace(symbol, letter)
    for number, letter in arabizi.items():
        text = text.replace(number, letter)
    return text

def load_wordlist(filename):
    words = set()
    with open(DATA / filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                words.add(normalize(line).strip())
    return words

# each list: (file, label shown to the user, points removed)
WORDLISTS = {
    "nicknames": ("nicknames.txt", "a nickname", 30),
    "tribes":    ("tribes.txt", "a tribe or family name", 30),
    "religious": ("religious.txt", "a common religious phrase", 20),
    "clubs":     ("clubs.txt", "a Saudi football club", 20),
    "cities":    ("cities.txt", "a Saudi city", 15),
}

wordlists = {}
for key, (filename, label, points) in WORDLISTS.items():
    wordlists[key] = load_wordlist(filename)
    print("Hisn loaded", len(wordlists[key]), key)

# club nicknames -> club, and the years each club won a title
def load_club_data():
    aliases = {}
    with open(DATA / "club_aliases.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            aliases[row["alias"]] = row["club"]
    titles = {}
    with open(DATA / "club_titles.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            titles.setdefault(row["club"], {})[row["year"]] = row["competition"]
    return aliases, titles

club_aliases, club_titles = load_club_data()

# Arabic keyboard (Windows 101) -> the English key in the same place
# so "السلام" typed with the keyboard on English becomes "hgsghl"
ARABIC_KEYS = {
    "ض": "q", "ص": "w", "ث": "e", "ق": "r", "ف": "t", "غ": "y", "ع": "u",
    "ه": "i", "خ": "o", "ح": "p", "ج": "[", "د": "]", "ش": "a", "س": "s",
    "ي": "d", "ب": "f", "ل": "g", "ا": "h", "ت": "j", "ن": "k", "م": "l",
    "ك": ";", "ط": "'", "ئ": "z", "ء": "x", "ؤ": "c", "ر": "v", "ى": "n",
    "ة": "m", "و": ",", "ز": ".", "ظ": "/", "ذ": "`",
    "أ": "h", "إ": "h", "آ": "h",
}
DIACRITICS = re.compile(r"[\u064B-\u0652\u0640]")  # tashkeel + tatweel

def to_english_keys(arabic_text):
    arabic_text = DIACRITICS.sub("", arabic_text)
    return "".join(ARABIC_KEYS.get(ch, "") for ch in arabic_text)

# common Arabic words people type as passwords
COMMON_ARABIC_WORDS = ["السلام", "حبيبي", "حبيبتي", "الله", "الحمدلله", "بسمالله",
                       "ماشاءالله", "سبحانالله", "السعودية", "سعودي", "الهلال",
                       "النصر", "الاتحاد", "الاهلي", "الرياض", "جدة", "مكة"]

def add_keyed(keyed, arabic):
    keys = to_english_keys(arabic)
    # 3 keys is enough if it has a symbol key like ] ; ' (rare in normal words)
    if len(keys) >= 4 or (len(keys) == 3 and any(not k.isalpha() for k in keys)):
        keyed[keys] = DIACRITICS.sub("", arabic)

def load_keyboard_names():
    keyed = {}
    with open(DATA / "muslim_names.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            arabic = row["arabic_name"].strip()
            add_keyed(keyed, arabic)
    for word in COMMON_ARABIC_WORDS:
        add_keyed(keyed, word)
    return keyed

keyboard_names = load_keyboard_names()
print("Hisn loaded", len(keyboard_names), "names typed on the wrong keyboard")

# ===== Read password =====
password = input("Enter your password: ")
length = len(password)
print("Your password has", length, "characters")

# ===== Character types =====
has_upper = any(c.isupper() for c in password)
has_lower = any(c.islower() for c in password)
has_digit = any(c.isdigit() for c in password)
has_symbol = any(not c.isalnum() for c in password)

print("Uppercase:", has_upper)
print("Lowercase:", has_lower)
print("Digits:", has_digit)
print("Symbols:", has_symbol)

# ===== Score =====
score = 0

if length >= 12:
    score += 40
elif length >= 8:
    score += 20

if has_upper:
    score += 15
if has_lower:
    score += 15
if has_digit:
    score += 15
if has_symbol:
    score += 15

# ===== Normalize (decode Arabizi and leetspeak) =====
normalized = normalize(password)

# ===== Search for names (keep the longest match) =====
found_name = None
for n in names:
    if n in normalized:
        if found_name is None or len(n) > len(found_name):
            found_name = n

# ===== Search for years (on the original password) =====
found_year = None
for i in range(len(password) - 3):
    part = password[i:i+4]
    if part.isdigit():
        year = int(part)
        if 1950 <= year <= 2030 or 1370 <= year <= 1460:
            found_year = part

# ===== Search for sequences =====
sequences = ["0123456789", "abcdefghijklmnopqrstuvwxyz",
             "qwertyuiop", "asdfghjkl", "zxcvbnm"]

found_sequence = None
low = password.lower()
for seq in sequences:
    for i in range(len(seq) - 3):
        chunk = seq[i:i+4]
        if chunk in low or chunk[::-1] in low:
            found_sequence = chunk

# ===== Search for repeated characters =====
found_repeat = None
for i in range(len(password) - 3):
    if password[i] * 4 == password[i:i+4]:
        found_repeat = password[i:i+4]

# ===== Search in the Saudi wordlists =====
found_words = {}
for key, words in wordlists.items():
    best = None
    for w in words:
        if len(w) >= 3 and w in normalized:
            if best is None or len(w) > len(best):
                best = w
    if best:
        found_words[key] = best

# if a generic name overlaps a more specific word (tribe, nickname, city...),
# keep the specific one because its warning is more useful
def overlaps(a, b):
    i, j = normalized.find(a), normalized.find(b)
    return i < j + len(b) and j < i + len(a)

if found_name and any(overlaps(found_name, w) for w in found_words.values()):
    found_name = None

# ===== Search for Arabic names typed with the keyboard on English =====
found_keyboard = None
low_pw = password.lower()
for keys, arabic in keyboard_names.items():
    if keys in low_pw:
        if found_keyboard is None or len(keys) > len(found_keyboard[0]):
            found_keyboard = (keys, arabic)

# ===== Search for Arabic letters (keyboard left on Arabic) =====
has_arabic = any("\u0600" <= c <= "\u06FF" for c in password)

# ===== Search for Saudi phone numbers =====
found_phone = re.search(r"(9665|05|5)\d{8}", password)

# ===== Warnings =====
if found_name:
    score -= 30
    print("Warning: contains a common name ->", found_name)
if found_year:
    score -= 20
    print("Warning: contains a year ->", found_year)
if found_sequence:
    score -= 20
    print("Warning: contains an easy sequence ->", found_sequence)
if found_repeat:
    score -= 20
    print("Warning: contains repeated characters ->", found_repeat)
already_counted = {found_name}
for key, word in found_words.items():
    if word in already_counted:
        continue
    filename, label, points = WORDLISTS[key]
    score -= points
    print("Warning: contains " + label + " ->", word)
    already_counted.add(word)
if found_keyboard:
    score -= 30
    print("Warning: an Arabic name or word typed on the English keyboard ->", found_keyboard[0])
if has_arabic:
    intended = "".join(ARABIC_KEYS.get(c, c) for c in password)
    print("Warning: contains Arabic letters - the keyboard may be set to Arabic.")
    print("         Many sites reject them and you could get locked out.")
    print("         On an English keyboard you would have typed ->", intended)
if found_phone:
    score -= 30
    print("Warning: contains a Saudi phone number ->", found_phone.group())

# fans love writing the year their club won something
club_word = found_words.get("clubs")
if club_word and found_year:
    club = club_aliases.get(club_word)
    won = club_titles.get(club, {}).get(found_year)
    if won:
        score -= 10
        print("DANGER: " + club + " won the " + won + " in " + found_year + " - fans often use this year!")

if (found_name or found_words or found_keyboard) and found_year:
    print("DANGER: a personal word + a year together = very easy to guess!")

# ===== Final score =====
if score < 0:
    score = 0

print("Score:", score, "/ 100")
