"""Password policy, following NIST SP 800-63B.

- Length is what matters: 10 to 128 characters, any characters (spaces and emoji included).
- No composition rules ("one uppercase, one symbol..."): they make passwords more predictable.
- Refuse passwords that are easy to guess anyway: very common ones, the account's own email or
  name, a single repeated character, or an obvious sequence.
"""

import re

MIN_LENGTH = 10
MAX_LENGTH = 128

# A known word (email name, person's name) plus fewer extra characters than this is guessable.
_MIN_EXTRA = 6

# Passwords of 10+ characters that appear at the top of every leaked-password list.
COMMON = frozenset(
    {
        "1234567890",
        "0123456789",
        "12345678910",
        "123456789a",
        "1234567890a",
        "0987654321",
        "1111111111",
        "0000000000",
        "1122334455",
        "1234554321",
        "1q2w3e4r5t",
        "1qaz2wsx3edc",
        "qwertyuiop",
        "qwerty1234",
        "qwerty12345",
        "qwerty123456",
        "asdfghjkl1",
        "zxcvbnm123",
        "password12",
        "password123",
        "password1234",
        "passw0rd123",
        "p@ssw0rd123",
        "password!!",
        "iloveyou12",
        "iloveyou123",
        "abcdefghij",
        "abcd123456",
        "abc1234567",
        "a123456789",
        "letmein123",
        "welcome123",
        "welcome1234",
        "admin12345",
        "administrator",
        "changeme123",
        "football123",
        "baseball123",
        "princess123",
        "sunshine123",
        "starwars123",
        "dragon1234",
        "monkey12345",
        "superman123",
        "trustno1234",
        "whatever123",
        "computer123",
        "internet123",
        "contraseña",
        "contrasena",
        "contraseña123",
        "contrasena123",
        "teamo12345",
        "123456789123",
        "extracta123",
        "extracta1234",
        "qwertyqwerty",
        "passwordpassword",
        "aaaaaaaaaa",
    }
)

_SEQUENCES = ("0123456789", "abcdefghijklmnopqrstuvwxyz", "qwertyuiopasdfghjklzxcvbnm")


class WeakPasswordError(ValueError):
    """The password does not meet the policy; the message is safe to show."""


def _is_sequence(value: str) -> bool:
    """True when almost every character follows the previous one on a known sequence (in either
    direction, wrapping around): 1234567890123, zyxwvuts, qwertyuiop..."""
    steps = list(zip(value, value[1:], strict=False))
    if not steps:
        return False
    for sequence in _SEQUENCES:
        size = len(sequence)
        position = {char: index for index, char in enumerate(sequence)}
        forward = backward = 0
        for a, b in steps:
            if a in position and b in position:
                forward += (position[b] - position[a]) % size == 1
                backward += (position[a] - position[b]) % size == 1
        if max(forward, backward) >= 0.8 * len(steps):
            return True
    return False


def check(password: str, *, email: str, name: str | None = None) -> None:
    """Raise WeakPasswordError with a clear reason if the password is too weak."""
    password = password or ""
    if not MIN_LENGTH <= len(password) <= MAX_LENGTH:
        raise WeakPasswordError(f"Use a password between {MIN_LENGTH} and {MAX_LENGTH} characters.")

    lowered = password.strip().lower()
    compact = re.sub(r"[\s._-]", "", lowered)
    if lowered in COMMON or compact in COMMON:
        raise WeakPasswordError("This password is too common. Choose one that is harder to guess.")
    if len(set(compact)) <= 2:
        raise WeakPasswordError("Use more than one or two different characters.")
    if _is_sequence(compact):
        raise WeakPasswordError("Avoid simple sequences like 1234567890 or abcdefghij.")

    local_part = email.split("@", 1)[0].lower()
    if lowered == email.lower() or (
        len(local_part) >= 4 and local_part in lowered and len(lowered) - len(local_part) < _MIN_EXTRA
    ):
        raise WeakPasswordError("The password cannot be based on your email address.")
    for word in (name or "").lower().split():
        if len(word) >= 4 and word in lowered and len(lowered) - len(word) < _MIN_EXTRA:
            raise WeakPasswordError("The password cannot be based on your name.")
