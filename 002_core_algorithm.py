# -*- coding: utf-8 -*-


class SchedulingError(Exception):
    pass


class TimetableScheduler:
    def __init__(
        self,
        teachers,
        subjects,
        classes,
        requirements,
        days,
        periods_per_day,
    ):
        self.teachers = teachers
        self.subjects = subjects
        self.classes = classes
        self.requirements = requirements
        self.days = days
        self.periods_per_day = periods_per_day

        self.units_needed = {}
        self.placements = {}

        self.cells = {}
        self.teacher_busy = set()
        self.class_busy = set()
        self.subject_used_on_day = set()

        self.class_day_load = {}
        self.teacher_day_load = {}

        self.search_nodes = 0
        self.max_search_nodes = 1000000

        self.validate_input()

    def validate_input(self):
        if not self.days:
            raise SchedulingError(
                "يجب تحديد يوم دراسي واحد على الأقل."
            )

        if self.periods_per_day < 1:
            raise SchedulingError(
                "عدد الحصص اليومية يجب أن يكون أكبر من صفر."
            )

        seen_requirement_ids = set()
        seen_class_subjects = set()

        class_load = {}
        teacher_load = {}

        total_capacity = (
            len(self.days) * self.periods_per_day
        )

        for requirement in self.requirements:
            requirement_id = requirement["id"]
            class_id = requirement["class_id"]
            subject_id = requirement["subject_id"]
            teacher_id = requirement["teacher_id"]
            weekly_periods = requirement["weekly_periods"]

            if requirement_id in seen_requirement_ids:
                raise SchedulingError(
                    "رقم متطلب مكرر: " + requirement_id
                )

            seen_requirement_ids.add(requirement_id)

            if class_id not in self.classes:
                raise SchedulingError(
                    "الفصل غير موجود: " + class_id
                )

            if subject_id not in self.subjects:
                raise SchedulingError(
                    "المادة غير موجودة: " + subject_id
                )

            if teacher_id not in self.teachers:
                raise SchedulingError(
                    "المعلم غير موجود: " + teacher_id
                )

            if weekly_periods <= 0:
                raise SchedulingError(
                    "عدد الحصص الأسبوعية يجب أن يكون موجباً."
                )

            class_subject_key = (
                class_id,
                subject_id,
            )

            if class_subject_key in seen_class_subjects:
                raise SchedulingError(
                    "يوجد أكثر من متطلب للمادة نفسها "
                    "والفصل نفسه."
                )

            seen_class_subjects.add(class_subject_key)

            is_double = self.subjects[
                subject_id
            ]["double"]

            if is_double:
                if self.periods_per_day < 2:
                    raise SchedulingError(
                        "المادة المزدوجة تحتاج حصتين "
                        "على الأقل في اليوم."
                    )

                if weekly_periods % 2 != 0:
                    raise SchedulingError(
                        "عدد حصص المادة المزدوجة يجب "
                        "أن يكون عدداً زوجياً."
                    )

                double_blocks = weekly_periods // 2

                if double_blocks > len(self.days):
                    raise SchedulingError(
                        "عدد الكتل المزدوجة أكبر من "
                        "عدد الأيام المتاحة."
                    )

                self.units_needed[
                    requirement_id
                ] = double_blocks
            else:
                if weekly_periods > len(self.days):
                    raise SchedulingError(
                        "لا يمكن توزيع المادة دون تكرار؛ "
                        "عدد حصصها أكبر من عدد الأيام."
                    )

                self.units_needed[
                    requirement_id
                ] = weekly_periods

            self.placements[requirement_id] = []

            class_load[class_id] = (
                class_load.get(class_id, 0)
                + weekly_periods
            )

            teacher_load[teacher_id] = (
                teacher_load.get(teacher_id, 0)
                + weekly_periods
            )

        for class_id in class_load:
            if class_load[class_id] > total_capacity:
                raise SchedulingError(
                    "حصص الفصل تتجاوز السعة الأسبوعية: "
                    + self.classes[class_id]
                )

        for teacher_id in teacher_load:
            if teacher_load[teacher_id] > total_capacity:
                raise SchedulingError(
                    "حصص المعلم تتجاوز السعة الأسبوعية: "
                    + self.teachers[teacher_id]
                )

    def solve(self):
        solved = self.search()

        if not solved:
            raise SchedulingError(
                "تعذر إنشاء جدول يحقق جميع الشروط."
            )

        result = {
            "cells": dict(self.cells),
            "placements": {},
            "search_nodes": self.search_nodes,
        }

        for requirement_id in self.placements:
            result["placements"][requirement_id] = list(
                self.placements[requirement_id]
            )

        self.validate_solution(result)
        return result

    def search(self):
        self.search_nodes += 1

        if self.search_nodes > self.max_search_nodes:
            raise SchedulingError(
                "تم تجاوز الحد الأقصى لمحاولات البحث."
            )

        completed = True

        for requirement in self.requirements:
            requirement_id = requirement["id"]

            if (
                len(self.placements[requirement_id])
                < self.units_needed[requirement_id]
            ):
                completed = False
                break

        if completed:
            return True

        selected_requirement = None
        selected_candidates = None
        selected_key = None

        for requirement in self.requirements:
            requirement_id = requirement["id"]

            placed_count = len(
                self.placements[requirement_id]
            )
            required_count = self.units_needed[
                requirement_id
            ]

            if placed_count >= required_count:
                continue

            candidates = self.get_candidates(
                requirement
            )

            if not candidates:
                return False

            subject = self.subjects[
                requirement["subject_id"]
            ]

            duration = (
                2 if subject["double"] else 1
            )

            remaining = required_count - placed_count

            selection_key = (
                len(candidates),
                -duration,
                -remaining,
                requirement_id,
            )

            if (
                selected_key is None
                or selection_key < selected_key
            ):
                selected_key = selection_key
                selected_requirement = requirement
                selected_candidates = candidates

        if selected_requirement is None:
            return True

        for placement in selected_candidates:
            self.place(
                selected_requirement,
                placement,
            )

            if self.search():
                return True

            self.unplace(
                selected_requirement,
                placement,
            )

        return False

    def get_candidates(self, requirement):
        requirement_id = requirement["id"]
        class_id = requirement["class_id"]
        subject_id = requirement["subject_id"]
        teacher_id = requirement["teacher_id"]

        is_double = self.subjects[
            subject_id
        ]["double"]

        duration = 2 if is_double else 1

        existing_placements = self.placements[
            requirement_id
        ]

        if existing_placements:
            previous = existing_placements[-1]

            last_rank = (
                previous["day"]
                * self.periods_per_day
                + previous["start_period"]
                - 1
            )
        else:
            last_rank = -1

        candidates = []

        for day_index in range(len(self.days)):
            subject_day_key = (
                class_id,
                subject_id,
                day_index,
            )

            if (
                subject_day_key
                in self.subject_used_on_day
            ):
                continue

            final_start = (
                self.periods_per_day
                - duration
                + 1
            )

            for start_period in range(
                1,
                final_start + 1,
            ):
                candidate_rank = (
                    day_index
                    * self.periods_per_day
                    + start_period
                    - 1
                )

                if candidate_rank <= last_rank:
                    continue

                available = True

                for offset in range(duration):
                    period = start_period + offset

                    class_slot = (
                        class_id,
                        day_index,
                        period,
                    )

                    teacher_slot = (
                        teacher_id,
                        day_index,
                        period,
                    )

                    if class_slot in self.class_busy:
                        available = False
                        break

                    if teacher_slot in self.teacher_busy:
                        available = False
                        break

                if available:
                    candidates.append(
                        {
                            "day": day_index,
                            "start_period": start_period,
                            "duration": duration,
                        }
                    )

        remaining_units = (
            self.units_needed[requirement_id]
            - len(existing_placements)
        )

        available_days = set()

        for candidate in candidates:
            available_days.add(candidate["day"])

        if len(available_days) < remaining_units:
            return []

        def candidate_score(candidate):
            day_index = candidate["day"]

            class_load_key = (
                class_id,
                day_index,
            )

            teacher_load_key = (
                teacher_id,
                day_index,
            )

            return (
                self.class_day_load.get(
                    class_load_key,
                    0,
                ),
                self.teacher_day_load.get(
                    teacher_load_key,
                    0,
                ),
                day_index,
                candidate["start_period"],
            )

        candidates.sort(key=candidate_score)

        return candidates

    def place(self, requirement, placement):
        requirement_id = requirement["id"]
        class_id = requirement["class_id"]
        subject_id = requirement["subject_id"]
        teacher_id = requirement["teacher_id"]

        day_index = placement["day"]
        start_period = placement["start_period"]
        duration = placement["duration"]

        self.placements[requirement_id].append(
            placement
        )

        subject_day_key = (
            class_id,
            subject_id,
            day_index,
        )

        self.subject_used_on_day.add(
            subject_day_key
        )

        for offset in range(duration):
            period = start_period + offset

            class_slot = (
                class_id,
                day_index,
                period,
            )

            teacher_slot = (
                teacher_id,
                day_index,
                period,
            )

            self.class_busy.add(class_slot)
            self.teacher_busy.add(teacher_slot)

            self.cells[class_slot] = {
                "requirement_id": requirement_id,
                "subject_id": subject_id,
                "teacher_id": teacher_id,
                "block_part": offset + 1,
                "block_size": duration,
            }

        class_load_key = (
            class_id,
            day_index,
        )

        teacher_load_key = (
            teacher_id,
            day_index,
        )

        self.class_day_load[class_load_key] = (
            self.class_day_load.get(
                class_load_key,
                0,
            )
            + duration
        )

        self.teacher_day_load[teacher_load_key] = (
            self.teacher_day_load.get(
                teacher_load_key,
                0,
            )
            + duration
        )

    def unplace(self, requirement, placement):
        requirement_id = requirement["id"]
        class_id = requirement["class_id"]
        subject_id = requirement["subject_id"]
        teacher_id = requirement["teacher_id"]

        day_index = placement["day"]
        start_period = placement["start_period"]
        duration = placement["duration"]

        removed = self.placements[
            requirement_id
        ].pop()

        if removed != placement:
            raise SchedulingError(
                "حدث خطأ داخلي في ترتيب الحصص."
            )

        subject_day_key = (
            class_id,
            subject_id,
            day_index,
        )

        self.subject_used_on_day.remove(
            subject_day_key
        )

        for offset in range(duration):
            period = start_period + offset

            class_slot = (
                class_id,
                day_index,
                period,
            )

            teacher_slot = (
                teacher_id,
                day_index,
                period,
            )

            del self.cells[class_slot]
            self.class_busy.remove(class_slot)
            self.teacher_busy.remove(teacher_slot)

        class_load_key = (
            class_id,
            day_index,
        )

        teacher_load_key = (
            teacher_id,
            day_index,
        )

        self.class_day_load[class_load_key] -= (
            duration
        )

        self.teacher_day_load[teacher_load_key] -= (
            duration
        )

    def validate_solution(self, result):
        cells = result["cells"]

        expected_periods = 0

        for requirement in self.requirements:
            expected_periods += requirement[
                "weekly_periods"
            ]

        if len(cells) != expected_periods:
            raise SchedulingError(
                "عدد الحصص الناتجة غير صحيح."
            )

        requirement_counts = {}
        teacher_slots = set()
        grouped_lessons = {}

        for class_slot in cells:
            class_id = class_slot[0]
            day_index = class_slot[1]
            period = class_slot[2]

            lesson = cells[class_slot]

            requirement_id = lesson[
                "requirement_id"
            ]
            subject_id = lesson["subject_id"]
            teacher_id = lesson["teacher_id"]

            requirement_counts[requirement_id] = (
                requirement_counts.get(
                    requirement_id,
                    0,
                )
                + 1
            )

            teacher_slot = (
                teacher_id,
                day_index,
                period,
            )

            if teacher_slot in teacher_slots:
                raise SchedulingError(
                    "تم اكتشاف تعارض لأحد المعلمين."
                )

            teacher_slots.add(teacher_slot)

            group_key = (
                class_id,
                day_index,
                subject_id,
            )

            if group_key not in grouped_lessons:
                grouped_lessons[group_key] = []

            grouped_lessons[group_key].append(
                {
                    "period": period,
                    "lesson": lesson,
                }
            )

        for requirement in self.requirements:
            requirement_id = requirement["id"]
            expected = requirement["weekly_periods"]
            actual = requirement_counts.get(
                requirement_id,
                0,
            )

            if actual != expected:
                raise SchedulingError(
                    "عدد حصص المتطلب غير صحيح: "
                    + requirement_id
                )

        for group_key in grouped_lessons:
            subject_id = group_key[2]
            subject = self.subjects[subject_id]
            lessons = grouped_lessons[group_key]

            lessons.sort(
                key=lambda item: item["period"]
            )

            if not subject["double"]:
                if len(lessons) != 1:
                    raise SchedulingError(
                        "تكررت مادة عادية للفصل "
                        "نفسه في اليوم نفسه."
                    )
            else:
                if len(lessons) != 2:
                    raise SchedulingError(
                        "التربية الفنية ليست حصة "
                        "مزدوجة كاملة."
                    )

                first = lessons[0]
                second = lessons[1]

                if (
                    second["period"]
                    != first["period"] + 1
                ):
                    raise SchedulingError(
                        "حصتا التربية الفنية "
                        "غير متتاليتين."
                    )

                first_lesson = first["lesson"]
                second_lesson = second["lesson"]

                if (
                    first_lesson["teacher_id"]
                    != second_lesson["teacher_id"]
                ):
                    raise SchedulingError(
                        "معلم الحصة المزدوجة غير متطابق."
                    )

                if (
                    first_lesson["block_part"] != 1
                    or second_lesson["block_part"] != 2
                ):
                    raise SchedulingError(
                        "ترتيب الحصة المزدوجة غير صحيح."
                    )


def print_schedule(
    result,
    teachers,
    subjects,
    classes,
    class_order,
    days,
    periods_per_day,
):
    cells = result["cells"]

    print("")
    print("=" * 70)
    print("الجدول المدرسي النهائي")
    print("=" * 70)

    for day_index in range(len(days)):
        day_name = days[day_index]

        print("")
        print("اليوم -> " + day_name)
        print("-" * 70)

        for period in range(
            1,
            periods_per_day + 1,
        ):
            print("")
            print("  الحصة -> " + str(period))

            for class_id in class_order:
                class_name = classes[class_id]

                class_slot = (
                    class_id,
                    day_index,
                    period,
                )

                lesson = cells.get(class_slot)

                if lesson is None:
                    print(
                        "    الفصل -> "
                        + class_name
                        + " | المادة -> فراغ"
                        + " | المعلم -> -"
                    )
                    continue

                subject = subjects[
                    lesson["subject_id"]
                ]

                teacher_name = teachers[
                    lesson["teacher_id"]
                ]

                line = (
                    "    الفصل -> "
                    + class_name
                    + " | المادة -> "
                    + subject["name"]
                    + " | المعلم -> "
                    + teacher_name
                )

                if subject["double"]:
                    line += (
                        " | حصة مزدوجة -> "
                        + str(lesson["block_part"])
                        + "/"
                        + str(lesson["block_size"])
                    )

                print(line)

    print("")
    print("=" * 70)
    print("نتيجة التحقق")
    print("=" * 70)
    print(
        "نجاح -> لم تتكرر أي مادة عادية "
        "للفصل نفسه في اليوم نفسه."
    )
    print(
        "نجاح -> جميع حصص التربية الفنية "
        "مزدوجة ومتتالية."
    )
    print(
        "نجاح -> لا يوجد معلم في أكثر من "
        "فصل خلال الحصة نفسها."
    )
    print(
        "نجاح -> لا يوجد فصل لديه حصتان "
        "في الوقت نفسه."
    )
    print(
        "عدد محاولات البحث -> "
        + str(result["search_nodes"])
    )
    print("=" * 70)


def build_mock_data():
    teachers = {
        "t_math": "أحمد القحطاني",
        "t_arabic": "سارة الحربي",
        "t_english": "ليلى الشهري",
        "t_science": "خالد العتيبي",
        "t_art": "نورة الدوسري",
        "t_pe": "ماجد المطيري",
    }

    subjects = {
        "math": {
            "name": "الرياضيات",
            "double": False,
        },
        "arabic": {
            "name": "اللغة العربية",
            "double": False,
        },
        "english": {
            "name": "اللغة الإنجليزية",
            "double": False,
        },
        "science": {
            "name": "العلوم",
            "double": False,
        },
        "art": {
            "name": "التربية الفنية",
            "double": True,
        },
        "pe": {
            "name": "التربية البدنية",
            "double": False,
        },
    }

    classes = {
        "class_1a": "الأول / أ",
        "class_1b": "الأول / ب",
        "class_2a": "الثاني / أ",
    }

    class_order = [
        "class_1a",
        "class_1b",
        "class_2a",
    ]

    requirements = []

    for class_id in class_order:
        requirements.append(
            {
                "id": class_id + "_math",
                "class_id": class_id,
                "subject_id": "math",
                "teacher_id": "t_math",
                "weekly_periods": 4,
            }
        )

        requirements.append(
            {
                "id": class_id + "_arabic",
                "class_id": class_id,
                "subject_id": "arabic",
                "teacher_id": "t_arabic",
                "weekly_periods": 4,
            }
        )

        requirements.append(
            {
                "id": class_id + "_english",
                "class_id": class_id,
                "subject_id": "english",
                "teacher_id": "t_english",
                "weekly_periods": 3,
            }
        )

        requirements.append(
            {
                "id": class_id + "_science",
                "class_id": class_id,
                "subject_id": "science",
                "teacher_id": "t_science",
                "weekly_periods": 2,
            }
        )

        requirements.append(
            {
                "id": class_id + "_art",
                "class_id": class_id,
                "subject_id": "art",
                "teacher_id": "t_art",
                "weekly_periods": 2,
            }
        )

        requirements.append(
            {
                "id": class_id + "_pe",
                "class_id": class_id,
                "subject_id": "pe",
                "teacher_id": "t_pe",
                "weekly_periods": 2,
            }
        )

    return (
        teachers,
        subjects,
        classes,
        class_order,
        requirements,
    )


def main():
    days = [
        "الأحد",
        "الاثنين",
        "الثلاثاء",
        "الأربعاء",
        "الخميس",
    ]

    periods_per_day = 6

    (
        teachers,
        subjects,
        classes,
        class_order,
        requirements,
    ) = build_mock_data()

    scheduler = TimetableScheduler(
        teachers=teachers,
        subjects=subjects,
        classes=classes,
        requirements=requirements,
        days=days,
        periods_per_day=periods_per_day,
    )

    result = scheduler.solve()

    print_schedule(
        result=result,
        teachers=teachers,
        subjects=subjects,
        classes=classes,
        class_order=class_order,
        days=days,
        periods_per_day=periods_per_day,
    )


if __name__ == "__main__":
    try:
        main()
    except SchedulingError as error:
        print("")
        print("فشل إنشاء الجدول.")
        print("السبب -> " + str(error))
