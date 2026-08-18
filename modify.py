import sys
import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

helpers = '''
            function teacherHasLessonAfter(teacherId, dayId, period) {
                return state.schedule.some(
                    (lesson) =>
                        lesson.teacherId === teacherId &&
                        lessonOccupies(lesson, dayId, period + 1)
                );
            }

            function getWeekRange(dateString) {
                const parts = dateString.split('-');
                if (parts.length !== 3) {
                    const d = new Date();
                    return getWeekRange(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`);
                }
                const d = new Date(parts[0], parts[1] - 1, parts[2]);
                const day = d.getDay();
                const start = new Date(d);
                start.setDate(d.getDate() - day);
                const end = new Date(start);
                end.setDate(start.getDate() + 4);
                
                const format = (date) => {
                    const y = date.getFullYear();
                    const m = String(date.getMonth() + 1).padStart(2, '0');
                    const dayOfMonth = String(date.getDate()).padStart(2, '0');
                    return `${y}-${m}-${dayOfMonth}`;
                };
                return { startStr: format(start), endStr: format(end) };
            }
'''

new_compute_start = '''
            function computeWaitingReport() {
                if (!selectedAbsentTeacherIds.length) {
                    const selected =
                        $("#absentTeacherSelect").value;

                    if (selected) {
                        selectedAbsentTeacherIds.push(
                            selected
                        );

                        renderAbsentTeacherChips();
                    }
                }

                if (!selectedAbsentTeacherIds.length) {
                    showToast(
                        "أضف معلماً غائباً واحداً على الأقل.",
                        "error"
                    );
                    return null;
                }

                const dayId = $("#reportDaySelect").value;
                const dateValue = $("#reportDateInput").value || new Date().toISOString().split("T")[0];

                const { startStr, endStr } = getWeekRange(dateValue);
                const currentWeekWaitingCounts = {};
                (state.waitingHistory || []).filter(h => h.date >= startStr && h.date <= endStr).forEach(entry => {
                    if (entry.report && entry.report.groups) {
                        entry.report.groups.forEach(group => {
                            group.rows.forEach(row => {
                                let tId = row.waitingTeacherId;
                                if (!tId && row.waitingTeacher) {
                                    const found = state.teachers.find(t => t.name === row.waitingTeacher);
                                    if (found) tId = found.id;
                                }
                                if (tId) {
                                    currentWeekWaitingCounts[tId] = (currentWeekWaitingCounts[tId] || 0) + 1;
                                }
                            });
                        });
                    }
                });

                const absentSet = new Set(
                    selectedAbsentTeacherIds
                );

                const reserved = new Set();
                const assignedToday = {};
                const weeklyLoads = Object.fromEntries(
                    state.teachers.map((teacher) => [
                        teacher.id,
                        teacherWeeklyLoad(teacher.id)
                    ])
                );
'''

search_part1 = r'            function computeWaitingReport\(\) \{[\s\S]*?teacherWeeklyLoad\(teacher\.id\)\n\s*\]\)\n\s*\);'
replacement1 = helpers + new_compute_start.lstrip('\n')

content = re.sub(search_part1, replacement1, content)

search_part2 = r'\.sort\([\s\S]*?first\.name\.localeCompare\([\s\S]*?\"ar\"[\s\S]*?\)\n\s*\);\n\s*\}\n\s*\);'

new_sort = '''.sort((first, second) => {
                                                    const firstScore = Number(currentWeekWaitingCounts[first.id] || 0) + Number(assignedToday[first.id] || 0) + (weeklyLoads[first.id] || 0);
                                                    const secondScore = Number(currentWeekWaitingCounts[second.id] || 0) + Number(assignedToday[second.id] || 0) + (weeklyLoads[second.id] || 0);
                                                    
                                                    const firstHasAfter = teacherHasLessonAfter(first.id, dayId, period) ? 0 : 1;
                                                    const secondHasAfter = teacherHasLessonAfter(second.id, dayId, period) ? 0 : 1;

                                                    return (
                                                        firstScore - secondScore ||
                                                        firstHasAfter - secondHasAfter ||
                                                        first.name.localeCompare(
                                                            second.name,
                                                            "ar"
                                                        )
                                                    );
                                                });'''

content = re.sub(search_part2, new_sort, content)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced successfully")
