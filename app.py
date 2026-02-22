import streamlit as st
import pandas as pd
from io import BytesIO

st.title("AI-Based MBA Timetable Scheduler")
st.write("Conflict-free scheduling with dynamic classroom capacity")

# -------------------------
# PARAMETERS
# -------------------------
SECTION_LIMIT = 70
SESSIONS_PER_SECTION = 20

weeks = list(range(1, 11))
days = list(range(1, 7))    # Mon–Sat
slots = list(range(1, 7))   # 6 slots per day

def get_rooms(week):
    return list(range(1, 11)) if week <= 4 else list(range(1, 5))

# -------------------------
# FILE UPLOAD
# -------------------------
uploaded_file = st.file_uploader("Upload WAI_Data.xlsx", type=["xlsx"])

if uploaded_file:

    xls = pd.ExcelFile(uploaded_file)

    sections = []
    section_students = {}
    student_sections = {}

    # -------------------------
    # CREATE SECTIONS
    # -------------------------
    for sheet in xls.sheet_names:
        df = pd.read_excel(uploaded_file, sheet_name=sheet)
        students = df.iloc[:, 0].dropna().astype(str).tolist()
        n = len(students)

        if n == 0:
            continue

        if n <= SECTION_LIMIT:
            sec = f"{sheet}_A"
            sections.append(sec)
            section_students[sec] = students
        else:
            mid = n // 2
            sec1 = f"{sheet}_A"
            sec2 = f"{sheet}_B"
            sections.extend([sec1, sec2])
            section_students[sec1] = students[:mid]
            section_students[sec2] = students[mid:]

    # student → sections map
    for sec, students in section_students.items():
        for s in students:
            student_sections.setdefault(s, []).append(sec)

    st.success(f"Total Sections Created: {len(sections)}")

    # -------------------------
    # GENERATE TIMETABLE
    # -------------------------
    if st.button("Generate Timetable"):

        # Tracking usage
        room_usage = {}        # (week,day,slot,room)
        student_usage = {}     # student → set of (week,day,slot)
        schedule = []
        section_session_count = {sec: 0 for sec in sections}

        # -------------------------
        # FRONT-LOADING ORDER
        # Weeks 1–4 first (higher capacity)
        # -------------------------
        time_order = []
        for week in weeks:
            for day in days:
                for slot in slots:
                    rooms = get_rooms(week)
                    for room in rooms:
                        time_order.append((week, day, slot, room))

        # Sort so weeks 1–4 come first
        time_order.sort(key=lambda x: x[0])

        # -------------------------
        # GREEDY SCHEDULING
        # -------------------------
        for sec in sections:

            students = section_students[sec]

            for (week, day, slot, room) in time_order:

                if section_session_count[sec] >= SESSIONS_PER_SECTION:
                    break

                # Room available?
                if (week, day, slot, room) in room_usage:
                    continue

                # Student conflict check
                conflict = False
                for s in students:
                    if (week, day, slot) in student_usage.get(s, set()):
                        conflict = True
                        break

                if conflict:
                    continue

                # Assign session
                schedule.append([sec, week, day, slot, room])
                room_usage[(week, day, slot, room)] = sec

                for s in students:
                    student_usage.setdefault(s, set()).add((week, day, slot))

                section_session_count[sec] += 1

        # -------------------------
        # RESULTS
        # -------------------------
        schedule_df = pd.DataFrame(
            schedule,
            columns=["Section", "Week", "Day", "Slot", "Room"]
        )

        # Summary metrics
        total_required = len(sections) * SESSIONS_PER_SECTION
        total_scheduled = len(schedule_df)
        completion_rate = round((total_scheduled / total_required) * 100, 2)

        st.subheader("Scheduling Summary")
        st.write(f"Total Sessions Required: {total_required}")
        st.write(f"Total Sessions Scheduled: {total_scheduled}")
        st.write(f"Completion Rate: {completion_rate}%")

        if completion_rate < 100:
            st.warning("Capacity constraints prevented full scheduling. Increase slots or rooms.")
        else:
            st.success("Complete Conflict-Free Timetable Generated")

        st.dataframe(schedule_df.head(20))

        # -------------------------
        # DOWNLOAD
        # -------------------------
        output = BytesIO()
        schedule_df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            label="Download Final Timetable",
            data=output,
            file_name="Final_Timetable.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
