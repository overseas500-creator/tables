BEGIN;

CREATE SCHEMA IF NOT EXISTS school_schedule;
SET LOCAL search_path TO school_schedule, public;

CREATE TABLE teachers (
    teacher_id BIGINT GENERATED ALWAYS AS IDENTITY,
    employee_number VARCHAR(50) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(254),
    waiting_count BIGINT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_teachers
        PRIMARY KEY (teacher_id),

    CONSTRAINT uq_teachers_employee_number
        UNIQUE (employee_number),

    CONSTRAINT chk_teachers_employee_number
        CHECK (
            employee_number = BTRIM(employee_number)
            AND employee_number <> ''
        ),

    CONSTRAINT chk_teachers_full_name
        CHECK (
            full_name = BTRIM(full_name)
            AND full_name <> ''
        ),

    CONSTRAINT chk_teachers_email
        CHECK (
            email IS NULL
            OR (
                email = BTRIM(email)
                AND email <> ''
            )
        ),

    CONSTRAINT chk_teachers_waiting_count
        CHECK (waiting_count >= 0)
);

CREATE UNIQUE INDEX uq_teachers_email_ci
    ON teachers (LOWER(email))
    WHERE email IS NOT NULL;


CREATE TABLE subjects (
    subject_id BIGINT GENERATED ALWAYS AS IDENTITY,
    subject_code VARCHAR(30) NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_subjects
        PRIMARY KEY (subject_id),

    CONSTRAINT uq_subjects_code
        UNIQUE (subject_code),

    CONSTRAINT uq_subjects_name
        UNIQUE (subject_name),

    CONSTRAINT chk_subjects_code
        CHECK (
            subject_code = BTRIM(subject_code)
            AND subject_code <> ''
        ),

    CONSTRAINT chk_subjects_name
        CHECK (
            subject_name = BTRIM(subject_name)
            AND subject_name <> ''
        )
);


CREATE TABLE school_classes (
    class_id BIGINT GENERATED ALWAYS AS IDENTITY,
    class_code VARCHAR(30) NOT NULL,
    class_name VARCHAR(150) NOT NULL,
    grade_level VARCHAR(30) NOT NULL,
    section_name VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_school_classes
        PRIMARY KEY (class_id),

    CONSTRAINT uq_school_classes_code
        UNIQUE (class_code),

    CONSTRAINT uq_school_classes_name
        UNIQUE (class_name),

    CONSTRAINT chk_school_classes_code
        CHECK (
            class_code = BTRIM(class_code)
            AND class_code <> ''
        ),

    CONSTRAINT chk_school_classes_name
        CHECK (
            class_name = BTRIM(class_name)
            AND class_name <> ''
        ),

    CONSTRAINT chk_school_classes_grade
        CHECK (
            grade_level = BTRIM(grade_level)
            AND grade_level <> ''
        ),

    CONSTRAINT chk_school_classes_section
        CHECK (
            section_name = BTRIM(section_name)
            AND section_name <> ''
        )
);


CREATE TABLE timetable_entries (
    timetable_entry_id BIGINT GENERATED ALWAYS AS IDENTITY,
    academic_year_start SMALLINT NOT NULL,
    term_number SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    period_number SMALLINT NOT NULL,
    teacher_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    class_id BIGINT NOT NULL,
    room_name VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_timetable_entries
        PRIMARY KEY (timetable_entry_id),

    CONSTRAINT fk_timetable_teacher
        FOREIGN KEY (teacher_id)
        REFERENCES teachers (teacher_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_timetable_subject
        FOREIGN KEY (subject_id)
        REFERENCES subjects (subject_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_timetable_class
        FOREIGN KEY (class_id)
        REFERENCES school_classes (class_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_timetable_academic_year
        CHECK (academic_year_start BETWEEN 2000 AND 2200),

    CONSTRAINT chk_timetable_term
        CHECK (term_number BETWEEN 1 AND 4),

    CONSTRAINT chk_timetable_day
        CHECK (day_of_week BETWEEN 1 AND 7),

    CONSTRAINT chk_timetable_period
        CHECK (period_number BETWEEN 1 AND 20),

    CONSTRAINT chk_timetable_room
        CHECK (
            room_name IS NULL
            OR BTRIM(room_name) <> ''
        ),

    CONSTRAINT uq_timetable_teacher_slot
        UNIQUE (
            academic_year_start,
            term_number,
            day_of_week,
            period_number,
            teacher_id
        ),

    CONSTRAINT uq_timetable_class_slot
        UNIQUE (
            academic_year_start,
            term_number,
            day_of_week,
            period_number,
            class_id
        ),

    CONSTRAINT uq_timetable_reference_context
        UNIQUE (
            timetable_entry_id,
            academic_year_start,
            term_number,
            day_of_week,
            period_number,
            teacher_id,
            class_id
        )
);

CREATE INDEX ix_timetable_teacher
    ON timetable_entries (
        teacher_id,
        academic_year_start,
        term_number,
        day_of_week
    );

CREATE INDEX ix_timetable_class
    ON timetable_entries (
        class_id,
        academic_year_start,
        term_number,
        day_of_week
    );


CREATE TABLE daily_absences (
    absence_id BIGINT GENERATED ALWAYS AS IDENTITY,
    absence_date DATE NOT NULL,
    teacher_id BIGINT NOT NULL,
    reason TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_daily_absences
        PRIMARY KEY (absence_id),

    CONSTRAINT fk_daily_absences_teacher
        FOREIGN KEY (teacher_id)
        REFERENCES teachers (teacher_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT uq_daily_absences_teacher_date
        UNIQUE (absence_date, teacher_id),

    CONSTRAINT uq_daily_absences_reference
        UNIQUE (absence_id, absence_date, teacher_id),

    CONSTRAINT chk_daily_absences_reason
        CHECK (
            reason IS NULL
            OR BTRIM(reason) <> ''
        )
);

CREATE INDEX ix_daily_absences_teacher
    ON daily_absences (teacher_id, absence_date DESC);


CREATE TABLE waiting_archive (
    waiting_archive_id BIGINT GENERATED ALWAYS AS IDENTITY,
    duty_date DATE NOT NULL,

    duty_day_of_week SMALLINT
        GENERATED ALWAYS AS (
            EXTRACT(ISODOW FROM duty_date)::SMALLINT
        ) STORED,

    academic_year_start SMALLINT NOT NULL,
    term_number SMALLINT NOT NULL,
    period_number SMALLINT NOT NULL,
    timetable_entry_id BIGINT NOT NULL,
    absence_id BIGINT NOT NULL,
    absent_teacher_id BIGINT NOT NULL,
    substitute_teacher_id BIGINT NOT NULL,
    class_id BIGINT NOT NULL,
    waiting_points INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_waiting_archive
        PRIMARY KEY (waiting_archive_id),

    CONSTRAINT fk_waiting_archive_timetable_context
        FOREIGN KEY (
            timetable_entry_id,
            academic_year_start,
            term_number,
            duty_day_of_week,
            period_number,
            absent_teacher_id,
            class_id
        )
        REFERENCES timetable_entries (
            timetable_entry_id,
            academic_year_start,
            term_number,
            day_of_week,
            period_number,
            teacher_id,
            class_id
        )
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_waiting_archive_absence
        FOREIGN KEY (
            absence_id,
            duty_date,
            absent_teacher_id
        )
        REFERENCES daily_absences (
            absence_id,
            absence_date,
            teacher_id
        )
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_waiting_archive_substitute
        FOREIGN KEY (substitute_teacher_id)
        REFERENCES teachers (teacher_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_waiting_archive_period
        CHECK (period_number BETWEEN 1 AND 20),

    CONSTRAINT chk_waiting_archive_points
        CHECK (waiting_points > 0),

    CONSTRAINT chk_waiting_archive_different_teachers
        CHECK (absent_teacher_id <> substitute_teacher_id),

    CONSTRAINT chk_waiting_archive_notes
        CHECK (
            notes IS NULL
            OR BTRIM(notes) <> ''
        ),

    CONSTRAINT uq_waiting_archive_timetable_date
        UNIQUE (duty_date, timetable_entry_id),

    CONSTRAINT uq_waiting_archive_substitute_slot
        UNIQUE (
            duty_date,
            period_number,
            substitute_teacher_id
        ),

    CONSTRAINT uq_waiting_archive_class_slot
        UNIQUE (
            duty_date,
            period_number,
            class_id
        )
);

CREATE INDEX ix_waiting_archive_substitute_history
    ON waiting_archive (substitute_teacher_id, duty_date DESC);

CREATE INDEX ix_waiting_archive_absent_history
    ON waiting_archive (absent_teacher_id, duty_date DESC);


CREATE FUNCTION school_schedule.validate_waiting_assignment()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = pg_catalog, school_schedule
AS $function$
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtextextended(
            FORMAT(
                'teacher-slot:%s:%s:%s:%s:%s',
                NEW.academic_year_start,
                NEW.term_number,
                NEW.duty_day_of_week,
                NEW.period_number,
                NEW.substitute_teacher_id
            ),
            0
        )
    );

    PERFORM pg_advisory_xact_lock(
        hashtextextended(
            FORMAT(
                'teacher-absence:%s:%s',
                NEW.duty_date,
                NEW.substitute_teacher_id
            ),
            0
        )
    );

    IF EXISTS (
        SELECT 1
        FROM school_schedule.timetable_entries AS entry
        WHERE entry.academic_year_start = NEW.academic_year_start
          AND entry.term_number = NEW.term_number
          AND entry.day_of_week = NEW.duty_day_of_week
          AND entry.period_number = NEW.period_number
          AND entry.teacher_id = NEW.substitute_teacher_id
    ) THEN
        RAISE EXCEPTION
            'Substitute teacher % already has a scheduled class in this slot.',
            NEW.substitute_teacher_id
            USING ERRCODE = '23505';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM school_schedule.daily_absences AS absence
        WHERE absence.absence_date = NEW.duty_date
          AND absence.teacher_id = NEW.substitute_teacher_id
    ) THEN
        RAISE EXCEPTION
            'Substitute teacher % is absent on %.',
            NEW.substitute_teacher_id,
            NEW.duty_date
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$function$;


CREATE FUNCTION school_schedule.validate_timetable_assignment()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = pg_catalog, school_schedule
AS $function$
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtextextended(
            FORMAT(
                'teacher-slot:%s:%s:%s:%s:%s',
                NEW.academic_year_start,
                NEW.term_number,
                NEW.day_of_week,
                NEW.period_number,
                NEW.teacher_id
            ),
            0
        )
    );

    IF EXISTS (
        SELECT 1
        FROM school_schedule.waiting_archive AS waiting
        WHERE waiting.academic_year_start = NEW.academic_year_start
          AND waiting.term_number = NEW.term_number
          AND waiting.duty_day_of_week = NEW.day_of_week
          AND waiting.period_number = NEW.period_number
          AND waiting.substitute_teacher_id = NEW.teacher_id
    ) THEN
        RAISE EXCEPTION
            'Teacher % already has waiting-duty history in this timetable slot.',
            NEW.teacher_id
            USING ERRCODE = '23505';
    END IF;

    RETURN NEW;
END;
$function$;


CREATE FUNCTION school_schedule.validate_daily_absence()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = pg_catalog, school_schedule
AS $function$
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtextextended(
            FORMAT(
                'teacher-absence:%s:%s',
                NEW.absence_date,
                NEW.teacher_id
            ),
            0
        )
    );

    IF EXISTS (
        SELECT 1
        FROM school_schedule.waiting_archive AS waiting
        WHERE waiting.duty_date = NEW.absence_date
          AND waiting.substitute_teacher_id = NEW.teacher_id
    ) THEN
        RAISE EXCEPTION
            'Teacher % already has a waiting duty on %.',
            NEW.teacher_id,
            NEW.absence_date
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$function$;


CREATE FUNCTION school_schedule.sync_teacher_waiting_count()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = pg_catalog, school_schedule
AS $function$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE school_schedule.teachers
        SET waiting_count = waiting_count + NEW.waiting_points
        WHERE teacher_id = NEW.substitute_teacher_id;

        RETURN NEW;
    END IF;

    IF TG_OP = 'DELETE' THEN
        UPDATE school_schedule.teachers
        SET waiting_count = waiting_count - OLD.waiting_points
        WHERE teacher_id = OLD.substitute_teacher_id;

        RETURN OLD;
    END IF;

    UPDATE school_schedule.teachers
    SET waiting_count =
        waiting_count
        + CASE
            WHEN teacher_id = NEW.substitute_teacher_id
                THEN NEW.waiting_points
            ELSE 0
          END
        - CASE
            WHEN teacher_id = OLD.substitute_teacher_id
                THEN OLD.waiting_points
            ELSE 0
          END
    WHERE teacher_id IN (
        OLD.substitute_teacher_id,
        NEW.substitute_teacher_id
    );

    RETURN NEW;
END;
$function$;


CREATE TRIGGER trg_timetable_validate_waiting_conflict
BEFORE INSERT OR UPDATE
ON timetable_entries
FOR EACH ROW
EXECUTE FUNCTION school_schedule.validate_timetable_assignment();


CREATE TRIGGER trg_daily_absences_validate_waiting_conflict
BEFORE INSERT OR UPDATE
ON daily_absences
FOR EACH ROW
EXECUTE FUNCTION school_schedule.validate_daily_absence();


CREATE TRIGGER trg_waiting_archive_validate
BEFORE INSERT OR UPDATE
ON waiting_archive
FOR EACH ROW
EXECUTE FUNCTION school_schedule.validate_waiting_assignment();


CREATE TRIGGER trg_waiting_archive_sync_counter
AFTER INSERT OR UPDATE OR DELETE
ON waiting_archive
FOR EACH ROW
EXECUTE FUNCTION school_schedule.sync_teacher_waiting_count();

COMMIT;
