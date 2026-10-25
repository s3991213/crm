import staff_auth


def add(username="priya", name="Priya Shah", password="temp-pass-1", must_change=True):
    staff = staff_auth.load_staff()
    staff[username] = {"name": name, "password_hash": staff_auth.hash_password(password), "must_change": must_change}
    staff_auth.save_staff(staff)


def test_hash_is_salted(staff_file):
    assert staff_auth.hash_password("same-password") != staff_auth.hash_password("same-password")
    assert "same-password" not in staff_auth.hash_password("same-password")


def test_verify(staff_file):
    add()
    assert staff_auth.verify("priya", "temp-pass-1") == "Priya Shah"
    assert staff_auth.verify("  PRIYA ", "temp-pass-1") == "Priya Shah"
    assert staff_auth.verify("priya", "wrong-pass") is None
    assert staff_auth.verify("nobody", "temp-pass-1") is None


def test_verify_with_no_staff_file(staff_file):
    assert staff_auth.verify("priya", "temp-pass-1") is None


def test_corrupt_hash_never_verifies(staff_file):
    staff_auth.save_staff({"priya": {"name": "Priya Shah", "password_hash": "garbage", "must_change": False}})
    assert staff_auth.verify("priya", "garbage") is None


def test_forced_first_change(staff_file):
    add()
    assert staff_auth.must_change("priya")
    assert staff_auth.change_password("priya", None, "my-own-pass", "my-own-pass") is None
    assert not staff_auth.must_change("priya")
    assert staff_auth.verify("priya", "my-own-pass") == "Priya Shah"
    assert staff_auth.verify("priya", "temp-pass-1") is None


def test_voluntary_change_needs_current_password(staff_file):
    add(must_change=False)
    assert "current password" in staff_auth.change_password("priya", "wrong", "new-pass-123", "new-pass-123")
    assert staff_auth.change_password("priya", "temp-pass-1", "new-pass-123", "new-pass-123") is None


def test_change_password_rules(staff_file):
    add(must_change=False)
    assert "8 characters" in staff_auth.change_password("priya", "temp-pass-1", "short", "short")
    assert "match" in staff_auth.change_password("priya", "temp-pass-1", "new-pass-123", "new-pass-124")
    assert "different" in staff_auth.change_password("priya", "temp-pass-1", "temp-pass-1", "temp-pass-1")
    assert "couldn't find" in staff_auth.change_password("nobody", None, "new-pass-123", "new-pass-123")
    assert staff_auth.verify("priya", "temp-pass-1") == "Priya Shah"
