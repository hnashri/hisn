# Hisn - a password checker that understands Arabic names, Arabizi and Hijri years
# by Hind Nashri

import csv
import json
import hashlib
import re
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"


# ---------- names ----------

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


# ---------- turning A7med into ahmed ----------

# people write Arabic letters with numbers: 7 = h, 3 = a (ع) ...
arabizi = {"2": "a", "3": "a", "5": "kh", "6": "t", "7": "h", "8": "q", "9": "s"}

# and swap letters with symbols: @ = a, 0 = o ...
leet = {"@": "a", "$": "s", "0": "o", "1": "i", "!": "i", "4": "a"}


def normalize_with_mask(text):
    # returns the decoded text + a list that says which letters were decoded
    # (I need it later so a "name" made only of symbols doesn't count)
    text = text.lower()
    out = []
    changed = []
    i = 0

    while i < len(text):
        # 2024 or 0551234567 are numbers, not Arabizi, so I skip them
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
        if ch in leet:
            new = leet[ch]
        elif ch in arabizi:
            new = arabizi[ch]
        else:
            new = None

        if new:
            for letter in new:
                out.append(letter)
                changed.append(True)
        else:
            out.append(ch)
            changed.append(False)
        i += 1

    return "".join(out), changed


def normalize(text):
    decoded, changed = normalize_with_mask(text)
    return decoded


def spelling_variants(word):
    # same Arabic name, different English spelling:
    # sharif / shareef / shereef, qahtani / gahtani, hakami / hakamy
    variants = {word}

    swaps = [("ee", "i"), ("i", "ee"), ("oo", "u"), ("u", "oo"), ("ou", "u"),
             ("aa", "a"), ("q", "g"), ("q", "k"), ("a", "e")]
    for old, new in swaps:
        for v in list(variants):
            if old in v:
                variants.add(v.replace(old, new, 1))

    for v in list(variants):
        # hakami -> hakamy, hakamee, hakamie
        if v.endswith("i"):
            start = v[:-1]
            variants.add(start + "y")
            variants.add(start + "ee")
            variants.add(start + "ie")

        # mujarrashi -> mujarashi
        for i in range(len(v) - 1):
            if v[i] == v[i + 1] and v[i].isalpha() and v[i] not in "aeiou":
                variants.add(v[:i] + v[i + 1:])

    return variants


# ---------- my word lists (data folder) ----------

def load_wordlist(filename):
    words = set()
    with open(DATA / filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            word = normalize(line).strip()
            if filename in ("tribes.txt", "nicknames.txt", "cities.txt"):
                words.update(spelling_variants(word))
            else:
                words.add(word)
    return words


# list name: (file, English label, points to remove)
WORDLISTS = {
    "nicknames": ("nicknames.txt", "a nickname", 30),
    "tribes": ("tribes.txt", "a tribe or family name", 30),
    "religious": ("religious.txt", "a common religious phrase", 20),
    "cities": ("cities.txt", "a Saudi city", 15),
    "common": ("common_words.txt", "a very common password word", 30),
}

wordlists = {}
for key in WORDLISTS:
    filename = WORDLISTS[key][0]
    wordlists[key] = load_wordlist(filename)
    print("Hisn loaded", len(wordlists[key]), key)


# ---------- clubs (names, nicknames, title years) ----------

def load_clubs():
    with open(DATA / "clubs.json", encoding="utf-8") as f:
        clubs = json.load(f)

    # alzaeem -> hilal, alalami -> nassr ...
    aliases = {}
    for club in clubs:
        for name in clubs[club]["names"]:
            aliases[normalize(name).strip()] = club

    return clubs, aliases


clubs, club_aliases = load_clubs()
wordlists["clubs"] = set(club_aliases)
WORDLISTS["clubs"] = ("clubs.json", "a Saudi football club", 20)
print("Hisn loaded", len(clubs), "clubs")


# ---------- Arabic words typed with the keyboard on English ----------

# each Arabic letter and the English key in the same place
# so "السلام" becomes "hgsghl" if you forget to switch the keyboard
ARABIC_KEYS = {
    "ض": "q", "ص": "w", "ث": "e", "ق": "r", "ف": "t", "غ": "y", "ع": "u",
    "ه": "i", "خ": "o", "ح": "p", "ج": "[", "د": "]", "ش": "a", "س": "s",
    "ي": "d", "ب": "f", "ل": "g", "ا": "h", "ت": "j", "ن": "k", "م": "l",
    "ك": ";", "ط": "'", "ئ": "z", "ء": "x", "ؤ": "c", "ر": "v", "ى": "n",
    "ة": "m", "و": ",", "ز": ".", "ظ": "/", "ذ": "`",
    "أ": "h", "إ": "h", "آ": "h",
}

# tashkeel and tatweel, removed before converting
DIACRITICS = re.compile(r"[ً-ْـ]")

COMMON_ARABIC_WORDS = ["السلام", "حبيبي", "حبيبتي", "الله", "الحمدلله", "بسمالله",
                       "ماشاءالله", "سبحانالله", "السعودية", "سعودي", "الهلال",
                       "النصر", "الاتحاد", "الاهلي", "الرياض", "جدة", "مكة"]


def to_english_keys(arabic_text):
    arabic_text = DIACRITICS.sub("", arabic_text)
    keys = ""
    for ch in arabic_text:
        if ch in ARABIC_KEYS:
            keys += ARABIC_KEYS[ch]
    return keys


def add_keyed(keyed, arabic):
    keys = to_english_keys(arabic)

    has_symbol = False
    for k in keys:
        if not k.isalpha():
            has_symbol = True

    # short letter-only keys look like normal English, so they need 5+
    # with a symbol like ] or ; even 3 is enough (هند = ik])
    if len(keys) >= 5 or (len(keys) >= 3 and has_symbol):
        keyed[keys] = DIACRITICS.sub("", arabic)


def load_keyboard_names():
    keyed = {}
    with open(DATA / "muslim_names.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            add_keyed(keyed, row["arabic_name"].strip())
    for word in COMMON_ARABIC_WORDS:
        add_keyed(keyed, word)
    return keyed


keyboard_names = load_keyboard_names()
print("Hisn loaded", len(keyboard_names), "names typed on the wrong keyboard")


# ---------- messages ----------

ARABIC_LABELS = {
    "nicknames": "اسم تدليل",
    "tribes": "اسم قبيلة أو عائلة",
    "religious": "عبارة دينية شائعة",
    "clubs": "اسم نادٍ رياضي",
    "cities": "اسم مدينة سعودية",
    "common": "كلمة شائعة جدًا في كلمات المرور",
}

# the reason, shown after each warning
WHY = {
    "nicknames": "اسم التدليل يعرفه المقربون ويظهر في الحسابات، فيسهل على المخترق تخمينه.",
    "tribes": "اسم العائلة أو القبيلة معروف ويظهر في الحسابات، فيسهل على المخترق تخمينه.",
    "religious": "العبارات الدينية يستخدمها كثيرون، فهي من أول ما يجربه المخترق.",
    "clubs": "أسماء الأندية وألقابها من أول ما يجربه المخترق، خصوصًا مع سنة بطولة.",
    "cities": "اسم المدينة مرتبط بالشخص، فيسهل على المخترق تخمينه.",
    "common": "هذه الكلمات أول ما يجربه المخترق، حتى لو استُبدلت بعض حروفها برموز.",
}


# ---------- data breaches (Have I Been Pwned) ----------

def check_pwned(password):
    # I never send the password. I hash it with sha1 and send only the first 5
    # characters, the site sends back all hashes that start with them and I
    # compare the rest here (this is called k-anonymity)
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]

    request = urllib.request.Request(
        "https://api.pwnedpasswords.com/range/" + prefix,
        headers={"User-Agent": "Hisn-password-checker", "Add-Padding": "true"})

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            lines = response.read().decode("utf-8").splitlines()
    except Exception:
        return None   # no internet

    for line in lines:
        hash_suffix, count = line.split(":")
        if hash_suffix == suffix:
            return int(count)
    return 0


# ---------- time to crack ----------

def human_time_ar(seconds):
    if seconds < 1:
        return "أقل من ثانية"

    # (how many of this unit make the next one, singular, plural for 3-10)
    units = [(60, "ثانية", "ثوانٍ"), (60, "دقيقة", "دقائق"), (24, "ساعة", "ساعات"),
             (30, "يوم", "أيام"), (12, "شهر", "أشهر"), (100, "سنة", "سنوات")]

    value = seconds
    for size, singular, plural in units:
        if value < size:
            n = int(value)
            if 3 <= n <= 10:
                return str(n) + " " + plural
            return str(n) + " " + singular
        value = value / size

    if value < 10:
        return "أكثر من 100 سنة"
    return "قرون"


def estimate_crack_seconds(password, known_parts, pwned):
    # a leaked password is guessed right away
    if pwned:
        return 0

    charset = 0
    if any_char(password, "lower"):
        charset += 26
    if any_char(password, "upper"):
        charset += 26
    if any_char(password, "digit"):
        charset += 10
    if any_char(password, "symbol"):
        charset += 33
    if charset < 10:
        charset = 10

    # a name or a year isn't guessed letter by letter, the hacker picks it
    # from a list, so it counts as one choice from that list
    random_length = len(password)
    guesses = 1
    for part, list_size in known_parts:
        random_length -= len(part)
        guesses *= list_size
    if random_length > 0:
        guesses *= charset ** random_length

    # a strong computer tries about 10 billion passwords per second
    return guesses / 10_000_000_000


# ---------- small helpers ----------

def any_char(password, kind):
    for c in password:
        if kind == "lower" and c.islower():
            return True
        if kind == "upper" and c.isupper():
            return True
        if kind == "digit" and c.isdigit():
            return True
        if kind == "symbol" and not c.isalnum():
            return True
    return False


def overlaps(text, a, b):
    # do words a and b share any letters in text?
    i = text.find(a)
    j = text.find(b)
    if i == -1 or j == -1:
        return False
    return i < j + len(b) and j < i + len(a)


def level_for(score):
    if score >= 70:
        return "green", "قوية"
    if score >= 40:
        return "yellow", "متوسطة"
    return "red", "ضعيفة"


# ---------- the main check ----------

def analyze(password):
    findings = []

    def add(severity, en, ar):
        findings.append({"severity": severity, "en": en, "ar": ar})

    length = len(password)
    low = password.lower()

    has_upper = any_char(password, "upper")
    has_lower = any_char(password, "lower")
    has_digit = any_char(password, "digit")
    has_symbol = any_char(password, "symbol")

    # --- start with length and character types ---
    score = 0
    if length >= 12:
        score += 40
    elif length >= 8:
        score += 20
    else:
        add("red", "Too short (less than 8 characters)",
            "كلمة المرور قصيرة؛ يُنصح بألا تقل عن 12 حرفًا.")

    missing = []
    if has_upper:
        score += 15
    else:
        missing.append("حروف كبيرة")
    if has_lower:
        score += 15
    else:
        missing.append("حروف صغيرة")
    if has_digit:
        score += 15
    else:
        missing.append("أرقام")
    if has_symbol:
        score += 15
    else:
        missing.append("رموز")

    if missing:
        add("yellow", "Missing character types",
            "لا تحتوي كلمة المرور على: " + "، ".join(missing) + ".")

    # --- decode A7med -> ahmed before searching ---
    normalized, changed = normalize_with_mask(password)

    # --- names (the longest one wins) ---
    # a name only counts if at most 1 letter came from a symbol,
    # otherwise random passwords like x9#Lm@Rt give fake names
    found_name = None
    for n in names:
        if len(n) < 4:
            continue
        pos = normalized.find(n)
        if pos == -1:
            continue
        decoded_letters = sum(changed[pos:pos + len(n)])
        if decoded_letters <= 1:
            if found_name is None or len(n) > len(found_name):
                found_name = n

    # --- years (gregorian 1950-2030, hijri 1370-1460) ---
    found_year = None
    for i in range(len(password) - 3):
        part = password[i:i + 4]
        if part.isdigit():
            year = int(part)
            if 1950 <= year <= 2030 or 1370 <= year <= 1460:
                found_year = part

    # --- sequences like 1234, abcd, qwerty ---
    sequences = ["0123456789", "abcdefghijklmnopqrstuvwxyz",
                 "qwertyuiop", "asdfghjkl", "zxcvbnm"]
    found_sequence = None
    for seq in sequences:
        for i in range(len(seq) - 3):
            chunk = seq[i:i + 4]
            backwards = chunk[::-1]
            if chunk in low or backwards in low:
                found_sequence = chunk

    # --- short ones like 123 or 987 (not inside a year like 2012) ---
    short_sequence = None
    if not found_sequence:
        text = low
        if found_year:
            text = text.replace(found_year, " ")
        for i in range(8):
            chunk = "0123456789"[i:i + 3]
            if chunk in text:
                short_sequence = chunk
            elif chunk[::-1] in text:
                short_sequence = chunk[::-1]

    # --- aaaa or 1111 ---
    found_repeat = None
    for i in range(len(password) - 3):
        if password[i] * 4 == password[i:i + 4]:
            found_repeat = password[i:i + 4]

    # --- my lists: nicknames, tribes, clubs, cities ... ---
    found_words = {}
    for key in wordlists:
        best = None
        for w in wordlists[key]:
            if len(w) >= 3 and w in normalized:
                if best is None or len(w) > len(best):
                    best = w
        if best:
            found_words[key] = best

    # hamdi is inside ghamdi, so keep only ghamdi
    for key in list(found_words):
        word = found_words[key]
        for other in found_words.values():
            if other != word and word in other:
                del found_words[key]
                break

    # if the name is part of a tribe/nickname we found, the tribe message is better
    if found_name:
        for w in found_words.values():
            if overlaps(normalized, found_name, w):
                found_name = None
                break

    # --- Arabic word typed on the English keyboard ---
    found_keyboard = None
    for keys in keyboard_names:
        if keys in low:
            if found_keyboard is None or len(keys) > len(found_keyboard[0]):
                found_keyboard = (keys, keyboard_names[keys])

    # skip it if it's just part of a word we already found (hali in madkhali)
    if found_keyboard:
        known = list(found_words.values())
        if found_name:
            known.append(found_name)
        for w in known:
            if found_keyboard[0] in w or overlaps(low, found_keyboard[0], w):
                found_keyboard = None
                break

    # --- Arabic letters = the keyboard was left on Arabic ---
    has_arabic = False
    for c in password:
        if "؀" <= c <= "ۿ":
            has_arabic = True

    # --- Saudi mobile number: 05xxxxxxxx, 9665xxxxxxxx or 5xxxxxxxx ---
    found_phone = re.search(r"(9665|05|5)\d{8}", password)

    # ---------- warnings ----------

    if found_name:
        score -= 30
        pos = normalized.find(found_name)
        note = ""
        if any(changed[pos:pos + len(found_name)]):
            note = " حتى مع استبدال بعض الحروف بأرقام أو رموز، فهذه الحيلة معروفة."
        add("red", "Contains a common name -> " + found_name,
            "تحتوي كلمة المرور على اسم شائع (" + found_name + ")." + note +
            " الأسماء من أول ما يجربه المخترق، خصوصًا اسم صاحب الحساب أو أفراد عائلته.")

    if found_year:
        score -= 20
        if 1370 <= int(found_year) <= 1460:
            kind = "هجرية"
        else:
            kind = "ميلادية"
        add("red", "Contains a year -> " + found_year,
            "تحتوي كلمة المرور على سنة " + kind + " (" + found_year + "). "
            "سنوات الميلاد والتخرج تظهر غالبًا في الحسابات، وهي من أول ما يُجرَّب عند التخمين.")

    if found_sequence:
        score -= 20
        add("red", "Contains an easy sequence -> " + found_sequence,
            "تحتوي كلمة المرور على تسلسل سهل (" + found_sequence + ").")

    if short_sequence:
        score -= 10
        add("yellow", "Contains a short number sequence -> " + short_sequence,
            "تحتوي كلمة المرور على تسلسل أرقام قصير (" + short_sequence +
            ")، وهو من أشهر الإضافات التي يجربها المخترق.")

    if found_repeat:
        score -= 20
        add("red", "Contains repeated characters -> " + found_repeat,
            "تحتوي كلمة المرور على حروف مكررة (" + found_repeat + ").")

    for key in found_words:
        word = found_words[key]
        if word == found_name:
            continue
        label = WORDLISTS[key][1]
        points = WORDLISTS[key][2]
        score -= points
        add("red", "Contains " + label + " -> " + word,
            "تحتوي كلمة المرور على " + ARABIC_LABELS[key] + " (" + word + "). " + WHY[key])

    if found_keyboard:
        score -= 30
        add("red", "Arabic word typed on the English keyboard -> " + found_keyboard[0],
            "تحتوي كلمة المرور على كلمة عربية (" + found_keyboard[1] +
            ") مكتوبة بلوحة المفاتيح الإنجليزية، وهذا الأسلوب معروف لدى المخترقين.")

    if has_arabic:
        # what they meant to type if the keyboard was on English
        intended = ""
        for c in password:
            if c in ARABIC_KEYS:
                intended += ARABIC_KEYS[c]
            else:
                intended += c
        add("yellow", "Contains Arabic letters (keyboard may be set to Arabic) -> " + intended,
            "تحتوي كلمة المرور على حروف عربية؛ قد تكون لغة لوحة المفاتيح غير صحيحة. "
            "كثير من المواقع لا تقبلها وقد يُقفل الحساب بعد عدة محاولات. "
            "لو كانت اللوحة إنجليزية لكُتبت: " + intended)

    if found_phone:
        score -= 30
        number = found_phone.group()
        add("red", "Contains a Saudi phone number -> " + number,
            "تحتوي كلمة المرور على رقم جوال سعودي (" + number + ")، وهو متاح للآخرين غالبًا.")

    # fans love the year their club won something
    if "clubs" in found_words and found_year:
        club = club_aliases.get(found_words["clubs"])
        titles = clubs.get(club, {}).get("titles", {})
        if found_year in titles:
            score -= 10
            add("red", club + " won the " + titles[found_year] + " in " + found_year,
                "السنة " + found_year + " هي سنة فوز النادي ببطولة، ويستخدمها المشجعون كثيرًا.")

    # a personal word + a year is the first thing a hacker tries
    if found_year:
        word = None
        if found_name:
            word = found_name
        elif found_keyboard:
            word = found_keyboard[1]
        elif found_words:
            word = list(found_words.values())[0]
        if word:
            add("red", "A personal word + a year together = very easy to guess",
                "الجمع بين (" + word + ") والسنة (" + found_year + ") يجعل كلمة المرور سهلة التخمين جدًا؛ "
                "هذا أول نمط يجربه المخترق.")

    # ---------- data breaches ----------

    pwned = check_pwned(password)
    if pwned:
        score -= 50
        add("red", "Found in data breaches " + str(pwned) + " times",
            "ظهرت كلمة المرور هذه في تسريبات بيانات حقيقية " + f"{pwned:,}" +
            " مرة. يجب عدم استخدامها أبدًا، لأن المخترقين يجربون الكلمات المسربة أولًا.")
    elif pwned is None:
        add("yellow", "Breach check skipped (no internet)",
            "تعذّر فحص التسريبات لعدم توفر اتصال بالإنترنت.")

    # ---------- time to crack ----------

    # (part we found, how big the list a hacker would use is)
    known_parts = []
    if found_name:
        known_parts.append((found_name, 40000))
    for word in found_words.values():
        known_parts.append((word, 1000))
    if found_year:
        known_parts.append((found_year, 200))
    if found_phone:
        known_parts.append((found_phone.group(), 1000000))
    if found_sequence:
        known_parts.append((found_sequence, 100))
    if found_keyboard:
        known_parts.append((found_keyboard[0], 10000))
    crack_seconds = estimate_crack_seconds(password, known_parts, pwned)

    # ---------- blue notes (standards) ----------

    if length < 15:
        add("blue", "NIST: minimum 8, recommended 15 characters",
            "المعيار العالمي (NIST) يشترط 8 أحرف على الأقل ويوصي بـ15 حرفًا، "
            "وطول كلمة المرور الحالية " + str(length) + " أحرف.")

    if has_arabic:
        add("blue", "SAMA: bank accounts lock after 3 wrong attempts",
            "وفق إطار الأمن السيبراني للبنك المركزي السعودي (ساما)، يُقفل الحساب البنكي "
            "بعد 3 محاولات خاطئة، لذا قد تؤدي لغة لوحة المفاتيح الخاطئة إلى قفل الحساب.")

    if score < 0:
        score = 0

    if score >= 70:
        add("blue", "NCA: entities must set strong password policies",
            "تُلزم الهيئة الوطنية للأمن السيبراني الجهات بوضع سياسات قوية لكلمات المرور، "
            "وكلمة المرور هذه تتماشى مع هذا التوجه.")

    color, level = level_for(score)
    return {
        "score": score,
        "color": color,
        "level": level,
        "crack_time": human_time_ar(crack_seconds),
        "length": length,
        "findings": findings,
    }


# run it in the terminal: python hisn.py
if __name__ == "__main__":
    password = input("Enter your password: ")
    result = analyze(password)
    print("Your password has", result["length"], "characters")
    for f in result["findings"]:
        print("[" + f["severity"].upper() + "]", f["en"])
    print("Score:", result["score"], "/ 100", "(" + result["color"] + ")")
