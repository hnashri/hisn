# Hisn - a password checker that understands Arabic names and Arabizi and Hijri years
# by Hind Nashri

import csv
import json
import hashlib
import math
import re
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"


# names

def load_names():
    names = set()

    with open(DATA / "muslim_names.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["english_name"].strip().lower()
            if len(name) >= 3:
                names.add(name)
                # Saudis write oo as ou too (noora noura mansoor mansour)
                if "oo" in name:
                    names.add(name.replace("oo", "ou"))

    with open(DATA / "arabic_name_pairs.json", encoding="utf-8") as f:
        for name in json.load(f):
            name = name.strip().lower()
            if len(name) >= 3:
                names.add(name)

    return names


names = load_names()
print("Hisn loaded", len(names), "names")

# my names list has names from everywhere so some are normal English words
# (frost delta grace) so I need to know which ones are English words too
# (top English words from the zxcvbn project MIT license)
with open(DATA / "english_words.txt", encoding="utf-8") as f:
    english_words = set(f.read().split())


# turning A7med into ahmed

# people write Arabic letters with numbers like 7 = h and 3 = a (ع)
arabizi = {"2": "a", "3": "a", "5": "kh", "6": "t", "7": "h", "8": "q", "9": "s"}

# and swap letters with symbols like @ = a and 0 = o
leet = {"@": "a", "$": "s", "0": "o", "1": "i", "!": "i", "4": "a"}

# 3 (ع) and 2 (ء) don't always become a
# 3omar is omar and 3isa is eisa so I try other choices too
# ("" means the number just disappears)
arabizi_choices = [{}, {"3": "e", "2": "e"}, {"3": "o", "2": "o"}, {"3": "", "2": ""}]


def normalize_with_mask(text, choice=None):
    # returns the decoded text + a list that says which letters were decoded
    # (I need it later so a "name" made only of symbols doesn't count)
    # + a list that says where each letter was in the original password
    text = text.lower()
    out = []
    changed = []
    origin = []
    i = 0

    while i < len(text):
        # 2024 or 0551234567 are numbers not Arabizi so I skip them
        if text[i].isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            if j - i >= 2:
                out.append(" ")
                changed.append(False)
                origin.append(i)
                i = j
                continue

        ch = text[i]
        if choice and ch in choice:
            new = choice[ch]
        elif ch in leet:
            new = leet[ch]
        elif ch in arabizi:
            new = arabizi[ch]
        else:
            new = None

        if new is not None:
            for letter in new:
                out.append(letter)
                changed.append(True)
                origin.append(i)
        else:
            out.append(ch)
            changed.append(False)
            origin.append(i)
        i += 1

    return "".join(out), changed, origin


def normalize(text):
    decoded, changed, origin = normalize_with_mask(text)
    return decoded


def spelling_variants(word):
    # same Arabic name different English spelling:
    # sharif / shareef / shereef qahtani / gahtani hakami / hakamy
    variants = {word}

    swaps = [("ee", "i"), ("i", "ee"), ("oo", "u"), ("u", "oo"), ("ou", "u"),
             ("aa", "a"), ("q", "g"), ("q", "k"), ("a", "e")]
    for old, new in swaps:
        for v in list(variants):
            if old in v:
                variants.add(v.replace(old, new, 1))

    for v in list(variants):
        # hakami -> hakamy hakamee hakamie
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


# my word lists (data folder)

def load_wordlist(filename):
    words = set()
    with open(DATA / filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            word = normalize(line).strip()
            if filename in ("families.txt", "nicknames.txt", "cities.txt"):
                words.update(spelling_variants(word))
            else:
                words.add(word)
    return words


# list name: (file English label)
WORDLISTS = {
    "nicknames": ("nicknames.txt", "a nickname"),
    "families": ("families.txt", "a family name"),
    "religious": ("religious.txt", "a common religious phrase"),
    "cities": ("cities.txt", "a Saudi city"),
    "common": ("common_words.txt", "a very common password word"),
}

wordlists = {}
for key in WORDLISTS:
    filename = WORDLISTS[key][0]
    wordlists[key] = load_wordlist(filename)
    print("Hisn loaded", len(wordlists[key]), key)


# clubs (names nicknames title years)

def load_clubs():
    with open(DATA / "clubs.json", encoding="utf-8") as f:
        clubs = json.load(f)

    # alzaeem -> hilal alalami -> nassr
    aliases = {}
    for club in clubs:
        for name in clubs[club]["names"]:
            aliases[normalize(name).strip()] = club

    return clubs, aliases


clubs, club_aliases = load_clubs()
wordlists["clubs"] = set(club_aliases)
WORDLISTS["clubs"] = ("clubs.json", "a Saudi football club")
print("Hisn loaded", len(clubs), "clubs")


# Arabic words typed with the keyboard on English

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

# tashkeel and tatweel removed before converting
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

    # short letter-only keys look like normal English so they need 5+
    # with a symbol like ] or ; even 3-4 keys are enough (محمد = lpl])
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


# messages

ARABIC_LABELS = {
    "nicknames": "اسم تدليل",
    "families": "اسم عائلة",
    "religious": "عبارة دينية شائعة",
    "clubs": "اسم نادٍ رياضي",
    "cities": "اسم مدينة سعودية",
    "common": "كلمة شائعة جدًا في كلمات المرور",
}

# the reason shown after each warning
WHY = {
    "nicknames": "اسم التدليل يعرفه المقربون ويظهر في الحسابات، فيسهل على المخترق تخمينه.",
    "families": "اسم العائلة معروف ويظهر في الحسابات، فيسهل على المخترق تخمينه.",
    "religious": "العبارات الدينية يستخدمها كثيرون، فهي من أول ما يجربه المخترق.",
    "clubs": "أسماء الأندية وألقابها من أول ما يجربه المخترق، خصوصًا مع سنة بطولة.",
    "cities": "اسم المدينة مرتبط بالشخص، فيسهل على المخترق تخمينه.",
    "common": "هذه الكلمات أول ما يجربه المخترق، حتى لو استُبدلت بعض حروفها برموز.",
}


# data breaches (Have I Been Pwned)

def check_pwned(password):
    # I never send the password. I hash it with sha1 and send only the first 5
    # characters the site sends back all hashes that start with them and I
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


# time to crack

def human_time_ar(seconds):
    if seconds < 1:
        return "أقل من ثانية"

    # (how many of this unit make the next one singular plural for 3-10)
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


def estimate_guesses(password, known_parts, pwned):
    # how many guesses the hacker needs
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
    if any_char(password, "arabic"):
        charset += 36
    if charset < 10:
        charset = 10

    # a name or a year isn't guessed letter by letter the hacker picks it
    # from a list so it counts as one choice from that list
    random_length = len(password)
    guesses = 1
    for part, list_size in known_parts:
        random_length -= len(part)
        guesses *= list_size
    if random_length > 0:
        guesses *= charset ** random_length
    return guesses


# the time depends on how the hacker attacks
# online: the site slows them down (I assume 100 tries per hour)
# fast: they stole a database with a weak hash like MD5 (10 billion per second on GPUs)
# slow: the database uses a strong hash like bcrypt (10 thousand per second)
ATTACKS = {
    "online": 100 / 3600,
    "fast": 10_000_000_000,
    "slow": 10_000,
}


# small helpers

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
        if kind == "arabic" and "\u0600" <= c <= "\u06ff":
            return True
    return False


def whole_word(normalized, changed, origin, password, pos, size):
    # a name only counts if it is a whole word not a piece of a longer word
    # mango has "mang" inside but it is not a name
    # a capital letter starts a new word like AhmedAli
    # and a symbol next to it is fine like Sara@ (the @ is not part of the name)
    end = pos + size
    if pos > 0 and normalized[pos - 1].isalpha() and not changed[pos - 1]:
        if not password[origin[pos]].isupper():
            return False
    if end < len(normalized) and normalized[end].isalpha() and not changed[end]:
        if not password[origin[end]].isupper():
            return False
    return True


def valid_year(year):
    return 1950 <= year <= 2030 or 1370 <= year <= 1460


def find_date(password):
    # a full birth date like 01051426 (day month year) or 14260501
    # or a short one like 010526 (day month and the last 2 digits)
    for run in re.findall(r"\d{6,8}", password):
        if len(run) == 8:
            day, month, year = int(run[:2]), int(run[2:4]), int(run[4:])
            if 1 <= day <= 31 and 1 <= month <= 12 and valid_year(year):
                return run, run[4:]
            year, month, day = int(run[:4]), int(run[4:6]), int(run[6:])
            if 1 <= day <= 31 and 1 <= month <= 12 and valid_year(year):
                return run, run[:4]
        if len(run) == 6:
            day, month = int(run[:2]), int(run[2:4])
            if 1 <= day <= 31 and 1 <= month <= 12:
                return run, run[4:]
    return None


def score_from_seconds(seconds):
    # the score comes from the time to crack so they always agree
    # less than 1 second = 0 and about 30 thousand years (10^12 seconds) = 100
    # log10 counts the zeros so 1000 seconds = 3 and 10^12 seconds = 12
    if seconds < 1:
        return 0
    score = round(math.log10(seconds) / 12 * 100)
    if score > 100:
        score = 100
    return score


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


# the main check

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
    has_arabic = any_char(password, "arabic")

    if length < 8:
        add("red", "Too short (less than 8 characters)",
            "كلمة المرور قصيرة جدًا؛ حتى مع التحقق الثنائي لا يقبل المعيار العالمي (NIST) أقل من 8 أحرف.")

    # NIST cares about length more than mixing types
    # so I only show this tip when the password is not long
    # (Arabic letters have no capital letters so I skip them)
    missing = []
    if not has_upper:
        missing.append("حروف كبيرة")
    if not has_lower:
        missing.append("حروف صغيرة")
    if not has_digit:
        missing.append("أرقام")
    if not has_symbol:
        missing.append("رموز")
    if missing and length < 15 and not has_arabic:
        add("yellow", "Missing character types",
            "لا تحتوي كلمة المرور على: " + "، ".join(missing) +
            ". إضافتها تفيد، لكن زيادة الطول تفيد أكثر.")

    # decode A7med -> ahmed before searching
    normalized, changed, origin = normalize_with_mask(password)

    # names (the longest one wins)
    # a name only counts if at most 1 letter came from a symbol
    # otherwise random passwords like x9#Lm@Rt give fake names
    # and it has to be a whole word (mang inside mango is not a name)
    # (if 2 names fit I take the one with less decoded letters then the longer one
    # so Mansour@ gives mansour not mansoura)
    # I search every Arabizi choice (3 = a then e then o then nothing)
    found_name = None
    found_decoded = 0
    for choice in arabizi_choices:
        text, text_changed, text_origin = normalize_with_mask(password, choice)
        for n in names:
            if len(n) < 4:
                continue
            pos = text.find(n)
            if pos == -1:
                continue
            if not whole_word(text, text_changed, text_origin, password, pos, len(n)):
                continue
            # count decoded characters of the password not letters
            # (5 becomes kh but it is still 1 character)
            decoded = set()
            for k in range(pos, pos + len(n)):
                if text_changed[k]:
                    decoded.add(text_origin[k])
            # in 3omar the 3 is gone so it has no letter but it was still decoded
            start = text_origin[pos]
            if start > 0 and choice.get(password[start - 1].lower()) == "":
                decoded.add(start - 1)
            decoded_letters = len(decoded)
            if decoded_letters > 1:
                continue
            if found_name is None or decoded_letters < found_decoded:
                found_name = n
                found_decoded = decoded_letters
            elif decoded_letters == found_decoded and len(n) > len(found_name):
                found_name = n

    # a full birth date like 01051426
    found_date = find_date(password)

    # years (gregorian 1950-2030 hijri 1370-1460)
    found_year = None
    if found_date:
        found_year = found_date[1]
    else:
        for i in range(len(password) - 3):
            part = password[i:i + 4]
            if part.isdigit() and valid_year(int(part)):
                found_year = part

    # Saudi mobile number: 05xxxxxxxx 9665xxxxxxxx or 5xxxxxxxx
    # (people also write it with spaces or dashes like 055 246 8135)
    compact = re.sub(r"[\s-]", "", password)
    found_phone = re.search(r"(9665|05|5)\d{8}", compact)
    if found_phone and found_date and found_date[0] in found_phone.group():
        found_date = None
        found_year = None

    # 2 digits alone like Sara05 or 3bood@99 are often a year too
    short_year = None
    if not found_year:
        two = re.search(r"(?<!\d)\d\d(?!\d)", password)
        if two:
            short_year = two.group()

    # sequences like 1234 abcd qwerty
    sequences = ["0123456789", "abcdefghijklmnopqrstuvwxyz",
                 "qwertyuiop", "asdfghjkl", "zxcvbnm"]
    found_sequence = None
    for seq in sequences:
        for i in range(len(seq) - 3):
            chunk = seq[i:i + 4]
            backwards = chunk[::-1]
            if chunk in low or backwards in low:
                found_sequence = chunk
    # a sequence inside a date or a phone number is already counted there
    if found_sequence:
        if found_date and found_sequence in found_date[0]:
            found_sequence = None
        elif found_phone and found_sequence in found_phone.group():
            found_sequence = None

    # short ones like 123 or 987 (not inside a year like 2012)
    short_sequence = None
    if not found_sequence:
        text = low
        if found_year:
            text = text.replace(found_year, " ")
        if found_date:
            text = text.replace(found_date[0], " ")
        if found_phone:
            text = text.replace(found_phone.group(), " ")
        for i in range(8):
            chunk = "0123456789"[i:i + 3]
            if chunk in text:
                short_sequence = chunk
            elif chunk[::-1] in text:
                short_sequence = chunk[::-1]

    # the phone number already explains these digits
    if found_phone:
        if short_sequence and short_sequence in found_phone.group():
            short_sequence = None
        if short_year and short_year in found_phone.group():
            short_year = None

    # aaaa or 1111
    found_repeat = None
    for i in range(len(password) - 3):
        if password[i] * 4 == password[i:i + 4]:
            found_repeat = password[i:i + 4]

    # my lists: nicknames families clubs cities
    found_words = {}
    # (a whole word too like names so abha is not found inside kabhab)
    for key in wordlists:
        best = None
        for w in wordlists[key]:
            if len(w) < 3:
                continue
            pos = normalized.find(w)
            if pos == -1:
                continue
            if not whole_word(normalized, changed, origin, password, pos, len(w)):
                continue
            if best is None or len(w) > len(best):
                best = w
        if best:
            found_words[key] = best

    # hamdi is inside ghamdi so keep only ghamdi
    for key in list(found_words):
        word = found_words[key]
        for other in found_words.values():
            if other != word and word in other:
                del found_words[key]
                break

    # if the name is part of a family name/nickname we found that message is better
    if found_name:
        for w in found_words.values():
            if overlaps(normalized, found_name, w):
                found_name = None
                break

    # Arabic word typed on the English keyboard
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

    # warnings

    # a name that is also an English word (like frost) and a short year (like 82)
    # are only worth a warning when the password is weak
    # I check that after the score so here I skip them
    name_is_word = found_name is not None and found_name in english_words

    if found_name and not name_is_word:
        note = ""
        if found_decoded > 0:
            note = " حتى مع استبدال بعض الحروف بأرقام أو رموز، فهذه الحيلة معروفة."
        add("red", "Contains a common name -> " + found_name,
            "تحتوي كلمة المرور على اسم شائع (" + found_name + ")." + note +
            " الأسماء من أول ما يجربه المخترق، خصوصًا اسم صاحب الحساب أو أفراد عائلته.")

    if found_date:
        add("red", "Contains a full date -> " + found_date[0],
            "تحتوي كلمة المرور على تاريخ كامل (" + found_date[0] + "). "
            "تاريخ الميلاد من أول ما يجربه المخترق، لأنه يظهر غالبًا في الحسابات.")
    elif found_year:
        if 1370 <= int(found_year) <= 1460:
            kind = "هجرية"
        else:
            kind = "ميلادية"
        add("red", "Contains a year -> " + found_year,
            "تحتوي كلمة المرور على سنة " + kind + " (" + found_year + "). "
            "سنوات الميلاد والتخرج تظهر غالبًا في الحسابات، وهي من أول ما يُجرَّب عند التخمين.")


    if found_sequence:
        add("red", "Contains an easy sequence -> " + found_sequence,
            "تحتوي كلمة المرور على تسلسل سهل (" + found_sequence + ").")

    if short_sequence:
        add("yellow", "Contains a short number sequence -> " + short_sequence,
            "تحتوي كلمة المرور على تسلسل أرقام قصير (" + short_sequence +
            ")، وهو من أشهر الإضافات التي يجربها المخترق.")

    if found_repeat:
        add("red", "Contains repeated characters -> " + found_repeat,
            "تحتوي كلمة المرور على حروف مكررة (" + found_repeat + ").")

    for key in found_words:
        word = found_words[key]
        if word == found_name:
            continue
        label = WORDLISTS[key][1]
        add("red", "Contains " + label + " -> " + word,
            "تحتوي كلمة المرور على " + ARABIC_LABELS[key] + " (" + word + "). " + WHY[key])

    if found_keyboard:
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
        number = found_phone.group()
        add("red", "Contains a Saudi phone number -> " + number,
            "تحتوي كلمة المرور على رقم جوال سعودي (" + number + ")، وهو متاح للآخرين غالبًا.")

    # fans love the year their club won something
    title_year = False
    if "clubs" in found_words and found_year:
        club = club_aliases.get(found_words["clubs"])
        titles = clubs.get(club, {}).get("titles", {})
        if found_year in titles:
            title_year = True
            add("red", club + " won the " + titles[found_year] + " in " + found_year,
                "السنة " + found_year + " هي سنة فوز النادي ببطولة، ويستخدمها المشجعون كثيرًا.")

    # data breaches

    pwned = check_pwned(password)
    if pwned:
        add("red", "Found in data breaches " + str(pwned) + " times",
            "ظهرت كلمة المرور هذه في تسريبات بيانات حقيقية " + f"{pwned:,}" +
            " مرة. يجب عدم استخدامها أبدًا، لأن المخترقين يجربون الكلمات المسربة أولًا.")
    elif pwned is None:
        add("yellow", "Breach check skipped (no internet)",
            "تعذّر فحص التسريبات لعدم توفر اتصال بالإنترنت.")

    # time to crack

    # each part we found is one pick from a list so the hacker
    # tries the whole list instead of guessing letter by letter
    # (I use the real size of my lists)
    known_parts = []
    if found_name:
        known_parts.append((found_name, len(names)))
    for key in found_words:
        word = found_words[key]
        if word != found_name:
            known_parts.append((word, len(wordlists[key])))
    if found_date:
        # about 366 days in each of about 160 years (hijri and gregorian)
        known_parts.append((found_date[0], 366 * 160))
    elif found_year:
        if title_year:
            known_parts.append((found_year, 30))
        else:
            known_parts.append((found_year, 160))
    if found_phone:
        known_parts.append((found_phone.group(), 1000000))
    if found_sequence:
        known_parts.append((found_sequence, 100))
    if short_sequence:
        # 123 and 987 are some of the first endings a hacker adds
        known_parts.append((short_sequence, 20))
    if found_repeat:
        known_parts.append((found_repeat, 100))
    if found_keyboard:
        known_parts.append((found_keyboard[0], len(keyboard_names)))
    guesses = estimate_guesses(password, known_parts, pwned)
    crack_seconds = guesses / ATTACKS["fast"]

    # the score and the level both come from the time to crack
    # I use the fast attack because it is the worst case
    score = score_from_seconds(crack_seconds)

    if name_is_word and score < 40:
        add("yellow", "Contains a common name or English word -> " + found_name,
            "تحتوي كلمة المرور على اسم أو كلمة إنجليزية شائعة (" + found_name +
            ")، وهذه الكلمات موجودة في قوائم التخمين.")

    # a short year next to a personal word is a real pattern (Sara05)
    # but 82 at the end of a long strong passphrase is just a number
    personal = found_name or found_words or found_keyboard
    if short_year and (personal or score < 40):
        add("yellow", "Might be a short year -> " + short_year,
            "الرقمان (" + short_year + ") قد يكونان سنة مختصرة مثل 20" + short_year +
            " أو 19" + short_year + "، والمخترق يجرب هذا النمط كثيرًا.")

    # a personal word + a year is the first thing a hacker tries
    # (only when the password is weak because a long one hides it well)
    year_text = found_year or short_year
    if year_text and score < 40:
        word = None
        if found_name:
            word = found_name
        elif found_keyboard:
            word = found_keyboard[1]
        elif found_words:
            word = list(found_words.values())[0]
        if word:
            add("red", "A personal word + a year together = very easy to guess",
                "الجمع بين (" + word + ") والسنة (" + year_text + ") يجعل كلمة المرور سهلة التخمين جدًا؛ "
                "هذا أول نمط يجربه المخترق.")


    # blue notes (standards)

    if length < 15:
        add("blue", "NIST (2025): minimum 15 characters, or 8 with two-factor authentication",
            "المعيار العالمي (NIST SP 800-63B-4، 2025) يشترط 15 حرفًا على الأقل إذا كانت كلمة المرور "
            "وحدها تحمي الحساب، ويسمح بـ8 أحرف فقط مع التحقق الثنائي، "
            "وطول كلمة المرور الحالية " + str(length) + " أحرف.")

    if has_arabic:
        add("blue", "SAMA: organizations must revoke access after 3 wrong attempts",
            "يطلب إطار الأمن السيبراني للبنك المركزي السعودي (ساما) من الجهات وضع سياسة "
            "توقف الوصول بعد 3 محاولات خاطئة متتالية، لذا قد تؤدي لغة لوحة المفاتيح الخاطئة "
            "إلى إيقاف الحساب.")

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
        "crack_times": {
            "online": human_time_ar(guesses / ATTACKS["online"]),
            "fast": human_time_ar(crack_seconds),
            "slow": human_time_ar(guesses / ATTACKS["slow"]),
        },
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
