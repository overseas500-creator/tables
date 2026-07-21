# -*- coding: utf-8 -*-


class WaitingEngineError(Exception):
    pass


class DailyWaitingEngine:
    def __init__(
        self,
        teachers,
        base_timetable,
        waiting_archive,
        current_date,
        current_day,
    ):
        self.teachers = teachers
        self.base_timetable = base_timetable
        self.waiting_archive = waiting_archive
        self.current_date = current_date
        self.current_day = current_day

        self.absent_teacher_ids = set()

        self.validate_data()

    def validate_data(self):
        teacher_names = set()
        lesson_ids = set()
        teacher_slots = set()
        class_slots = set()

        for teacher_id in self.teachers:
            teacher_name = self.teachers[teacher_id]["name"]
            normalized_name = self.normalize_name(
                teacher_name
            )

            if normalized_name in teacher_names:
                raise WaitingEngineError(
                    "يجب ألا تتكرر أسماء المعلمين."
                )

            teacher_names.add(normalized_name)

        for lesson in self.base_timetable:
            lesson_id = lesson["lesson_id"]
            teacher_id = lesson["teacher_id"]
            day = lesson["day"]
            period = lesson["period"]
            class_name = lesson["class_name"]

            if lesson_id in lesson_ids:
                raise WaitingEngineError(
                    "رقم حصة أساسية مكرر: "
                    + lesson_id
                )

            lesson_ids.add(lesson_id)

            if teacher_id not in self.teachers:
                raise WaitingEngineError(
                    "معلم غير معروف في الجدول: "
                    + teacher_id
                )

            if period <= 0:
                raise WaitingEngineError(
                    "رقم الحصة يجب أن يكون موجباً."
                )

            teacher_slot = (
                teacher_id,
                day,
                period,
            )

            if teacher_slot in teacher_slots:
                raise WaitingEngineError(
                    "يوجد تعارض أساسي للمعلم: "
                    + self.teachers[teacher_id]["name"]
                )

            teacher_slots.add(teacher_slot)

            class_slot = (
                class_name,
                day,
                period,
            )

            if class_slot in class_slots:
                raise WaitingEngineError(
                    "يوجد تعارض أساسي للفصل: "
                    + class_name
                )

            class_slots.add(class_slot)

        for record in self.waiting_archive:
            substitute_id = record[
                "substitute_teacher_id"
            ]

            if substitute_id not in self.teachers:
                raise WaitingEngineError(
                    "معلم بديل غير معروف في الأرشيف: "
                    + substitute_id
                )

    @staticmethod
    def normalize_name(name):
        return name.strip().casefold()

    def find_teacher_id_by_name(self, teacher_name):
        normalized_input = self.normalize_name(
            teacher_name
        )

        matches = []

        for teacher_id in self.teachers:
            stored_name = self.teachers[
                teacher_id
            ]["name"]

            if (
                self.normalize_name(stored_name)
                == normalized_input
            ):
                matches.append(teacher_id)

        if not matches:
            raise WaitingEngineError(
                "لم يتم العثور على المعلم: "
                + teacher_name
            )

        if len(matches) > 1:
            raise WaitingEngineError(
                "يوجد أكثر من معلم بالاسم نفسه: "
                + teacher_name
            )

        return matches[0]

    def register_absent_teacher(self, teacher_name):
        teacher_id = self.find_teacher_id_by_name(
            teacher_name
        )

        self.absent_teacher_ids.add(teacher_id)

        return teacher_id

    def find_vacant_lessons(self):
        vacant_lessons = []

        for lesson in self.base_timetable:
            if lesson["day"] != self.current_day:
                continue

            if (
                lesson["teacher_id"]
                not in self.absent_teacher_ids
            ):
                continue

            vacant_lessons.append(lesson)

        vacant_lessons.sort(
            key=lambda lesson: (
                lesson["period"],
                lesson["class_name"],
                lesson["lesson_id"],
            )
        )

        return vacant_lessons

    def get_weekly_base_count(self, teacher_id):
        count = 0

        for lesson in self.base_timetable:
            if lesson["teacher_id"] == teacher_id:
                count += 1

        return count

    def get_waiting_count(self, teacher_id):
        count = 0

        for record in self.waiting_archive:
            if record.get("status") != "assigned":
                continue

            if (
                record["substitute_teacher_id"]
                == teacher_id
            ):
                count += 1

        return count

    def get_daily_waiting_count(self, teacher_id):
        count = 0

        for record in self.waiting_archive:
            if record.get("status") != "assigned":
                continue

            if record["date"] != self.current_date:
                continue

            if (
                record["substitute_teacher_id"]
                == teacher_id
            ):
                count += 1

        return count

    def get_teacher_metrics(self, teacher_id):
        weekly_base_count = (
            self.get_weekly_base_count(teacher_id)
        )

        waiting_count = self.get_waiting_count(
            teacher_id
        )

        cumulative_total = (
            weekly_base_count + waiting_count
        )

        return {
            "teacher_id": teacher_id,
            "teacher_name": self.teachers[
                teacher_id
            ]["name"],
            "weekly_base_count": weekly_base_count,
            "waiting_count": waiting_count,
            "daily_waiting_count":
                self.get_daily_waiting_count(
                    teacher_id
                ),
            "cumulative_total": cumulative_total,
        }

    def get_all_teacher_metrics(self):
        metrics = {}

        for teacher_id in self.teachers:
            metrics[teacher_id] = (
                self.get_teacher_metrics(teacher_id)
            )

        return metrics

    def has_primary_lesson(
        self,
        teacher_id,
        period,
    ):
        for lesson in self.base_timetable:
            if lesson["day"] != self.current_day:
                continue

            if lesson["period"] != period:
                continue

            if lesson["teacher_id"] == teacher_id:
                return True

        return False

    def has_waiting_lesson(
        self,
        teacher_id,
        period,
    ):
        for record in self.waiting_archive:
            if record.get("status") != "assigned":
                continue

            if record["date"] != self.current_date:
                continue

            if record["period"] != period:
                continue

            if (
                record["substitute_teacher_id"]
                == teacher_id
            ):
                return True

        return False

    def find_existing_coverage(self, lesson_id):
        for record in self.waiting_archive:
            if record.get("status") != "assigned":
                continue

            if record["date"] != self.current_date:
                continue

            if record["source_lesson_id"] == lesson_id:
                return record

        return None

    def get_available_teachers(self, period):
        available = []

        for teacher_id in self.teachers:
            if teacher_id in self.absent_teacher_ids:
                continue

            if self.has_primary_lesson(
                teacher_id,
                period,
            ):
                continue

            if self.has_waiting_lesson(
                teacher_id,
                period,
            ):
                continue

            metrics = self.get_teacher_metrics(
                teacher_id
            )

            available.append(metrics)

        available.sort(
            key=lambda teacher: (
                teacher["cumulative_total"],
                teacher["daily_waiting_count"],
                teacher["waiting_count"],
                teacher["weekly_base_count"],
                teacher["teacher_name"],
            )
        )

        return available

    def create_archive_id(self):
        sequence = len(self.waiting_archive) + 1

        return (
            "WAIT-"
            + self.current_date
            + "-"
            + str(sequence).zfill(5)
        )

    def assign_daily_waiting_lessons(self):
        vacant_lessons = (
            self.find_vacant_lessons()
        )

        results = []

        for lesson in vacant_lessons:
            existing_record = (
                self.find_existing_coverage(
                    lesson["lesson_id"]
                )
            )

            if existing_record is not None:
                results.append(
                    {
                        "status": "already_assigned",
                        "lesson": lesson,
                        "archive_record":
                            existing_record,
                    }
                )
                continue

            available_teachers = (
                self.get_available_teachers(
                    lesson["period"]
                )
            )

            if not available_teachers:
                results.append(
                    {
                        "status": "uncovered",
                        "lesson": lesson,
                        "reason":
                            "لا يوجد معلم متاح.",
                    }
                )
                continue

            selected = available_teachers[0]

            archive_record = {
                "archive_id":
                    self.create_archive_id(),
                "status": "assigned",
                "date": self.current_date,
                "day": self.current_day,
                "period": lesson["period"],
                "class_name":
                    lesson["class_name"],
                "subject_name":
                    lesson["subject_name"],
                "source_lesson_id":
                    lesson["lesson_id"],
                "absent_teacher_id":
                    lesson["teacher_id"],
                "substitute_teacher_id":
                    selected["teacher_id"],
                "weekly_base_count":
                    selected[
                        "weekly_base_count"
                    ],
                "waiting_count_before":
                    selected["waiting_count"],
                "waiting_count_after":
                    selected["waiting_count"] + 1,
                "cumulative_total_before":
                    selected[
                        "cumulative_total"
                    ],
                "cumulative_total_after":
                    selected[
                        "cumulative_total"
                    ] + 1,
            }

            self.waiting_archive.append(
                archive_record
            )

            results.append(
                {
                    "status": "assigned",
                    "lesson": lesson,
                    "archive_record":
                        archive_record,
                }
            )

        return results


def print_absence_summary(
    engine,
    absent_teacher_name,
):
    print("")
    print("=" * 78)
    print("تسجيل الغياب اليومي")
    print("=" * 78)
    print("التاريخ -> " + engine.current_date)
    print("اليوم -> " + engine.current_day)
    print(
        "المعلم الغائب -> "
        + absent_teacher_name
    )

    vacant_lessons = engine.find_vacant_lessons()

    print(
        "عدد الحصص الشاغرة -> "
        + str(len(vacant_lessons))
    )

    for lesson in vacant_lessons:
        print(
            "الحصة -> "
            + str(lesson["period"])
            + " | الفصل -> "
            + lesson["class_name"]
            + " | المادة -> "
            + lesson["subject_name"]
        )


def print_daily_assignments(
    engine,
    assignments,
):
    print("")
    print("=" * 78)
    print("جدول حصص الانتظار اليومي")
    print("=" * 78)

    if not assignments:
        print("لا توجد حصص شاغرة اليوم.")
        return

    for result in assignments:
        lesson = result["lesson"]

        print("")
        print("اليوم -> " + engine.current_day)
        print(
            "الحصة -> "
            + str(lesson["period"])
        )
        print(
            "الفصل -> "
            + lesson["class_name"]
        )
        print(
            "المادة -> "
            + lesson["subject_name"]
        )
        print(
            "المعلم الغائب -> "
            + engine.teachers[
                lesson["teacher_id"]
            ]["name"]
        )

        if result["status"] == "uncovered":
            print("المعلم البديل -> لم يتم التعيين")
            print(
                "الحالة -> "
                + result["reason"]
            )
            print("-" * 78)
            continue

        record = result["archive_record"]
        substitute_name = engine.teachers[
            record["substitute_teacher_id"]
        ]["name"]

        print(
            "المعلم البديل -> "
            + substitute_name
        )

        if result["status"] == "already_assigned":
            print("الحالة -> مسندة مسبقاً")
        else:
            print("الحالة -> تم الإسناد بنجاح")

        print(
            "الحصص الأساسية الأسبوعية -> "
            + str(record["weekly_base_count"])
        )
        print(
            "حصص الانتظار قبل الإسناد -> "
            + str(record["waiting_count_before"])
        )
        print(
            "المجموع التراكمي قبل الإسناد -> "
            + str(
                record[
                    "cumulative_total_before"
                ]
            )
        )
        print(
            "حصص الانتظار بعد الإسناد -> "
            + str(record["waiting_count_after"])
        )
        print(
            "المجموع التراكمي بعد الإسناد -> "
            + str(
                record[
                    "cumulative_total_after"
                ]
            )
        )
        print(
            "رقم سجل الأرشيف -> "
            + record["archive_id"]
        )
        print("-" * 78)


def print_updated_counters(
    engine,
    metrics_before,
    assignments,
):
    assigned_today = {}

    for result in assignments:
        if result["status"] != "assigned":
            continue

        teacher_id = result[
            "archive_record"
        ]["substitute_teacher_id"]

        assigned_today[teacher_id] = (
            assigned_today.get(teacher_id, 0)
            + 1
        )

    metrics_after = (
        engine.get_all_teacher_metrics()
    )

    print("")
    print("=" * 78)
    print("العدادات التراكمية بعد التوزيع")
    print("=" * 78)

    for teacher_id in engine.teachers:
        before = metrics_before[teacher_id]
        after = metrics_after[teacher_id]

        status = "متاح"

        if teacher_id in engine.absent_teacher_ids:
            status = "غائب"

        print("")
        print(
            "المعلم -> "
            + after["teacher_name"]
        )
        print("الحالة -> " + status)
        print(
            "الحصص الأساسية الأسبوعية -> "
            + str(after["weekly_base_count"])
        )
        print(
            "انتظار سابق -> "
            + str(before["waiting_count"])
        )
        print(
            "انتظار أسند اليوم -> "
            + str(
                assigned_today.get(
                    teacher_id,
                    0,
                )
            )
        )
        print(
            "عداد الانتظار الجديد -> "
            + str(after["waiting_count"])
        )
        print(
            "المجموع التراكمي الجديد -> "
            + str(after["cumulative_total"])
        )
        print("-" * 78)


def print_today_archive(engine):
    print("")
    print("=" * 78)
    print("الأرشيف التاريخي المحفوظ لليوم")
    print("=" * 78)

    records_found = 0

    for record in engine.waiting_archive:
        if record.get("status") != "assigned":
            continue

        if record["date"] != engine.current_date:
            continue

        records_found += 1

        substitute_name = engine.teachers[
            record["substitute_teacher_id"]
        ]["name"]

        absent_name = engine.teachers[
            record["absent_teacher_id"]
        ]["name"]

        print("")
        print(
            "رقم السجل -> "
            + record["archive_id"]
        )
        print(
            "الحصة -> "
            + str(record["period"])
        )
        print(
            "الفصل -> "
            + record["class_name"]
        )
        print(
            "المادة -> "
            + record["subject_name"]
        )
        print(
            "المعلم الغائب -> "
            + absent_name
        )
        print(
            "المعلم البديل -> "
            + substitute_name
        )
        print(
            "المجموع بعد الإسناد -> "
            + str(
                record[
                    "cumulative_total_after"
                ]
            )
        )
        print("-" * 78)

    if records_found == 0:
        print("لم تسجل عمليات انتظار اليوم.")


def add_lesson(
    timetable,
    lesson_id,
    day,
    period,
    class_name,
    subject_name,
    teacher_id,
):
    timetable.append(
        {
            "lesson_id": lesson_id,
            "day": day,
            "period": period,
            "class_name": class_name,
            "subject_name": subject_name,
            "teacher_id": teacher_id,
        }
    )


def fill_teacher_weekly_schedule(
    timetable,
    teacher_id,
    subject_name,
    target_count,
    days,
    periods_per_day,
    protected_slots,
):
    existing_slots = set()
    current_count = 0

    for lesson in timetable:
        if lesson["teacher_id"] == teacher_id:
            existing_slots.add(
                (
                    lesson["day"],
                    lesson["period"],
                )
            )
            current_count += 1

    sequence = 1

    for day in days:
        for period in range(
            1,
            periods_per_day + 1,
        ):
            if current_count >= target_count:
                return

            slot = (day, period)

            if slot in existing_slots:
                continue

            if slot in protected_slots:
                continue

            lesson_id = (
                "BASE-"
                + teacher_id
                + "-"
                + str(sequence).zfill(3)
            )

            class_name = (
                "مجموعة "
                + teacher_id
                + "-"
                + str(sequence)
            )

            add_lesson(
                timetable=timetable,
                lesson_id=lesson_id,
                day=day,
                period=period,
                class_name=class_name,
                subject_name=subject_name,
                teacher_id=teacher_id,
            )

            existing_slots.add(slot)
            current_count += 1
            sequence += 1

    if current_count < target_count:
        raise WaitingEngineError(
            "تعذر تكوين العدد الأسبوعي للمعلم: "
            + teacher_id
        )


def build_mock_archive(
    teachers,
    previous_waiting_counts,
):
    archive = []
    teacher_ids = list(teachers.keys())
    sequence = 1

    for teacher_index in range(
        len(teacher_ids)
    ):
        teacher_id = teacher_ids[
            teacher_index
        ]

        count = previous_waiting_counts.get(
            teacher_id,
            0,
        )

        absent_teacher_id = teacher_ids[
            (teacher_index + 1)
            % len(teacher_ids)
        ]

        for item_index in range(count):
            archive.append(
                {
                    "archive_id":
                        "HIST-"
                        + str(sequence).zfill(5),
                    "status": "assigned",
                    "date":
                        "2026-07-"
                        + str(
                            item_index + 1
                        ).zfill(2),
                    "day": "يوم سابق",
                    "period":
                        (item_index % 6) + 1,
                    "class_name":
                        "فصل تاريخي",
                    "subject_name":
                        "مادة تاريخية",
                    "source_lesson_id":
                        "HIST-LESSON-"
                        + str(sequence),
                    "absent_teacher_id":
                        absent_teacher_id,
                    "substitute_teacher_id":
                        teacher_id,
                    "weekly_base_count": 0,
                    "waiting_count_before":
                        item_index,
                    "waiting_count_after":
                        item_index + 1,
                    "cumulative_total_before":
                        item_index,
                    "cumulative_total_after":
                        item_index + 1,
                }
            )

            sequence += 1

    return archive


def build_mock_data():
    days = [
        "الأحد",
        "الاثنين",
        "الثلاثاء",
        "الأربعاء",
        "الخميس",
    ]

    periods_per_day = 6
    current_date = "2026-07-21"
    current_day = "الثلاثاء"

    teachers = {
        "t_absent": {
            "name": "أحمد القحطاني",
        },
        "t_sara": {
            "name": "سارة الحربي",
        },
        "t_khalid": {
            "name": "خالد العتيبي",
        },
        "t_noura": {
            "name": "نورة الدوسري",
        },
        "t_majed": {
            "name": "ماجد المطيري",
        },
        "t_laila": {
            "name": "ليلى الشهري",
        },
    }

    timetable = []

    # حصص المعلم الذي سيغيب اليوم.
    add_lesson(
        timetable,
        "ABSENT-TUE-01",
        current_day,
        1,
        "الأول / أ",
        "الرياضيات",
        "t_absent",
    )

    add_lesson(
        timetable,
        "ABSENT-TUE-03",
        current_day,
        3,
        "الثاني / أ",
        "الرياضيات",
        "t_absent",
    )

    add_lesson(
        timetable,
        "ABSENT-TUE-05",
        current_day,
        5,
        "الثالث / أ",
        "الرياضيات",
        "t_absent",
    )

    # إشغال بعض البدلاء في حصص محددة لإظهار الفحص الفعلي.
    add_lesson(
        timetable,
        "SARA-TUE-01",
        current_day,
        1,
        "الرابع / أ",
        "اللغة العربية",
        "t_sara",
    )

    add_lesson(
        timetable,
        "NOURA-TUE-03",
        current_day,
        3,
        "الخامس / أ",
        "التربية الفنية",
        "t_noura",
    )

    add_lesson(
        timetable,
        "MAJED-TUE-01",
        current_day,
        1,
        "السادس / أ",
        "التربية البدنية",
        "t_majed",
    )

    add_lesson(
        timetable,
        "MAJED-TUE-03",
        current_day,
        3,
        "السادس / ب",
        "التربية البدنية",
        "t_majed",
    )

    # حماية الحصص الشاغرة المطلوبة من الملء أثناء بناء بيانات الأسبوع.
    absent_protected = {
        (current_day, 2),
        (current_day, 4),
        (current_day, 6),
    }

    sara_protected = {
        (current_day, 3),
        (current_day, 5),
    }

    khalid_protected = {
        (current_day, 1),
        (current_day, 3),
        (current_day, 5),
    }

    noura_protected = {
        (current_day, 1),
        (current_day, 5),
    }

    majed_protected = {
        (current_day, 5),
    }

    laila_protected = {
        (current_day, 1),
        (current_day, 3),
        (current_day, 5),
    }

    fill_teacher_weekly_schedule(
        timetable,
        "t_absent",
        "الرياضيات",
        16,
        days,
        periods_per_day,
        absent_protected,
    )

    fill_teacher_weekly_schedule(
        timetable,
        "t_sara",
        "اللغة العربية",
        12,
        days,
        periods_per_day,
        sara_protected,
    )

    fill_teacher_weekly_schedule(
        timetable,
        "t_khalid",
        "العلوم",
        14,
        days,
        periods_per_day,
        khalid_protected,
    )

    fill_teacher_weekly_schedule(
        timetable,
        "t_noura",
        "التربية الفنية",
        10,
        days,
        periods_per_day,
        noura_protected,
    )

    fill_teacher_weekly_schedule(
        timetable,
        "t_majed",
        "التربية البدنية",
        16,
        days,
        periods_per_day,
        majed_protected,
    )

    fill_teacher_weekly_schedule(
        timetable,
        "t_laila",
        "اللغة الإنجليزية",
        9,
        days,
        periods_per_day,
        laila_protected,
    )

    previous_waiting_counts = {
        "t_absent": 2,
        "t_sara": 1,
        "t_khalid": 0,
        "t_noura": 4,
        "t_majed": 1,
        "t_laila": 6,
    }

    waiting_archive = build_mock_archive(
        teachers,
        previous_waiting_counts,
    )

    return {
        "days": days,
        "periods_per_day": periods_per_day,
        "current_date": current_date,
        "current_day": current_day,
        "teachers": teachers,
        "timetable": timetable,
        "waiting_archive": waiting_archive,
    }


def main():
    mock_data = build_mock_data()

    engine = DailyWaitingEngine(
        teachers=mock_data["teachers"],
        base_timetable=mock_data["timetable"],
        waiting_archive=mock_data[
            "waiting_archive"
        ],
        current_date=mock_data[
            "current_date"
        ],
        current_day=mock_data["current_day"],
    )

    absent_teacher_name = "أحمد القحطاني"

    engine.register_absent_teacher(
        absent_teacher_name
    )

    metrics_before = (
        engine.get_all_teacher_metrics()
    )

    print_absence_summary(
        engine,
        absent_teacher_name,
    )

    assignments = (
        engine.assign_daily_waiting_lessons()
    )

    print_daily_assignments(
        engine,
        assignments,
    )

    print_updated_counters(
        engine,
        metrics_before,
        assignments,
    )

    print_today_archive(engine)


if __name__ == "__main__":
    try:
        main()
    except WaitingEngineError as error:
        print("")
        print("فشل تشغيل محرك حصص الانتظار.")
        print("السبب -> " + str(error))
