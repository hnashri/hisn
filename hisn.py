password = input("Enter your password: ")
length = len(password)
print("Your password has", length, "characters")
if length < 8:
    print("Weak: too short")
elif length < 12:
    print("Medium: okay length")
else:
    print("Strong length")
has_upper = any(c.isupper() for c in password)
has_lower = any(c.islower() for c in password)
has_digit = any(c.isdigit() for c in password)
has_symbol = any(not c.isalnum() for c in password)

print("Uppercase:", has_upper)
print("Lowercase:", has_lower)
print("Digits:", has_digit)
print("Symbols:", has_symbol)