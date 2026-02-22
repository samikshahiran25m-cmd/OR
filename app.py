import streamlit as st
import pandas as pd
from io import BytesIO

st.title("AI-Based MBA Timetable Scheduler")
st.write("Optimized scheduling with conflict control and dynamic classroom capacity")

# --------------------------------------------------
# PARAMETERS
# --------------------------------------------------
SECTION_LIMIT = 70
SESSIONS_PER_SECTION = 20

weeks = list(range(1, 11))
days = list(range(1, 7))
slots = list(range(1, 7))

def get_rooms(week):
    return list(range(1, 11)) if week <= 4 else list(range(1, 5))

# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------
uploaded_file = st.file_uploader("Upload WAI_Data.xlsx", type=["xlsx"])

if uploaded_file:

    xls = pd.ExcelFile(uploaded_file)

    sections = []
    section_students = {}
    student_sections = {}
    course_summary = []

    # --------------------------------------------------
    # COURSE-WISE SECTION CREATION
    # --------------------------------------------------
    for sheet in xls.sheet_names:
        df = pd.read_excel(uploaded_file, sheet_name=sheet)
        students = df.iloc[:, 0].dropna().astype(str).tolist()
        students = list(set(students))  # remove duplicates
        n = len(students)

        if n == 0:
            continue

        if n <= SECTION_LIMIT:
            sec = f"{sheet}_A"
            sections.append(sec)
            section_students[sec] = students
            course_summary.append([sheet, n, 1])
        else:
            mid = n // 2
            sec1 = f"{sheet}_A"
            sec2 = f"{sheet}_B"
            sections.extend([sec1, sec2])
            section_students[sec1] = students[:mid]
            section_students[sec2] = students[mid:]
            course_summary.append([sheet, n, 2])

    # Student → sections mapping
    for sec, students in section_students.items():
        for s in students:
            student_sections.setdefault(s, []).append(sec)

    st.success(f"Total Courses: {len(course_summary)}")
    st.success(f"Total Sections Created: {len(sections)}")

    summary_df = pd.DataFrame(course_summary,
                              columns=["Course", "Enrollment", "Sections"])
    st.subheader("Course-wise Section Summary")
    st.dataframe(summary_df)

    # --------------------------------------------------
    # GENERATE TIMETABLE
    # --------------------------------------------------
    if st.button("Generate Timetable"):

        # PRIORITY FIX 1: Schedule large sections first
        sections_sorted = sorted(
            sections,
            key=lambda x: len(section_students[x]),
            reverse=True
        )

        room_usage = {}
        student_usage = {}
        schedule = []
        session_count = {sec: 0 for sec in sections_sorted}

        # PRIORITY FIX 2: Distribute sessions across weeks
        time_slots = []
        for week in weeks:
            for day in days:
                for slot in slots:
                    for room in get_rooms(week):
                        time_slots.append((week, day, slot, room))

        # Spread instead of clustering early weeks
        time_slots.sort(key=lambda x: (x[1], x[2], x[0]))

        # --------------------------------------------------
        # GREEDY SCHEDULING
        # --------------------------------------------------
        for sec in sections_sorted:

            students = section_students[sec]

            for (week, day, slot, room) in time_slots:

                if session_count[sec] >= SESSIONS_PER_SECTION:
                    break

                # Room conflict
                if (week, day, slot, room) in room_usage:
                    continue

                # Student conflict
                conflict = False
                for s in students:
                    if (week, day, slot) in student_usage.get(s, set()):
                        conflict = True
                        break

                if conflict:
                    continue

                # Assign
                schedule.append([sec, week, day, slot, room])
                room_usage[(week, day, slot, room)] = sec

                for s in students:
                    student_usage.setdefault(s, set()).add((week, day, slot))

                session_count[sec] += 1

        # --------------------------------------------------
        # RESULTS
        # --------------------------------------------------
        schedule_df = pd.DataFrame(schedule,
                                   columns=["Section", "Week", "Day", "Slot", "Room"])

        total_required = len(sections_sorted) * SESSIONS_PER_SECTION
        total_scheduled = len(schedule_df)
        completion_rate = round((total_scheduled / total_required) * 100, 2)

        st.subheader("Scheduling Summary")
        st.write("Total Sessions Required:", total_required)
        st.write("Total Sessions Scheduled:", total_scheduled)
        st.write("Completion Rate:", completion_rate, "%")

        if completion_rate == 100:
            st.success("Complete conflict-free timetable generated")
        elif completion_rate >= 90:
            st.warning("Near-complete scheduling. Minor conflicts due to high student overlap.")
        else:
            st.error("Low completion due to heavy student overlap. Consider additional slots or rooms.")

        st.subheader("Sample Schedule")
        st.dataframe(schedule_df.head(20))

        # Download
        output = BytesIO()
        schedule_df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            "Download Final Timetable",
            output,
            "Final_Timetable.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
