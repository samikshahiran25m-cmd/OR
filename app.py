import streamlit as st
import pandas as pd
from io import BytesIO

st.title("MBA Timetable Scheduler")
st.write("AI-assisted scheduling tool for classroom and student conflict management")

# Parameters
SECTION_LIMIT = 70
SESSIONS_PER_SECTION = 20

weeks = list(range(1,11))
days = list(range(1,7))   # Mon-Sat
slots = list(range(1,7))  # 6 slots per day

def get_rooms(week):
    if week <= 4:
        return list(range(1,11))
    else:
        return list(range(1,5))

# File Upload
uploaded_file = st.file_uploader("Upload Student Course Excel", type=["xlsx"])

if uploaded_file:

    xls = pd.ExcelFile(uploaded_file)

    sections = []
    student_section_map = {}

    # -----------------------------
    # Section Creation
    # -----------------------------
    for sheet in xls.sheet_names:
        df = pd.read_excel(uploaded_file, sheet_name=sheet)
        students = df.iloc[:,0].dropna().astype(str).tolist()
        enrollment = len(students)

        if enrollment == 0:
            continue

        if enrollment <= SECTION_LIMIT:
            sec = f"{sheet}_A"
            sections.append(sec)
            for s in students:
                student_section_map.setdefault(s, []).append(sec)

        else:
            mid = enrollment // 2
            sec1 = f"{sheet}_A"
            sec2 = f"{sheet}_B"

            sections.extend([sec1, sec2])

            for s in students[:mid]:
                student_section_map.setdefault(s, []).append(sec1)
            for s in students[mid:]:
                student_section_map.setdefault(s, []).append(sec2)

    st.success(f"Total Sections Created: {len(sections)}")

    # -----------------------------
    # Scheduling Button
    # -----------------------------
    if st.button("Generate Timetable"):

        schedule = []
        room_usage = {}
        student_usage = {}

        for sec in sections:
            sessions_assigned = 0

            for week in weeks:
                rooms = get_rooms(week)

                for day in days:
                    for slot in slots:
                        for room in rooms:

                            key_room = (week, day, slot, room)
                            key_student = (week, day, slot)

                            # Room available?
                            if key_room in room_usage:
                                continue

                            # Student conflict?
                            conflict = False
                            for student, sec_list in student_section_map.items():
                                if sec in sec_list:
                                    if key_student in student_usage.get(student, set()):
                                        conflict = True
                                        break

                            if conflict:
                                continue

                            # Assign
                            schedule.append([sec, week, day, slot, room])
                            room_usage[key_room] = sec

                            for student, sec_list in student_section_map.items():
                                if sec in sec_list:
                                    student_usage.setdefault(student, set()).add(key_student)

                            sessions_assigned += 1

                            if sessions_assigned >= SESSIONS_PER_SECTION:
                                break
                        if sessions_assigned >= SESSIONS_PER_SECTION:
                            break
                    if sessions_assigned >= SESSIONS_PER_SECTION:
                        break
                if sessions_assigned >= SESSIONS_PER_SECTION:
                    break

        schedule_df = pd.DataFrame(schedule, columns=[
            "Section","Week","Day","Slot","Room"
        ])

        st.success("Timetable Generated")
        st.dataframe(schedule_df.head())

        # Download
        output = BytesIO()
        schedule_df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            label="Download Timetable",
            data=output,
            file_name="Final_Timetable.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )