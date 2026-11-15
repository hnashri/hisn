import csv
import json
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
normalized = password.lower()
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

# ===== Warnings =====
if found_name:
    score -= 30
    print("Warning: contains a common name ->", found_name)
if found_year:
    score -= 20
    print("Warning: contains a year ->", found_year)
if found_name and found_year:
    print("DANGER: name + year together = very easy to guess!")

if score < 0:
    score = 0

print("Score:", score, "/ 100")
