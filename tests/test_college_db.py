"""college_db/: the synthetic college database, and importing it into the assistant's crm.db."""

import sqlite3
from datetime import date

import pytest

from backend.source_import import import_students, student_rows
from backend.store import EDITABLE, Store
from college_db.generate import Generator, main, to_sql, write_sqlite

TODAY = date(2026, 10, 25)


@pytest.fixture(scope="module")
def college(tmp_path_factory):
    path = tmp_path_factory.mktemp("college") / "college.db"
    write_sqlite(to_sql(Generator(120, seed=1, today=TODAY).run()), path)
    db = sqlite3.connect(path)
    yield db
    db.close()


def one(db, sql):
    return db.execute(sql).fetchone()[0]


def test_every_table_is_filled_and_consistent(college):
    assert one(college, "select count(*) from students") == 120
    for table in ("agents", "courses", "enrolments", "visas", "health_cover", "english_tests", "education_history",
                  "fee_instalments", "contact_notes"):
        assert one(college, f"select count(*) from {table}") > 0, table
    assert college.execute("pragma foreign_key_check").fetchall() == []
    assert one(college, "select count(distinct given_name || ' ' || family_name) from students") == 120


def test_dates_make_sense(college):
    assert one(college, "select count(*) from contact_notes where noted_on > '2026-10-25'") == 0
    assert one(college, "select count(*) from enrolments where offer_date > start_date") == 0
    assert one(college, "select count(*) from enrolments where expected_end_date <= start_date") == 0
    assert one(college, "select count(*) from visas where granted_on < lodged_on") == 0
    assert one(college, "select count(*) from fee_instalments where amount_paid > amount") == 0


def test_only_international_students_have_visas_and_passports(college):
    assert one(college, "select count(*) from students where is_international = 0 and passport_number is not null") == 0
    assert one(college, "select count(*) from visas v join students s on s.id = v.student_id "
                        "where s.is_international = 0") == 0


def test_planted_instructions_are_in_the_notes(college):
    assert one(college, "select count(*) from contact_notes where note like '%ignore all previous instructions%'") == 1


def test_same_seed_same_data():
    a = Generator(30, seed=5, today=TODAY).run()
    b = Generator(30, seed=5, today=TODAY).run()
    assert a == b
    assert a != Generator(30, seed=6, today=TODAY).run()


def test_import_maps_each_student_to_one_record(college):
    store = Store(":memory:", today=lambda: TODAY)
    assert import_students(college, store, today=TODAY) == 120
    rows = store.all_students()
    assert {r["status"] for r in rows} <= set(EDITABLE["status"])
    assert {r["payment_status"] for r in rows} <= set(EDITABLE["payment_status"])
    assert all(r["history"] and r["last_contact"] <= "2026-10-25" for r in rows)
    with pytest.raises(Exception):  # never loads over existing records
        import_students(college, store, today=TODAY)


def test_payment_status_follows_the_instalments(college):
    rows = {r["id"]: r for r in student_rows(college, TODAY)}
    unpaid = {sid for (sid,) in college.execute(
        "select e.student_id from fee_instalments f join enrolments e on e.id = f.enrolment_id "
        "where f.due_date <= '2026-10-25' and f.amount_paid = 0")}
    part_paid = {sid for (sid,) in college.execute(
        "select e.student_id from fee_instalments f join enrolments e on e.id = f.enrolment_id "
        "where f.due_date <= '2026-10-25' and f.amount_paid > 0 and f.amount_paid < f.amount")}
    assert unpaid and part_paid
    for sid, r in rows.items():
        expected = "Overdue" if sid in unpaid else "Partial" if sid in part_paid else "Paid"
        assert r["payment_status"] == expected, r["name"]


def test_command_line_builds_both_databases(tmp_path, capsys):
    main(["--students", "20", "--today", "2026-10-25", "--out", str(tmp_path), "--crm-db", str(tmp_path / "crm.db")])
    assert (tmp_path / "college.sql").read_text().startswith("-- A college's student database")
    assert len(Store(tmp_path / "crm.db").all_students()) == 20
    with pytest.raises(SystemExit):  # won't overwrite an existing database
        main(["--students", "20", "--out", str(tmp_path), "--crm-db", str(tmp_path / "crm.db")])
