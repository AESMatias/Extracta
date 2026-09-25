import pytest

from app import passwords


@pytest.mark.parametrize(
    ("password", "reason"),
    [
        ("short", "between"),
        ("x" * 129, "between"),
        ("password123", "too common"),
        ("Qwerty-1234", "too common"),  # separators and case do not help
        ("aaaaaaaaaaaaaa", "different characters"),
        ("abababababab", "different characters"),
        ("1234567890123", "sequences"),  # a longer run of the same sequence
        ("zyxwvutsrqpon", "sequences"),
        ("anaperez2026", "email"),
        ("AnaPerez@Example.com", "email"),
        ("qwertyuiopas", "sequences"),
        ("gonzalez!!", "name"),
    ],
)
def test_weak_passwords_are_refused(password: str, reason: str) -> None:
    with pytest.raises(passwords.WeakPasswordError, match=reason):
        passwords.check(password, email="anaperez@example.com", name="Ana Gonzalez")


@pytest.mark.parametrize(
    "password",
    ["correct horse battery", "Tres tristes tigres 42", "mi café favorito ☕", "q7!Kd9#rP2vL"],
)
def test_long_or_varied_passwords_are_accepted(password: str) -> None:
    passwords.check(password, email="anaperez@example.com", name="Ana Gonzalez")


def test_the_name_is_optional() -> None:
    passwords.check("correct horse battery", email="a@b.co")
