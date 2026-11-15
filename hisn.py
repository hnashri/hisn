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

def normalize_with_mask(text):
    """Decode Arabizi + leetspeak. Also returns which letters were changed,
    so we can ignore 'names' that are mostly made of decoded symbols."""
    text = text.lower()
    out, changed = [], []
    i = 0
    while i < len(text):
        # long digit runs (like 2024 or 0551234567) are numbers, not Arabizi letters
        if text[i].isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            if j - i >= 2:
                out.append(" ")
                changed.append(False)
                i = j
                continue
        ch = text[i]
        repl = leet.get(ch) or arabizi.get(ch)
        if repl:
            out.extend(repl)
            changed.extend([True] * len(repl))
        else:
            out.append(ch)
            changed.append(False)
        i += 1
    return "".join(out), changed

def normalize(text):
    return normalize_with_mask(text)[0]

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
    "cities":    ("cities.txt", "a Saudi city", 15),
}

wordlists = {}
for key, (filename, label, points) in WORDLISTS.items():
    wordlists[key] = load_wordlist(filename)
    print("Hisn loaded", len(wordlists[key]), key)

# clubs.json: every club with its names/nicknames and the years it won a title
def load_clubs():
    with open(DATA / "clubs.json", encoding="utf-8") as f:
        clubs = json.load(f)
    aliases = {}
    for club, info in clubs.items():
        for name in info["names"]:
            aliases[normalize(name).strip()] = club
    return clubs, aliases

clubs, club_aliases = load_clubs()
wordlists["clubs"] = set(club_aliases)
WORDLISTS["clubs"] = ("clubs.json", "a Saudi football club", 20)
print("Hisn loaded", len(clubs), "clubs")

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

# Arabic labels for each wordlist (formal, neutral wording)
ARABIC_LABELS = {
    "nicknames": "اسم تدليل",
    "tribes": "اسم قبيلة أو عائلة",
    "religious": "عبارة دينية شائعة",
    "clubs": "اسم نادٍ رياضي",
    "cities": "اسم مدينة سعودية",
}

def level_for(score):
    if score >= 70:
        return "green", "قوية"
    if score >= 40:
        return "yellow", "متوسطة"
    return "red", "ضعيفة"


def analyze(password):
    """Check one password and return the score + a list of findings."""
    findings = []   # each one: severity, English message, Arabic message

    def add(severity, en, ar):
        findings.append({"severity": severity, "en": en, "ar": ar})

    length = len(password)

    # ===== Character types =====
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)

    # ===== Score =====
    score = 0
    if length >= 12:
        score += 40
    elif length >= 8:
        score += 20
    else:
        add("red", "Too short (less than 8 characters)",
            "كلمة المرور قصيرة؛ يُنصح بألا تقل عن 12 حرفًا.")
    for flag in (has_upper, has_lower, has_digit, has_symbol):
        if flag:
            score += 15
    missing = [ar for flag, ar in ((has_upper, "حروف كبيرة"), (has_lower, "حروف صغيرة"),
                                   (has_digit, "أرقام"), (has_symbol, "رموز")) if not flag]
    if missing:
        add("yellow", "Missing character types",
            "لا تحتوي كلمة المرور على: " + "، ".join(missing) + ".")

    # ===== Normalize (decode Arabizi and leetspeak) =====
    normalized, changed = normalize_with_mask(password)

    # ===== Search for names (keep the longest match) =====
    # a name only counts if at most 1 of its letters came from a decoded symbol
    found_name = None
    for n in names:
        if len(n) < 4:
            continue
        pos = normalized.find(n)
        if pos != -1 and sum(changed[pos:pos + len(n)]) <= 1:
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

    # ===== Arabic names typed with the keyboard on English =====
    found_keyboard = None
    for keys, arabic in keyboard_names.items():
        if keys in low:
            if found_keyboard is None or len(keys) > len(found_keyboard[0]):
                found_keyboard = (keys, arabic)
    # skip it if it is just a piece of a word we already found (like "hali" in "madkhali")
    if found_keyboard:
        known = list(found_words.values()) + ([found_name] if found_name else [])
        if any(found_keyboard[0] in w for w in known):
            found_keyboard = None

    # ===== Arabic letters (keyboard left on Arabic) =====
    has_arabic = any("؀" <= c <= "ۿ" for c in password)

    # ===== Saudi phone numbers =====
    found_phone = re.search(r"(9665|05|5)\d{8}", password)

    # ===== Warnings =====
    if found_name:
        score -= 30
        add("red", "Contains a common name -> " + found_name,
            "تحتوي كلمة المرور على اسم شائع (" + found_name + ").")
    if found_year:
        score -= 20
        add("red", "Contains a year -> " + found_year,
            "تحتوي كلمة المرور على سنة (" + found_year + ")، وهي من أول ما يُجرَّب عند التخمين.")
    if found_sequence:
        score -= 20
        add("red", "Contains an easy sequence -> " + found_sequence,
            "تحتوي كلمة المرور على تسلسل سهل (" + found_sequence + ").")
    if found_repeat:
        score -= 20
        add("red", "Contains repeated characters -> " + found_repeat,
            "تحتوي كلمة المرور على حروف مكررة (" + found_repeat + ").")
    already_counted = {found_name}
    for key, word in found_words.items():
        if word in already_counted:
            continue
        filename, label, points = WORDLISTS[key]
        score -= points
        add("red", "Contains " + label + " -> " + word,
            "تحتوي كلمة المرور على " + ARABIC_LABELS[key] + " (" + word + ").")
        already_counted.add(word)
    if found_keyboard:
        score -= 30
        add("red", "Arabic word typed on the English keyboard -> " + found_keyboard[0],
            "تحتوي كلمة المرور على كلمة عربية (" + found_keyboard[1] +
            ") مكتوبة بلوحة المفاتيح الإنجليزية، وهذا الأسلوب معروف لدى المخترقين.")
    if has_arabic:
        intended = "".join(ARABIC_KEYS.get(c, c) for c in password)
        add("yellow", "Contains Arabic letters (keyboard may be set to Arabic) -> " + intended,
            "تحتوي كلمة المرور على حروف عربية؛ قد تكون لغة لوحة المفاتيح غير صحيحة. "
            "كثير من المواقع لا تقبلها وقد يُقفل الحساب بعد عدة محاولات. "
            "لو كانت اللوحة إنجليزية لكُتبت: " + intended)
    if found_phone:
        score -= 30
        add("red", "Contains a Saudi phone number -> " + found_phone.group(),
            "تحتوي كلمة المرور على رقم جوال سعودي (" + found_phone.group() + ")، وهو متاح للآخرين غالبًا.")

    # fans love writing the year their club won something
    club_word = found_words.get("clubs")
    if club_word and found_year:
        club = club_aliases.get(club_word)
        won = clubs.get(club, {}).get("titles", {}).get(found_year)
        if won:
            score -= 10
            add("red", club + " won the " + won + " in " + found_year,
                "السنة " + found_year + " هي سنة فوز النادي ببطولة، ويستخدمها المشجعون كثيرًا.")

    if (found_name or found_words or found_keyboard) and found_year:
        add("red", "A personal word + a year together = very easy to guess",
            "الجمع بين كلمة شخصية وسنة يجعل كلمة المرور سهلة التخمين جدًا.")

    # ===== Final score =====
    score = max(score, 0)
    color, level_ar = level_for(score)
    return {"score": score, "color": color, "level": level_ar,
            "length": length, "findings": findings}


# ===== Command line mode =====
if __name__ == "__main__":
    password = input("Enter your password: ")
    result = analyze(password)
    print("Your password has", result["length"], "characters")
    for f in result["findings"]:
        print("[" + f["severity"].upper() + "]", f["en"])
    print("Score:", result["score"], "/ 100", "(" + result["color"] + ")")
