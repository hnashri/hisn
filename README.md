# Hisn | حصن

**A password checker that thinks like an Arab attacker.**

Most password checkers look at `A7med_1415` and say *strong*: it has upper and lower case letters, numbers and a symbol.
Any Arab attacker reads it as **Ahmed, born in 1415 AH** and guesses it in less than a second.

Hisn checks passwords the way an attacker in Saudi Arabia would guess them.

---

## What Hisn detects

| | Example | What Hisn sees |
|---|---|---|
| Arabic names (35k+) | `Sara@2005` | name + year |
| Arabizi (7 = ح, 3 = ع ...) | `A7med`, `3bdullah` | Ahmed, Abdullah |
| Hijri and Gregorian years | `1426`, `2008` | a Hijri year, a Gregorian year |
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
- a score from 0 to 100 (green, yellow, red)
- an estimated time to crack, assuming the attacker tries name and year lists first
- notes from password standards (NIST, the National Cybersecurity Authority, SAMA)

## Privacy

- Hisn does not save or log the password.
- The breach check uses **k-anonymity**: the password is hashed with SHA-1 and only the first 5 characters of the hash are sent to [Have I Been Pwned](https://haveibeenpwned.com/Passwords). The full password and the full hash never leave the computer.
- No leaked password lists were used to build Hisn.

## Standards

What I found when I read the official documents:

- **NIST SP 800-63B**: minimum 8 characters, 15 recommended, no forced character mixing, no forced periodic changes.
- **NCA Essential Cybersecurity Controls (2-2-3-1)**: every organization must have a password policy (length, complexity, expiry, lockout) but the control does not set fixed numbers.
- **SAMA Cyber Security Framework (3.1.5)**: requires a strong password policy and locks access after 3 wrong attempts.

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

- The score weights come from reasoning, not from a statistical study.
- Some normal words are also names, like `sabah` (morning) or `jabal` (mountain).
- Very short names (3 letters like `ali`) are skipped to avoid false alarms.
- The time to crack is a rough estimate.

## Future ideas

- Support more Arab countries (clubs, cities and Arabizi styles from Egypt, the Gulf, the Maghreb).
- Grow the nickname and family name lists.
- Check passwords against an organization's own policy.

---

Made by **Hind Nashri**, IT student (Cybersecurity track), Saudi Arabia.
[LinkedIn](https://www.linkedin.com/in/hind-nashri-22a2a82b5/)
