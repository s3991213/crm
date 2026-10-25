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


def test_set_staff_and_remove(staff_file):
    staff_auth.set_staff(" Priya ", "Priya Shah", "temp-pass-1")
    assert staff_auth.verify("priya", "temp-pass-1") == "Priya Shah"
    assert staff_auth.must_change("priya")
    assert staff_auth.remove_staff("priya")
    assert staff_auth.verify("priya", "temp-pass-1") is None
    assert not staff_auth.remove_staff("priya")


def test_session_stays_valid_until_something_changes(staff_file):
    staff_auth.set_staff("priya", "Priya Shah", "temp-pass-1")
    version = staff_auth.session_version("priya")
    assert staff_auth.is_current("priya", version)
    assert staff_auth.is_current("PRIYA", version)


def test_removed_login_ends_sessions(staff_file):
    staff_auth.set_staff("priya", "Priya Shah", "temp-pass-1")
    version = staff_auth.session_version("priya")
    staff_auth.remove_staff("priya")
    assert staff_auth.session_version("priya") is None
    assert not staff_auth.is_current("priya", version)


def test_reset_ends_old_sessions(staff_file):
    staff_auth.set_staff("priya", "Priya Shah", "temp-pass-1")
    old = staff_auth.session_version("priya")
    staff_auth.set_staff("priya", "Priya Shah", "temp-pass-2")
    assert not staff_auth.is_current("priya", old)


def test_removed_then_re_added_login_ends_old_sessions(staff_file):
    staff_auth.set_staff("priya", "Priya Shah", "temp-pass-1")
    old = staff_auth.session_version("priya")
    staff_auth.remove_staff("priya")
    staff_auth.set_staff("priya", "Priya Shah", "temp-pass-2")
    assert not staff_auth.is_current("priya", old)


def test_password_change_ends_other_sessions(staff_file):
    staff_auth.set_staff("priya", "Priya Shah", "temp-pass-1")
    old = staff_auth.session_version("priya")
    assert staff_auth.change_password("priya", None, "my-own-pass", "my-own-pass") is None
    assert not staff_auth.is_current("priya", old)
    assert staff_auth.is_current("priya", staff_auth.session_version("priya"))


def test_failed_password_change_keeps_sessions(staff_file):
    staff_auth.set_staff("priya", "Priya Shah", "temp-pass-1")
    version = staff_auth.session_version("priya")
    staff_auth.change_password("priya", None, "short", "short")
    assert staff_auth.is_current("priya", version)


def test_records_without_version_still_work(staff_file):
    add(must_change=False)  # written the old way, with no "version" field
    assert staff_auth.is_current("priya", 0)
    assert not staff_auth.is_current("priya", None)  # sessions from before versions existed


def test_staff_file_is_private(staff_file):
    add()
    assert staff_file.stat().st_mode & 0o777 == 0o600


def test_failed_write_leaves_file_intact(staff_file, monkeypatch):
    add()
    before = staff_file.read_text()

    def crash(*args):
        raise OSError("disk full")
    monkeypatch.setattr(staff_auth.os, "replace", crash)
    try:
        staff_auth.set_staff("liam", "Liam Nguyen", "temp-pass-2")
    except OSError:
        pass
    assert staff_file.read_text() == before
    assert [p.name for p in staff_file.parent.iterdir()] == ["staff.json"]
