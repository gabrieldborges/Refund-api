# Pure unit (only cryptography), so we test the real handler, no mocks/fixtures needed.
from .password_handler import PasswordHandler


# encrypt_password must return a hash (string) different from the original password —
# i.e. the password is never stored in plain text.
def test_encrypt_password_returns_a_hash_different_from_the_plain_password():
    handler = PasswordHandler()
    hashed = handler.encrypt_password("mysecret123")

    assert isinstance(hashed, str)
    assert hashed != "mysecret123"


# check_password must recognize the correct password when compared against its hash.
def test_check_password_returns_true_for_the_correct_password():
    handler = PasswordHandler()
    hashed = handler.encrypt_password("mysecret123")

    assert handler.check_password("mysecret123", hashed) is True


# And it must reject a wrong password against that same hash.
def test_check_password_returns_false_for_the_wrong_password():
    handler = PasswordHandler()
    hashed = handler.encrypt_password("mysecret123")

    assert handler.check_password("wrongpassword", hashed) is False
