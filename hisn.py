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

def load_saudi_words():
    words = set()
    with open(DATA / "saudi_words.txt", encoding="utf-8") as f:
        for line in f:
            line = line.strip().lower()
            if line and not line.startswith("#"):
                words.add(line)
    return words

saudi_words = load_saudi_words()
print("Hisn loaded", len(saudi_words), "Saudi words (clubs, cities)")

arabizi = {"2": "a", "3": "a", "5": "kh", "6": "t", "7": "h", "8": "q", "9": "s"}
leet = {"@": "a", "$": "s", "0": "o", "1": "i", "!": "i"}

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

# ===== Normalize (decode Arabizi) =====
# long digit runs (like 2024 or 0551234567) are numbers, not Arabizi letters
normalized = re.sub(r"\d{2,}", " ", password.lower())
for symbol, letter in leet.items():
    normalized = normalized.replace(symbol, letter)
for number, letter in arabizi.items():
    normalized = normalized.replace(number, letter)

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

# ===== Search for Saudi clubs and cities =====
found_saudi = None
for w in saudi_words:
    if w in normalized:
        if found_saudi is None or len(w) > len(found_saudi):
            found_saudi = w

# ===== Search for Saudi phone numbers =====
found_phone = re.search(r"(9665|05|5)\d{8}", password)

# ===== Warnings =====
if found_name:
    score -= 30
    print("Warning: contains a common name ->", found_name)
if found_year:
    score -= 20
    print("Warning: contains a year ->", found_year)
if found_name and found_year:
    print("DANGER: name + year together = very easy to guess!")
if found_sequence:
    score -= 20
    print("Warning: contains an easy sequence ->", found_sequence)
if found_repeat:
    score -= 20
    print("Warning: contains repeated characters ->", found_repeat)
if found_saudi and found_saudi != found_name:
    score -= 20
    print("Warning: contains a Saudi club or city ->", found_saudi)
if found_phone:
    score -= 30
    print("Warning: contains a Saudi phone number ->", found_phone.group())

# ===== Final score =====
if score < 0:
    score = 0

print("Score:", score, "/ 100")
