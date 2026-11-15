import csv
import json
import hashlib
import re
import urllib.request
from pathlib import Path

# load data
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
    # changed = which letters came from a number or symbol
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

# arabic names for each list
ARABIC_LABELS = {
    "nicknames": "اسم تدليل",
    "tribes": "اسم قبيلة أو عائلة",
    "religious": "عبارة دينية شائعة",
    "clubs": "اسم نادٍ رياضي",
    "cities": "اسم مدينة سعودية",
}

def check_pwned(password):
    # k-anonymity: only the first 5 chars of the sha1 hash are sent
    # returns None when there's no internet
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    request = urllib.request.Request(
        "https://api.pwnedpasswords.com/range/" + prefix,
        headers={"User-Agent": "Hisn-password-checker", "Add-Padding": "true"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            for line in response.read().decode("utf-8").splitlines():
                hash_suffix, count = line.split(":")
                if hash_suffix == suffix:
                    return int(count)
        return 0
    except Exception:
        return None


def human_time_ar(seconds):
    if seconds < 1:
        return "أقل من ثانية"
    # (size, singular, plural for 3-10)
    units = [(60, "ثانية", "ثوانٍ"), (60, "دقيقة", "دقائق"), (24, "ساعة", "ساعات"),
             (30, "يوم", "أيام"), (12, "شهر", "أشهر"), (100, "سنة", "سنوات")]
    value = seconds
    for size, singular, plural in units:
        if value < size:
            n = int(value)
            return f"{n} {plural if 3 <= n <= 10 else singular}"
        value /= size
    return "أكثر من 100 سنة" if value < 10 else "قرون"


def estimate_crack_seconds(password, known_parts, pwned):
    # offline attack, 10 billion guesses per second
    # words/years we found count as one pick from a list, not random letters
    if pwned:
        return 0
    charset = 0
    if any(c.islower() for c in password): charset += 26
    if any(c.isupper() for c in password): charset += 26
    if any(c.isdigit() for c in password): charset += 10
    if any(not c.isalnum() for c in password): charset += 33
    charset = max(charset, 10)

    random_length = len(password)
    guesses = 1
    for part, list_size in known_parts:
        random_length -= len(part)
        guesses *= list_size
    guesses *= charset ** max(random_length, 0)
    return guesses / 10_000_000_000


# reason shown after each warning
WHY = {
    "nicknames": "اسم التدليل يعرفه المقربون ويظهر في الحسابات، فيسهل على المخترق تخمينه.",
    "tribes": "اسم العائلة أو القبيلة معروف ويظهر في الحسابات، فيسهل على المخترق تخمينه.",
    "religious": "العبارات الدينية يستخدمها كثيرون، فهي من أول ما يجربه المخترق.",
    "clubs": "أسماء الأندية وألقابها من أول ما يجربه المخترق، خصوصًا مع سنة بطولة.",
    "cities": "اسم المدينة مرتبط بالشخص، فيسهل على المخترق تخمينه.",
}


def level_for(score):
    if score >= 70:
        return "green", "قوية"
    if score >= 40:
        return "yellow", "متوسطة"
    return "red", "ضعيفة"


def analyze(password):

    findings = []   # each one: severity, English message, Arabic message

    def add(severity, en, ar):
        findings.append({"severity": severity, "en": en, "ar": ar})

    length = len(password)

    # character types
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)

    # score
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

    # normalize (decode Arabizi and leetspeak)
    normalized, changed = normalize_with_mask(password)

    # search for names (keep the longest match)
    # a name only counts if at most 1 of its letters came from a decoded symbol
    found_name = None
    for n in names:
        if len(n) < 4:
            continue
        pos = normalized.find(n)
        if pos != -1 and sum(changed[pos:pos + len(n)]) <= 1:
            if found_name is None or len(n) > len(found_name):
                found_name = n

    # search for years (on the original password)
    found_year = None
    for i in range(len(password) - 3):
        part = password[i:i+4]
        if part.isdigit():
            year = int(part)
            if 1950 <= year <= 2030 or 1370 <= year <= 1460:
                found_year = part

    # search for sequences
    sequences = ["0123456789", "abcdefghijklmnopqrstuvwxyz",
                 "qwertyuiop", "asdfghjkl", "zxcvbnm"]
    found_sequence = None
    low = password.lower()
    for seq in sequences:
        for i in range(len(seq) - 3):
            chunk = seq[i:i+4]
            if chunk in low or chunk[::-1] in low:
                found_sequence = chunk

    # search for repeated characters
    found_repeat = None
    for i in range(len(password) - 3):
        if password[i] * 4 == password[i:i+4]:
            found_repeat = password[i:i+4]

    # search in the Saudi wordlists
    found_words = {}
    for key, words in wordlists.items():
        best = None
        for w in words:
            if len(w) >= 3 and w in normalized:
                if best is None or len(w) > len(best):
                    best = w
        if best:
            found_words[key] = best

    # if the name is part of a tribe/nickname/city we found, use the more specific one
    def overlaps(a, b):
        i, j = normalized.find(a), normalized.find(b)
        return i < j + len(b) and j < i + len(a)

    if found_name and any(overlaps(found_name, w) for w in found_words.values()):
        found_name = None

    # Arabic names typed with the keyboard on English
    found_keyboard = None
    for keys, arabic in keyboard_names.items():
        if keys in low:
            if found_keyboard is None or len(keys) > len(found_keyboard[0]):
                found_keyboard = (keys, arabic)
    # ignore it if it's inside a word we already found (hali in madkhali)
    if found_keyboard:
        known = list(found_words.values()) + ([found_name] if found_name else [])
        if any(found_keyboard[0] in w for w in known):
            found_keyboard = None

    # Arabic letters (keyboard left on Arabic)
    has_arabic = any("؀" <= c <= "ۿ" for c in password)

    # Saudi phone numbers
    found_phone = re.search(r"(9665|05|5)\d{8}", password)

    # warnings
    if found_name:
        score -= 30
        pos = normalized.find(found_name)
        disguised = any(changed[pos:pos + len(found_name)])
        note = " حتى مع استبدال بعض الحروف بأرقام أو رموز، فهذه الحيلة معروفة." if disguised else ""
        add("red", "Contains a common name -> " + found_name,
            "تحتوي كلمة المرور على اسم شائع (" + found_name + ")." + note +
            " الأسماء من أول ما يجربه المخترق، خصوصًا اسم صاحب الحساب أو أفراد عائلته.")
    if found_year:
        score -= 20
        kind = "هجرية" if 1370 <= int(found_year) <= 1460 else "ميلادية"
        add("red", "Contains a year -> " + found_year,
            "تحتوي كلمة المرور على سنة " + kind + " (" + found_year + "). "
            "سنوات الميلاد والتخرج تظهر غالبًا في الحسابات، وهي من أول ما يُجرَّب عند التخمين.")
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
            "تحتوي كلمة المرور على " + ARABIC_LABELS[key] + " (" + word + "). " + WHY[key])
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
        word = found_name or (found_keyboard[1] if found_keyboard else None) or list(found_words.values())[0]
        add("red", "A personal word + a year together = very easy to guess",
            "الجمع بين (" + word + ") والسنة (" + found_year + ") يجعل كلمة المرور سهلة التخمين جدًا؛ "
            "هذا أول نمط يجربه المخترق.")

    # data breach check (Have I Been Pwned)
    pwned = check_pwned(password)
    if pwned:
        score -= 50
        add("red", "Found in data breaches " + str(pwned) + " times",
            "ظهرت كلمة المرور هذه في تسريبات بيانات حقيقية " + f"{pwned:,}" +
            " مرة. يجب عدم استخدامها أبدًا، لأن المخترقين يجربون الكلمات المسربة أولًا.")
    elif pwned is None:
        add("yellow", "Breach check skipped (no internet)",
            "تعذّر فحص التسريبات لعدم توفر اتصال بالإنترنت.")

    # time to crack
    known_parts = []
    if found_name: known_parts.append((found_name, 40_000))
    for word in found_words.values(): known_parts.append((word, 1_000))
    if found_year: known_parts.append((found_year, 200))
    if found_phone: known_parts.append((found_phone.group(), 1_000_000))
    if found_sequence: known_parts.append((found_sequence, 100))
    if found_keyboard: known_parts.append((found_keyboard[0], 10_000))
    crack_seconds = estimate_crack_seconds(password, known_parts, pwned)

    # blue info: standards that relate to this password
    if length < 15:
        add("blue", "NIST: minimum 8, recommended 15 characters",
            "المعيار العالمي (NIST) يشترط 8 أحرف على الأقل ويوصي بـ15 حرفًا، "
            "وطول كلمة المرور الحالية " + str(length) + " أحرف.")
    if has_arabic:
        add("blue", "SAMA: bank accounts lock after 3 wrong attempts",
            "وفق إطار الأمن السيبراني للبنك المركزي السعودي (ساما)، يُقفل الحساب البنكي "
            "بعد 3 محاولات خاطئة، لذا قد تؤدي لغة لوحة المفاتيح الخاطئة إلى قفل الحساب.")

    # final score
    score = max(score, 0)
    color, level_ar = level_for(score)
    if score >= 70:
        findings.append({"severity": "blue", "en": "NCA: entities must set strong password policies",
            "ar": "تُلزم الهيئة الوطنية للأمن السيبراني الجهات بوضع سياسات قوية لكلمات المرور، "
                  "وكلمة المرور هذه تتماشى مع هذا التوجه."})
    return {"score": score, "color": color, "level": level_ar,
            "crack_time": human_time_ar(crack_seconds),
            "length": length, "findings": findings}


# command line mode
if __name__ == "__main__":
    password = input("Enter your password: ")
    result = analyze(password)
    print("Your password has", result["length"], "characters")
    for f in result["findings"]:
        print("[" + f["severity"].upper() + "]", f["en"])
    print("Score:", result["score"], "/ 100", "(" + result["color"] + ")")
