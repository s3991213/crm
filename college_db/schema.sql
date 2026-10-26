-- A college's student database: the kind of system the CRM Assistant will read from.
--
-- Modelled on an Australian CRICOS-registered college (vocational and English courses) that
-- recruits international students through education agents. The fields follow what such a
-- college has to keep: Confirmation of Enrolment (CoE) details reported to PRISMS, visa and
-- health cover (OSHC), attendance and course progress (ESOS National Code, Standard 8), the
-- Unique Student Identifier (USI) for vocational students, fees, and staff contact notes.
--
-- Runs unchanged on MySQL 8 and SQLite. All data made by college_db/generate.py is synthetic.

DROP TABLE IF EXISTS enquiry_notes;
DROP TABLE IF EXISTS enquiries;
DROP TABLE IF EXISTS contact_notes;
DROP TABLE IF EXISTS fee_instalments;
DROP TABLE IF EXISTS health_cover;
DROP TABLE IF EXISTS attendance_weeks;
DROP TABLE IF EXISTS english_tests;
DROP TABLE IF EXISTS education_history;
DROP TABLE IF EXISTS visas;
DROP TABLE IF EXISTS enrolments;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS agents;

-- Education agencies that refer students, paid a commission on tuition.
CREATE TABLE agents (
    id               INTEGER PRIMARY KEY,
    agency_name      VARCHAR(120) NOT NULL,
    contact_name     VARCHAR(120),
    email            VARCHAR(160),
    phone            VARCHAR(30),
    country          VARCHAR(60)  NOT NULL,
    commission_rate  DECIMAL(5,2) NOT NULL,            -- percent of tuition
    agreement_expiry DATE,
    status           VARCHAR(20)  NOT NULL CHECK (status IN ('Active', 'Suspended', 'Ended'))
);

CREATE TABLE courses (
    id             INTEGER PRIMARY KEY,
    national_code  VARCHAR(12)   NOT NULL,             -- training.gov.au code; college code for English courses
    cricos_code    CHAR(7)       NOT NULL,
    name           VARCHAR(160)  NOT NULL,
    level          VARCHAR(40)   NOT NULL,
    duration_weeks INTEGER       NOT NULL,
    tuition_fee    DECIMAL(10,2) NOT NULL,
    material_fee   DECIMAL(10,2) NOT NULL DEFAULT 0
);

CREATE TABLE students (
    id                             INTEGER PRIMARY KEY,
    student_number                 VARCHAR(10)  NOT NULL UNIQUE,
    given_name                     VARCHAR(60)  NOT NULL,
    family_name                    VARCHAR(60)  NOT NULL,
    preferred_name                 VARCHAR(60),
    gender                         CHAR(1)      CHECK (gender IN ('F', 'M', 'X')),
    date_of_birth                  DATE         NOT NULL,
    email                          VARCHAR(160) NOT NULL UNIQUE,
    phone                          VARCHAR(30),
    is_international               BOOLEAN      NOT NULL,
    nationality                    VARCHAR(60)  NOT NULL,
    country_of_birth               VARCHAR(60)  NOT NULL,
    main_language                  VARCHAR(40),
    passport_number                VARCHAR(20),         -- international students only
    passport_expiry                DATE,
    usi                            CHAR(10),            -- vocational students only
    address_line                   VARCHAR(120),        -- address in Australia
    suburb                         VARCHAR(60),
    state                          VARCHAR(3),
    postcode                       CHAR(4),
    emergency_contact_name         VARCHAR(120),
    emergency_contact_relationship VARCHAR(30),
    emergency_contact_phone        VARCHAR(30),
    agent_id                       INTEGER,             -- the agency that referred them, if any
    created_on                     DATE         NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents (id)
);

-- One row per course a student enrols in; a pathway student has an English course, then a diploma.
-- status uses the CRM Assistant's own values.
CREATE TABLE enrolments (
    id                INTEGER PRIMARY KEY,
    student_id        INTEGER     NOT NULL,
    course_id         INTEGER     NOT NULL,
    coe_number        VARCHAR(20),                      -- international students only
    offer_date        DATE        NOT NULL,
    start_date        DATE        NOT NULL,
    expected_end_date DATE        NOT NULL,
    status            VARCHAR(20) NOT NULL
        CHECK (status IN ('Active', 'Visa pending', 'Deferred', 'Withdrawn', 'Completed')),
    status_changed_on DATE,
    deferred_until    DATE,
    attendance_pct    INTEGER     NOT NULL CHECK (attendance_pct BETWEEN 0 AND 100),
    course_progress   VARCHAR(20) NOT NULL CHECK (course_progress IN ('Satisfactory', 'At risk', 'Not satisfactory')),
    counsellor        VARCHAR(60),                      -- staff member looking after the student
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (course_id) REFERENCES courses (id)
);

-- Hours attended each week (Standard 8: attendance is monitored, and students below 80% are contacted).
CREATE TABLE attendance_weeks (
    id              INTEGER PRIMARY KEY,
    enrolment_id    INTEGER NOT NULL,
    week_start      DATE    NOT NULL,                   -- a Monday
    scheduled_hours INTEGER NOT NULL,                   -- 20 a week for student-visa courses
    attended_hours  INTEGER NOT NULL CHECK (attended_hours >= 0),
    FOREIGN KEY (enrolment_id) REFERENCES enrolments (id)
);

CREATE TABLE visas (
    id           INTEGER PRIMARY KEY,
    student_id   INTEGER     NOT NULL,
    subclass     VARCHAR(10) NOT NULL,                  -- 500 is the student visa
    grant_number VARCHAR(20),
    status       VARCHAR(20) NOT NULL CHECK (status IN ('Lodged', 'Granted', 'Refused', 'Expired')),
    lodged_on    DATE        NOT NULL,
    granted_on   DATE,
    expiry_date  DATE,
    FOREIGN KEY (student_id) REFERENCES students (id)
);

-- Overseas Student Health Cover, required for the whole visa.
CREATE TABLE health_cover (
    id            INTEGER PRIMARY KEY,
    student_id    INTEGER     NOT NULL,
    provider      VARCHAR(40) NOT NULL,
    policy_number VARCHAR(20) NOT NULL,
    cover_type    VARCHAR(10) NOT NULL CHECK (cover_type IN ('Single', 'Couple', 'Family')),
    start_date    DATE        NOT NULL,
    end_date      DATE        NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id)
);

CREATE TABLE english_tests (
    id            INTEGER PRIMARY KEY,
    student_id    INTEGER      NOT NULL,
    test_type     VARCHAR(30)  NOT NULL,
    overall_score DECIMAL(5,1) NOT NULL,
    test_date     DATE         NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id)
);

CREATE TABLE education_history (
    id             INTEGER PRIMARY KEY,
    student_id     INTEGER      NOT NULL,
    qualification  VARCHAR(120) NOT NULL,
    institution    VARCHAR(160) NOT NULL,
    country        VARCHAR(60)  NOT NULL,
    year_completed INTEGER      NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id)
);

CREATE TABLE fee_instalments (
    id           INTEGER PRIMARY KEY,
    enrolment_id INTEGER       NOT NULL,
    description  VARCHAR(60)   NOT NULL,
    due_date     DATE          NOT NULL,
    amount       DECIMAL(10,2) NOT NULL,
    amount_paid  DECIMAL(10,2) NOT NULL DEFAULT 0,
    paid_on      DATE,
    FOREIGN KEY (enrolment_id) REFERENCES enrolments (id)
);

CREATE TABLE contact_notes (
    id         INTEGER PRIMARY KEY,
    student_id INTEGER     NOT NULL,
    noted_on   DATE        NOT NULL,
    staff      VARCHAR(60) NOT NULL,
    channel    VARCHAR(20) NOT NULL CHECK (channel IN ('Phone', 'Email', 'In person', 'SMS', 'Agent')),
    note       TEXT        NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id)
);

-- People who asked about a course but haven't enrolled (yet): leads, from the website, agents, expos or walk-ins.
CREATE TABLE enquiries (
    id                INTEGER PRIMARY KEY,
    given_name        VARCHAR(60)  NOT NULL,
    family_name       VARCHAR(60)  NOT NULL,
    email             VARCHAR(160) NOT NULL UNIQUE,
    phone             VARCHAR(30),
    country           VARCHAR(60)  NOT NULL,
    course_id         INTEGER      NOT NULL,            -- the course they asked about
    agent_id          INTEGER,
    source            VARCHAR(20)  NOT NULL CHECK (source IN ('Website', 'Agent', 'Expo', 'Walk-in', 'Referral')),
    received_on       DATE         NOT NULL,
    status            VARCHAR(30)  NOT NULL
        CHECK (status IN ('New', 'Contacted', 'Application received', 'Offer sent', 'Lost')),
    status_changed_on DATE         NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses (id),
    FOREIGN KEY (agent_id) REFERENCES agents (id)
);

-- Every contact with an enquirer. `direction` says who reached out: 'In' from them, 'Out' from the college.
CREATE TABLE enquiry_notes (
    id         INTEGER PRIMARY KEY,
    enquiry_id INTEGER     NOT NULL,
    noted_on   DATE        NOT NULL,
    staff      VARCHAR(60) NOT NULL,
    channel    VARCHAR(20) NOT NULL CHECK (channel IN ('Phone', 'Email', 'In person', 'SMS', 'Agent')),
    direction  CHAR(3)     NOT NULL CHECK (direction IN ('In', 'Out')),
    note       TEXT        NOT NULL,
    FOREIGN KEY (enquiry_id) REFERENCES enquiries (id)
);

CREATE INDEX idx_students_family_name ON students (family_name);
CREATE INDEX idx_enrolments_student ON enrolments (student_id);
CREATE INDEX idx_attendance_weeks_enrolment ON attendance_weeks (enrolment_id);
CREATE INDEX idx_enquiry_notes_enquiry ON enquiry_notes (enquiry_id);
CREATE INDEX idx_visas_student ON visas (student_id);
CREATE INDEX idx_health_cover_student ON health_cover (student_id);
CREATE INDEX idx_english_tests_student ON english_tests (student_id);
CREATE INDEX idx_education_history_student ON education_history (student_id);
CREATE INDEX idx_fee_instalments_enrolment ON fee_instalments (enrolment_id);
CREATE INDEX idx_contact_notes_student ON contact_notes (student_id);
