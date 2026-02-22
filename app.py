import streamlit as st
import pandas as pd
from io import BytesIO
import random

st.title("AI-Based MBA Timetable Scheduler")
st.write("Block-based scheduling with dynamic classroom capacity")

# --------------------------------------------------
# PARAMETERS
# --------------------------------------------------
SECTION_LIMIT = 70
SESSIONS_PER_SECTION = 20
NUM_BLOCKS = 5   # Elective baskets

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
    course_summary = []

    # --------------------------------------------------
    # COURSE-WISE SECTION CREATION
    # --------------------------------------------------
    for sheet in xls.sheet_names:

        df = pd.read_excel(uploaded_file, sheet_name=sheet)
        students = df.iloc[:, 0].dropna().astype(str).tolist()
        students = list(set(students))
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

    st.success(f"Total Sections Created: {len(sections)}")

    summary_df = pd.DataFrame(course_summary,
                              columns=["Course", "Enrollment", "Sections"])
    st.subheader("Course-wise Section Summary")
    st.dataframe(summary_df)

    # --------------------------------------------------
    # ASSIGN BLOCKS (Elective baskets)
    # --------------------------------------------------
    random.seed(42)
    section_block = {}

    for sec in sections:
        section_block[sec] = random.randint(1, NUM_BLOCKS)

    block_df = pd.DataFrame(
        [(sec, section_block[sec]) for sec in sections],
        columns=["Section", "Block"]
    )

    st.subheader("Block Allocation")
    st.dataframe(block_df.head(20))

    # --------------------------------------------------
    # GENERATE TIMETABLE
    # --------------------------------------------------
    if st.button("Generate Timetable"):

        room_usage = {}
        block_usage = {}
        schedule = []
        session_count = {sec: 0 for sec in sections}

        # Time slots
        time_slots = []
        for week in weeks:
            for day in days:
                for slot in slots:
                    for room in get_rooms(week):
                        time_slots.append((week, day, slot, room))

        # Spread sessions across term
        time_slots.sort(key=lambda x: (x[1], x[2], x[0]))

        # Schedule sections block-wise
        for sec in sections:

            block = section_block[sec]

            for (week, day, slot, room) in time_slots:

                if session_count[sec] >= SESSIONS_PER_SECTION:
                    break

                # Room conflict
                if (week, day, slot, room) in room_usage:
                    continue

                # Block conflict (only one course per block at a time)
                if (week, day, slot, block) in block_usage:
                    continue

                # Assign
                schedule.append([
                    sec,
                    block,
                    week,
                    day,
                    slot,
                    room
                ])

                room_usage[(week, day, slot, room)] = sec
                block_usage[(week, day, slot, block)] = sec
                session_count[sec] += 1

        # --------------------------------------------------
        # RESULTS
        # --------------------------------------------------
        schedule_df = pd.DataFrame(schedule, columns=[
            "Section", "Block", "Week", "Day", "Slot", "Room"
        ])

        total_required = len(sections) * SESSIONS_PER_SECTION
        total_scheduled = len(schedule_df)
        completion_rate = round((total_scheduled / total_required) * 100, 2)

        st.subheader("Scheduling Summary")
        st.write("Total Sessions Required:", total_required)
        st.write("Total Sessions Scheduled:", total_scheduled)
        st.write("Completion Rate:", completion_rate, "%")

        if completion_rate == 100:
            st.success("Complete timetable generated with block-based conflict control")
        else:
            st.warning("Partial scheduling — increase number of blocks or rooms")

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
