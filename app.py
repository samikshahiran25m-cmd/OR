import streamlit as st
import pandas as pd
from io import BytesIO

st.title("MBA Timetable Scheduler (2 Section Model)")
st.write("Program-level scheduling with Section A and Section B")

# --------------------------
# PARAMETERS
# --------------------------
SESSIONS_PER_SECTION = 20

weeks = list(range(1, 11))
days = list(range(1, 7))
slots = list(range(1, 7))

def get_rooms(week):
    return list(range(1, 11)) if week <= 4 else list(range(1, 5))

# --------------------------
# FILE UPLOAD
# --------------------------
uploaded_file = st.file_uploader("Upload WAI_Data.xlsx", type=["xlsx"])

if uploaded_file:

    xls = pd.ExcelFile(uploaded_file)

    # --------------------------
    # GET UNIQUE STUDENTS
    # --------------------------
    all_students = set()
    course_students = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(uploaded_file, sheet_name=sheet)
        students = df.iloc[:, 0].dropna().astype(str).tolist()
        course_students[sheet] = students
        all_students.update(students)

    all_students = list(all_students)

    # --------------------------
    # CREATE TWO SECTIONS
    # --------------------------
    mid = len(all_students) // 2
    section_A_students = set(all_students[:mid])
    section_B_students = set(all_students[mid:])

    st.success(f"Total Students: {len(all_students)}")
    st.success("Program divided into Section A and Section B")

    # --------------------------
    # CREATE COURSE-SECTIONS
    # Each course runs for A and B
    # --------------------------
    sections = []
    section_students = {}

    for course in course_students:
        secA = f"{course}_A"
        secB = f"{course}_B"

        # Students of that course belonging to each section
        section_students[secA] = list(
            set(course_students[course]) & section_A_students
        )
        section_students[secB] = list(
            set(course_students[course]) & section_B_students
        )

        sections.extend([secA, secB])

    st.success(f"Total Teaching Sections: {len(sections)}")

    # --------------------------
    # GENERATE TIMETABLE
    # --------------------------
    if st.button("Generate Timetable"):

        room_usage = {}
        student_usage = {}
        schedule = []
        session_count = {sec: 0 for sec in sections}

        # Time priority (front-load early weeks)
        time_slots = []
        for week in weeks:
            for day in days:
                for slot in slots:
                    for room in get_rooms(week):
                        time_slots.append((week, day, slot, room))

        time_slots.sort(key=lambda x: x[0])  # weeks 1–4 first

        # --------------------------
        # GREEDY ASSIGNMENT
        # --------------------------
        for sec in sections:
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

        # --------------------------
        # OUTPUT
        # --------------------------
        schedule_df = pd.DataFrame(
            schedule,
            columns=["Section", "Week", "Day", "Slot", "Room"]
        )

        total_required = len(sections) * SESSIONS_PER_SECTION
        total_scheduled = len(schedule_df)
        completion = round((total_scheduled / total_required) * 100, 2)

        st.subheader("Scheduling Summary")
        st.write("Sessions Required:", total_required)
        st.write("Sessions Scheduled:", total_scheduled)
        st.write("Completion Rate:", completion, "%")

        if completion == 100:
            st.success("Complete timetable generated")
        else:
            st.warning("Capacity constraints prevented full scheduling")

        st.dataframe(schedule_df.head(20))

        # Download
        output = BytesIO()
        schedule_df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            "Download Timetable",
            output,
            "Final_Timetable.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
