# Exam Seating Arrangement System

This project generates seating arrangements for exams based on the given timetable, course-to-roll mapping, room capacities, and other inputs. It automates allocation, checks clashes, applies rules like buffer seats and sparse/dense mode, and produces Excel and PDF outputs.

---

## Features

- Allocate seats by choosing the **largest course first** for each day and slot.
- Try to keep a subject within the **same building** to reduce faculty movement.
- Prefer **adjacent or nearby rooms** for better organization.
- Apply **buffer seats** and **Sparse/Dense** seating logic.
- Detect clashes (if a roll number appears in multiple subjects in the same slot).
- Generate:
  - Per-subject seating Excel files  
  - Summary Excel sheets  
  - Attendance PDFs  
  - Logs for all steps and errors
- Includes:
  - **Command-line script**
  - **Streamlit UI**
  - **Docker support**

---

## Input Files

The Excel file must contain these sheets:

- `in_timetable`
- `in_course_roll_mapping`
- `in_roll_name_mapping`
- `in_room_capacity`

Names and spacing inside columns are automatically cleaned.

---

## Important Rules

### 1. Largest Course First
Courses for a slot are sorted by number of enrolled students. The largest one is allocated first.

### 2. Building Preference
A subject should not be split across buildings unless needed.  
Example to avoid:
```
CS101 in Building B1 room 6101 AND Building B2 room 10502
```

### 3. Adjacent Rooms
Rooms are automatically sorted so that allocations stay close to each other.

### 4. Buffer + Sparse/Dense Logic
- **Dense** → full capacity (minus buffer)
- **Sparse** → half capacity (after buffer)
- Example:
  - Room capacity = 50  
  - Buffer = 5  
  - Dense = 45 seats  
  - Sparse = 22 seats  

### 5. Missing Student Names
If a roll number has no matching name, the student’s name becomes:
```
Unknown Name
```

---

## Outputs

Generated inside the `output/` folder:

- One folder per exam date  
- Subfolders: Morning / Evening  
- Excel seating files  
- `op_overall_seating_arrangement.xlsx`  
- `op_seats_left.xlsx`  
- Attendance PDFs  
- `seating.log` and `errors.txt`  

---

## How to Run (CLI)

```
pip install -r requirements.txt
python3 seating_arrangement.py --input exam.xlsx --buffer 5 --density Sparse
```

---

## How to Run (Streamlit UI)

```
streamlit run streamlit_app.py
```

Open:
```
http://localhost:8501
```

Upload your input file → Generate → Download zip.

---

## Docker Instructions

### Build:
```
docker build -t exam-seating .
```

### Run:
```
docker run -p 8501:8501 exam-seating
```

Then open:
```
http://localhost:8501
```

---

## Logging & Error Handling

- All steps are logged in `seating.log`
- All errors go to `errors.txt`
- The program keeps running even if one subject fails to allocate
- If total students exceed total capacity, the system logs:
```
Cannot allocate due to excess students
```

---

## Simple Summary

You provide the exam timetable + roll mappings + room capacities.  
The system automatically:

- Checks for clashes  
- Allocates seating intelligently  
- Minimizes building changes  
- Applies buffer and density rules  
- Produces clean Excel and PDF files  
- Gives logs for every step  

This keeps exam seating smooth, organized, and error-free.

---

For any improvements or extensions, feel free to modify the modules in the `core/` folder.
