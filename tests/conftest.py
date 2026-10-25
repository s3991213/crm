import copy
import logging

import pytest

# mock_backend/main.py calls logging.basicConfig(filename="audit.log") on import.
# A root handler makes that a no-op, so tests don't write audit.log into the repo.
logging.getLogger().addHandler(logging.NullHandler())

import main  # noqa: E402
import staff_auth  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_backend():
    """Each test starts from the original mock records with nothing staged."""
    students = copy.deepcopy(main.STUDENTS)
    main.PENDING.clear()
    yield
    main.STUDENTS.clear()
    main.STUDENTS.update(students)
    main.PENDING.clear()


@pytest.fixture
def staff_file(tmp_path, monkeypatch):
    """Point staff_auth at a throwaway staff.json, with fast hashing."""
    path = tmp_path / "staff.json"
    monkeypatch.setattr(staff_auth, "STAFF_FILE", path)
    monkeypatch.setattr(staff_auth, "ITERATIONS", 1_000)
    return path


@pytest.fixture
def anyio_backend():
    return "asyncio"
