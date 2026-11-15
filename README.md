# Hisn | حصن

**A password checker that thinks like an Arab attacker.**

Most password checkers look at `A7med_1415` and say *strong*: it has upper and lower case letters, numbers and a symbol.
Any Arab attacker reads it as **Ahmed, born in 1415 AH** and guesses it in less than a second.

Hisn checks passwords the way an attacker in Saudi Arabia would guess them.

**Try it online:** [hisn-sa.streamlit.app](https://hisn-sa.streamlit.app) (it's a demo, so test a password similar to yours, not your real one)

---

## What Hisn detects

| | Example | What Hisn sees |
|---|---|---|
| Arabic names (35k+) | `Sara@2005` | name + year |
| Arabizi (7 = ح, 3 = ع ...) | `A7med`, `3bdullah`, `3omar` | Ahmed, Abdullah, Omar |
| Hijri and Gregorian years | `1426`, `2008`, `Sara05` | a Hijri year, a Gregorian year, a short year |
| Full birth dates | `01051426` | day + month + year |
| Nicknames | `3bood`, `Fahood`, `Lulu` | Saudi nicknames |
| Family names (many spellings) | `AlOtaibi`, `Gahtani` | family names |
| Saudi football clubs and nicknames | `AlZaeem2019` | Al-Hilal + a year it won a title |
| Saudi cities | `Jeddah#123` | a city + a short sequence |
| Religious phrases | `Bismillah2020` | a common phrase + a year |
| Arabic typed on the English keyboard | `hgsghl`, `lpl]` | السلام, محمد |
| Arabic letters by mistake | `شفثقف` | the keyboard was on Arabic, you meant `atert` |
| Saudi phone numbers | `0551234567` | a mobile number |
| Sequences and repeats | `qwerty`, `1234`, `aaaa` | easy patterns |
| Leaked passwords | `P@ssw0rd` | found in real data breaches |

For every finding Hisn explains **why** it is risky, in Arabic.

It also shows:
- an estimated time to crack, assuming the attacker tries name and year lists first
- a score from 0 to 100 that comes from the time to crack, so the two always agree
- notes from password standards (NIST, the National Cybersecurity Authority, SAMA)

## How the score works

1. Every part Hisn finds (a name, a year, a club...) counts as **one pick from a list**, using the real size of that list. A name is one guess out of 35k names, not 5 random letters.
2. The rest of the password is guessed character by character (English letters, Arabic letters, digits and symbols).
3. The time is shown for 3 attacks:
   - **online**, where the site limits tries (100 per hour)
   - **offline with a weak hash** like MD5 on GPUs (10 billion per second), the worst case
   - **offline with a strong hash** like bcrypt (10 thousand per second)
4. The score follows the worst case: less than 1 second is 0, about 30 thousand years is 100. Below 40 is weak, 70 and above is strong.

This is why a long passphrase like `purple-kettle-drift-mango` is strong even without capitals or digits, which matches NIST.

## Why Hisn exists

A 2018 study, [*Your Culture is in Your Password*](https://elmi.hbku.edu.qa/en/publications/your-culture-is-in-your-password-an-analysis-of-a-demographically/), analyzed a leak from a Middle Eastern bank and found that a popular password meter rated these passwords **stronger than they really were**, and that adding local context made it more accurate. Hisn is my attempt at that local context for Saudi users.

## Evaluation

An outside reviewer (another AI assistant, not me) wrote **101 test cases** for Hisn: Saudi style passwords that have a pattern, "trap" passwords that should not trigger anything, and edge cases. The expected answers are the reviewer's opinion, not a ground truth. All passwords are made up.

**Baseline (v0, before any fix):**

| | Result |
|---|---|
| Same strength level as expected | **72 of 101** |
| Found a pattern when there was one (lenient) | 68 of 74 |
| Found the **main** pattern, not just the year (strict) | about 58 of 74 |
| False alarms on the 27 traps | 9 (only notes, all 9 still scored strong) |

**Hisn vs [zxcvbn](https://github.com/dropbox/zxcvbn) on the same 101 cases:**

| | Hisn | zxcvbn |
|---|---|---|
| Same strength level as expected | **72** | 32 |
| Saudi pattern passwords rated **strong** | 6 of 74 | **53 of 74** |
| Trap passwords rated strong | 26 of 27 | 26 of 27 |

zxcvbn rates passwords like `A7mad_1446`, `AlHilal_2021`, `Bismillah_1441` and even the phone number `0557812463` as strong. Hisn rates 37 of those 53 as weak. Both tools agree on the trap passwords, so Hisn is not just calling everything weak.

What Hisn still misses: phone numbers with spaces or dashes, Arabizi without vowels (`3bd-7sn`), Arabizi phrases (`SbahAlkhair`), new nicknames (`Dadoosh`), and 3 letter names like `Ali` (skipped on purpose). It also gives a noisy "short year" note on some long passphrases.

**v1 (after 3 fixes, tested on the same 101 cases I had already seen):**

| | v0 | v1 (seen) |
|---|---|---|
| Same strength level as expected | 72 | 74 |
| False alarms on traps | 9 | 2 |
| Missed patterns | 6 | 8 |

The fixes: the short year note is only shown next to a personal word or on a weak password, names that are also English words (like `frost`) are only mentioned on weak passwords, and phone numbers can have spaces or dashes. Missed patterns went up because some phrases were only "found" through a short year before. These v1 numbers come from cases I studied while fixing, so they are **not** a fair test. The fair test will be a new set of cases from a different source, run once.

Run it yourself: `python tests/run_benchmark.py` and `python tests/compare_zxcvbn.py` (needs `pip install zxcvbn`). This version is tagged `v0-baseline`. Results after my fixes will be reported separately, on new cases I have not seen.

## Privacy

- Hisn does not save or log the password.
- The breach check uses **k-anonymity**: the password is hashed with SHA-1 and only the first 5 characters of the hash are sent to [Have I Been Pwned](https://haveibeenpwned.com/Passwords). The full password and the full hash are never sent to that site.
- In the online demo the check runs on the Streamlit server, so the password does leave your device (it is not saved). That is why the demo asks you to try a similar password, not your real one. Running Hisn on your own computer keeps everything local.
- No leaked password lists were used to build Hisn.

## Standards

What I found when I read the official documents:

- **NIST SP 800-63B-4 (2025)**: minimum 15 characters when the password is the only factor, 8 only with multi-factor authentication. Composition rules (forcing a mix of character types) must not be imposed, and no forced periodic changes.
- **NCA Essential Cybersecurity Controls (2-2-3-1)**: every organization must have a password policy (length, complexity, expiry, lockout) but the control does not set fixed numbers.
- **SAMA Cyber Security Framework (3.1.5)**: requires organizations to have a strong password policy, including revoking access after 3 consecutive wrong attempts.

So Hisn uses NIST for the numbers and explains the Saudi requirements as notes.

## Run it

The checker is plain Python. The interface is built with [Streamlit](https://streamlit.io), a ready-made Python framework for simple web apps.

```bash
pip install streamlit
python -m streamlit run app.py
```

Then open http://localhost:8501

Command line version:

```bash
python hisn.py
```

Tests:

```bash
python -m unittest discover -s tests
```

## Project files

```
hisn.py            the checker
app.py             the interface (Streamlit)
data/              names, nicknames, family names, clubs, cities ...
tests/             test cases
```

## Data sources

See [data/SOURCES.md](data/SOURCES.md). The name lists come from open datasets (CC0 and CC BY 4.0). Nicknames, family names, clubs, cities and phrases were written by hand.

## Known limitations

- The time to crack (and the score) is a rough estimate based on a simple attack model, not a statistical study.
- Some normal words are also names, like `sabah` (morning) or `jabal` (mountain).
- Very short names (3 letters like `ali`) are skipped to avoid false alarms.
- The names list is global, so it has names that are also English words. A list of common English words (from zxcvbn) keeps them quiet on strong passwords, but rare words like `aster` can still show up.
- A name has to be a whole word, so two names glued in lowercase (`ahmedali`) may be missed. `AhmedAli` works.
- Hisn has not been compared with other meters yet (planned, see below).

## Future ideas

- Learn how parts are usually ordered (name then symbol then year) from real data, using a probabilistic grammar (PCFG).
- Compare Hisn with [zxcvbn](https://github.com/dropbox/zxcvbn) on a set of Saudi style passwords I write myself.
- Support more Arab countries (clubs, cities and Arabizi styles from Egypt, the Gulf, the Maghreb).
- Grow the nickname and family name lists.
- Check passwords against an organization's own policy.

---

Made by **Hind Nashri**, IT student (Cybersecurity track), Saudi Arabia.
[LinkedIn](https://www.linkedin.com/in/hind-nashri-22a2a82b5/)

License: [MIT](LICENSE)
