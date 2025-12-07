#file for seat allocation
import os
import pandas as pd
from collections import defaultdict
from attendance_pdf import build_attendance_pdf

def read_excel_file(path, logger=None):
    try:
        xls = pd.ExcelFile(path)
    except Exception:
        if logger:
            logger.exception('Unable to open Excel file: %s', path)
        raise

    sheets = {name: xls.parse(name) for name in xls.sheet_names}
    if logger:
        logger.debug('Read sheets: %s', xls.sheet_names)
    return sheets


def write_output_excel(filepath, df):
    df.to_excel(filepath, index=False)


class SeatingAllocator:
    def __init__(self, input_file, buffer=0, density='Dense', outdir='output', logger=None):
        self.input_file = input_file
        self.buffer = int(buffer)
        self.density = density  # 'Dense' or 'Sparse' (case-insensitive)
        self.outdir = outdir
        self.logger = logger

        # loaded data
        self.sheets = {}
        self.timetable = None  # list of dicts: [{Date, Day, Morning:[...], Evening:[...]}]
        self.course_roll_map = None  # dataframe from in_course_roll_mapping
        self.roll_name_map = {}  # roll -> name
        self.subject_rolls = defaultdict(list)  # course_code -> [rollno, ...]
        self.room_capacity = []  # list of dicts with building, room_code, capacity, capacity_effective
        self.allocations = defaultdict(list)  # slot_key -> list of allocations

        os.makedirs(self.outdir, exist_ok=True)

    def load_inputs(self):
        """Read and process required input sheets:
           - in_timetable (Date, Day, Morning, Evening)
           - in_course_roll_mapping (rollno, register_sem, schedule_sem, course_code)
           - in_roll_name_mapping (Roll, Name)
           - in_room_capacity (Room No., Exam Capacity, Block [, sparse...])
        """
        try:
            self.logger.info("Loading Excel input file: %s", self.input_file)
            self.sheets = read_excel_file(self.input_file, logger=self.logger)

            # -------- in_timetable --------
            if 'in_timetable' not in self.sheets:
                raise ValueError("Missing required sheet: in_timetable")

            df_tt = self.sheets['in_timetable']
            required_cols = ['Date', 'Day', 'Morning', 'Evening']
            for col in required_cols:
                if col not in df_tt.columns:
                    raise ValueError(f"in_timetable missing required column: {col}")

            # build self.timetable as list of dicts (keeps NO EXAM explicitly)
            self.timetable = []
            for _, row in df_tt.iterrows():
                date = str(row['Date']).strip()
                day = str(row['Day']).strip()

                def parse_cell(raw):
                    if pd.isna(raw):
                        return ['NO EXAM']
                    text = str(raw).strip()
                    if text.upper() == 'NO EXAM' or text == '':
                        return ['NO EXAM']
                    return [s.strip() for s in text.split(';') if s.strip()]

                morning_subjects = parse_cell(row['Morning'])
                evening_subjects = parse_cell(row['Evening'])

                self.timetable.append({
                    'Date': date,
                    'Day': day,
                    'Morning': morning_subjects,
                    'Evening': evening_subjects
                })
            self.logger.info("Loaded timetable with %d days.", len(self.timetable))

            # -------- in_roll_name_mapping --------
            if 'in_roll_name_mapping' in self.sheets:
                df = self.sheets['in_roll_name_mapping']
                # normalize column names
                cols = {c.lower(): c for c in df.columns}

                if 'roll' in cols and 'name' in cols:
                    roll_col, name_col = cols['roll'], cols['name']
                    for _, r in df.iterrows():
                        roll = str(r[roll_col]).strip()
                        name = str(r[name_col]).strip() or "Unknown Name"
                        if roll:
                            self.roll_name_map[roll] = name
                else:
                    self.logger.warning("'in_roll_name_mapping' missing Roll/Name columns; defaulting names.")

                self.logger.info("Loaded %d roll-name entries.", len(self.roll_name_map))

            else:
                self.logger.warning("'in_roll_name_mapping' sheet missing; names default to 'Unknown Name'.")

            # -------- in_course_roll_mapping --------
            if 'in_course_roll_mapping' not in self.sheets:
                raise ValueError("Missing required sheet: in_course_roll_mapping")
            df_map = self.sheets['in_course_roll_mapping']
            # expected columns: rollno, course_code
            if not {'rollno', 'course_code'}.issubset({c.lower() for c in df_map.columns}):
                # try fuzzy match: lowercase mapping
                cols_lower = {c.lower(): c for c in df_map.columns}
                if 'rollno' in cols_lower and 'course_code' in cols_lower:
                    roll_col = cols_lower['rollno']
                    course_col = cols_lower['course_code']
                else:
                    raise ValueError("in_course_roll_mapping must contain columns: rollno, course_code")
            else:
                cols_lower = {c.lower(): c for c in df_map.columns}
                roll_col = cols_lower['rollno']
                course_col = cols_lower['course_code']

            # store df_map for clash checks and also populate subject_rolls
            self.course_roll_map = df_map
            count = 0
            for _, r in df_map.iterrows():
                roll = str(r[roll_col]).strip()
                subj = str(r[course_col]).strip()
                if roll and subj:
                    self.subject_rolls[subj].append(roll)
                    count += 1
            self.logger.info("Loaded course-roll mapping: %d mappings, %d distinct subjects.", count, len(self.subject_rolls))

            # -------- in_room_capacity --------
            if 'in_room_capacity' not in self.sheets:
                raise ValueError("Missing required sheet: in_room_capacity")
            df_room = self.sheets['in_room_capacity']
            # required columns: Room No., Exam Capacity, Block
            # attempt to find matching names (strip case)
            col_map = {c.strip().lower(): c for c in df_room.columns}
            required_room_cols = ['room no.', 'exam capacity', 'block']
            for rc in required_room_cols:
                if rc not in col_map:
                    raise ValueError("in_room_capacity must contain columns: 'Room No.', 'Exam Capacity', 'Block' (case-insensitive)")

            room_col = col_map['room no.']
            cap_col = col_map['exam capacity']
            block_col = col_map['block']

            self.room_capacity = []
            for _, r in df_room.iterrows():
                room_code = str(r[room_col]).strip()
                try:
                    capacity = int(r[cap_col])
                except Exception:
                    # try to coerce
                    capacity = int(float(r[cap_col]))
                block = str(r[block_col]).strip()
                eff = self.effective_capacity(capacity)
                self.room_capacity.append({
                    'building': block,
                    'room_code': room_code,
                    'capacity': capacity,
                    'capacity_effective': eff
                })
            self.logger.info("Loaded %d rooms from in_room_capacity.", len(self.room_capacity))

            self.logger.info("All required sheets loaded successfully.")

        except Exception as e:
            self.logger.exception("Error loading inputs: %s", e)
            raise
    # ---------------------------------------------------------------------
    def effective_capacity(self, capacity):
        """Return adjusted capacity based on buffer and density type."""
        try:
            adjusted = max(0, int(capacity) - int(self.buffer))
        except Exception:
            adjusted = max(0, int(float(capacity)) - int(self.buffer))
        if str(self.density).strip().lower() == 'sparse':
            return adjusted // 2
        return adjusted

    # ---------------------------------------------------------------------
    def check_clashes(self):
        """Check if any student (rollno) appears in multiple courses on same date + slot."""
        try:
            if self.course_roll_map is None:
                raise ValueError("course_roll_map not loaded; cannot check clashes.")

            # Normalize names for lookups
            df_map = self.course_roll_map
            # find actual column names
            cols_lower = {c.lower(): c for c in df_map.columns}
            roll_col = cols_lower.get('rollno', None)
            course_col = cols_lower.get('course_code', None)
            if not roll_col or not course_col:
                raise ValueError("in_course_roll_mapping must contain rollno and course_code columns")

            conflict_found = False

            for entry in self.timetable:
                date = entry['Date']
                for slot_name, subjects in [('Morning', entry['Morning']), ('Evening', entry['Evening'])]:
                    if subjects == ['NO EXAM']:
                        continue

                    # map subject -> set(rolls)
                    subj_rolls = {}
                    for subj in subjects:
                        subj = str(subj).strip()
                        rolls = set(
                            str(x).strip()
                            for x in df_map.loc[df_map[course_col].astype(str).str.strip() == subj, roll_col].dropna()
                        )
                        subj_rolls[subj] = rolls

                    # pairwise intersection
                    subjects_list = list(subj_rolls.keys())
                    for i in range(len(subjects_list)):
                        for j in range(i + 1, len(subjects_list)):
                            a, b = subjects_list[i], subjects_list[j]
                            inter = subj_rolls[a] & subj_rolls[b]
                            if inter:
                                conflict_found = True
                                for r in inter:
                                    msg = f"Clash on {date} {slot_name}: {a} & {b} -> {r}"
                                    self.logger.error(msg)

            if conflict_found:
                print("⚠️ Clash detected — check log for details.")
            else:
                self.logger.info("No clashes found across timetable.")

        except Exception as e:
            self.logger.exception("Error during clash checking: %s", e)
            raise

    # ---------------------------------------------------------------------
    def allocate_subject(self, subject, rolls, room_pool):
        """Allocate rolls (list) for a single subject into the available room_pool.
           room_pool is a list of dicts with capacity_effective key which is mutable in-place.
           Returns: (assignments, leftover)
             assignments: list of {'building','room','rolls'}
             leftover: list of rollnos not allocated
        """
        try:
            assignments = []
            pending = list(rolls)
            # sort rooms by remaining effective capacity descending (to minimize number of rooms used)
            sorted_rooms = sorted(room_pool, key=lambda r: r.get('capacity_effective', 0), reverse=True)

            for room in sorted_rooms:
                if not pending:
                    break
                cap = int(room.get('capacity_effective', 0))
                if cap <= 0:
                    continue
                take = min(len(pending), cap)
                to_assign = pending[:take]
                pending = pending[take:]
                assignments.append({
                    'building': room.get('building'),
                    'room': room.get('room_code'),
                    'rolls': to_assign
                })
            return assignments, pending
        except Exception as e:
            self.logger.exception("Error in allocate_subject for %s: %s", subject, e)
            raise
    # ---------------------------------------------------------------------
    def allocate_all_days(self):
        """Iterate through timetable and allocate all subjects in each slot to rooms."""
        try:
            # do clash check first (log conflicts but continue)
            self.check_clashes()

            for entry in self.timetable:
                date = entry['Date']
                day = entry['Day']
                # folder name: convert date like 30-04-2016 -> 30_04_2016 (replace non-alnum with _)
                # Remove unwanted time (like "00:00:00")
                date_only = str(date).split()[0]

                date_folder_name = (
                    date_only
                    .replace("-", "_")
                    .replace("/", "_")
                )

                date_folder = os.path.join(self.outdir, date_folder_name)
                morning_folder = os.path.join(date_folder, 'Morning')
                evening_folder = os.path.join(date_folder, 'Evening')
                os.makedirs(morning_folder, exist_ok=True)
                os.makedirs(evening_folder, exist_ok=True)

                for slot_name, subjects in [('Morning', entry['Morning']), ('Evening', entry['Evening'])]:
                    slot_folder = morning_folder if slot_name == 'Morning' else evening_folder

                    if subjects == ['NO EXAM']:
                        # create a small NO_EXAM.txt file for clarity
                        try:
                            with open(os.path.join(slot_folder, 'NO_EXAM.txt'), 'w', encoding='utf-8') as fh:
                                fh.write('NO EXAM')
                        except Exception:
                            self.logger.exception("Unable to write NO_EXAM.txt in %s", slot_folder)
                        continue

                    # fresh copy of room pool for this slot (so each slot starts with full capacities)
                    room_pool = [dict(r) for r in self.room_capacity]

                    # sort subjects by descending size (help packing big ones first)
                    subjects_sizes = [(s, len(self.subject_rolls.get(s, []))) for s in subjects]
                    subjects_sizes.sort(key=lambda x: x[1], reverse=True)

                    for subj, size in subjects_sizes:
                        subj = str(subj).strip()
                        rolls = self.subject_rolls.get(subj, [])
                        if not rolls:
                            self.logger.warning("Subject %s on %s %s has no rolls listed.", subj, date, slot_name)
                            # still create a small empty file to indicate subject present
                            try:
                                df_empty = pd.DataFrame(columns=['Room', 'Rolls (semicolon separated)', 'Count'])
                                df_empty.to_excel(os.path.join(slot_folder, f"{subj}.xlsx"), index=False)
                            except Exception:
                                self.logger.exception("Unable to write empty subject file for %s", subj)
                            continue

                        # allocate this subject into room_pool
                        assignments, leftover = self.allocate_subject(subj, rolls, room_pool)
                        if leftover:
                            # Not enough capacity in this slot across all rooms
                            msg = f"Cannot allocate {len(leftover)} students for {subj} on {date} {slot_name}"
                            self.logger.error(msg)
                            raise RuntimeError("Cannot allocate due to excess students across rooms")

                        # update room_pool capacities and record allocations
                        for a in assignments:
                            # deduct capacity
                            for r in room_pool:
                                if r['room_code'] == a['room'] and r['building'] == a['building']:
                                    r['capacity_effective'] = max(0, r.get('capacity_effective', 0) - len(a['rolls']))
                                    break

                            # register allocation in master dict
                            slot_key = f"{date}_{slot_name}"
                            self.allocations[slot_key].append({
                                'date': date,
                                'day': day,
                                'slot': slot_name,
                                'subject': subj,
                                'building': a['building'],
                                'room': a['room'],
                                'rolls': a['rolls']
                            })

                        # write subject file inside the slot folder (one xlsx per subject)
                        try:
                            rows = []
                            for a in assignments:
                                rows.append({
                                    'Room': a['room'],
                                    'Rolls (semicolon separated)': ';'.join(a['rolls']),
                                    'Count': len(a['rolls'])
                                })
                            df_sub = pd.DataFrame(rows)
                            out_path = os.path.join(slot_folder, f"{subj}.xlsx")
                            df_sub.to_excel(out_path, index=False)
                        except Exception:
                            self.logger.exception("Failed to write subject file for %s in %s", subj, slot_folder)

                    self.logger.info("Allocated slot %s for date %s (subjects: %s)", slot_name, date, ','.join(subjects))

        except Exception as e:
            self.logger.exception("Error allocating all days: %s", e)
            raise

    # ---------------------------------------------------------------------
    def write_outputs(self):
        """Write:
        1) master overall seating file
        2) per-day, per-slot seats-left file (multi-sheet XLSX)
        """
        try:
            # -------- 1. Overall seating arrangement (same as before) ----------
            rows = []
            for slot_key, allocs in self.allocations.items():
                for a in allocs:
                    rows.append({
                        "Date": a["date"],
                        "Day": a.get("day", ""),
                        "course_code": a["subject"],
                        "Room": a["room"],
                        "Allocated_students_count": len(a["rolls"]),
                        "Roll_list (semicolon separated)": ";".join(a["rolls"]),
                    })

            df_overall = pd.DataFrame(rows)
            op1 = os.path.join(self.outdir, "op_overall_seating_arrangement.xlsx")
            df_overall.to_excel(op1, index=False)

            # -------- 2. Seats left: per date & slot in one workbook ----------

            # Group allocations by (date, slot) first
            from collections import defaultdict

            grouped = defaultdict(list)  # (date, slot) -> list[alloc]
            for slot_key, allocs in self.allocations.items():
                for a in allocs:
                    key = (str(a["date"]), str(a["slot"]))
                    grouped[key].append(a)

            op2 = os.path.join(self.outdir, "op_seats_left.xlsx")

            with pd.ExcelWriter(op2, engine="xlsxwriter") as writer:
                for (date, slot), allocs in grouped.items():
                    # count students per room for this (date, slot)
                    room_allotted = {r["room_code"]: 0 for r in self.room_capacity}
                    for a in allocs:
                        rcode = a["room"]
                        room_allotted[rcode] = room_allotted.get(rcode, 0) + len(a["rolls"])

                    seats_rows = []
                    for r in self.room_capacity:
                        allotted = room_allotted.get(r["room_code"], 0)
                        vacant = max(0, r["capacity"] - allotted)
                        seats_rows.append({
                            "Room No.": r["room_code"],
                            "Exam Capacity": r["capacity"],
                            "Block": r["building"],
                            "Alloted": allotted,
                            "Vacant (B-C)": vacant,
                        })

                    df_seats = pd.DataFrame(seats_rows)

                    # Sheet name: e.g. 2016_05_01_Morning (must be <=31 chars, no /:\*?[])
                    date_only = str(date).split()[0].replace("-", "_").replace("/", "_")
                    sheet_name = f"{date_only}_{slot}"
                    # Clean up characters not allowed in sheet names
                    bad = '[]:*?/\\'
                    for ch in bad:
                        sheet_name = sheet_name.replace(ch, "_")
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]

                    df_seats.to_excel(writer, sheet_name=sheet_name, index=False)

            self.logger.info("Wrote output files: %s and %s", op1, op2)

        except Exception as e:
            self.logger.exception("Error writing outputs: %s", e)
            raise

        # ---------------------------------------------------------------------
        # ---------------------------------------------------------------------
    def generate_attendance_pdfs(self, photos_dir, no_image_icon, pdf_outdir=None):
        """
        Generate one attendance PDF per (date, slot, room, subject).

        photos_dir: folder containing ROLL.jpg (e.g. 'photos/')
        no_image_icon: path to generic 'no image available' icon
        pdf_outdir: root folder for PDFs (default: <self.outdir>/attendance)
        """
        # Decide where PDFs will be stored
        if pdf_outdir is None:
            pdf_outdir = os.path.join(self.outdir, "attendance")

        # Make sure the folder actually exists
        os.makedirs(pdf_outdir, exist_ok=True)

        self.logger.info("Generating attendance PDFs in %s", pdf_outdir)

        # Group allocations by (date, slot, room, subject)
        grouped = {}  # key -> list of rolls
        for slot_key, allocs in self.allocations.items():
            for a in allocs:
                key = (
                    str(a["date"]),
                    str(a["slot"]),
                    str(a["room"]),
                    str(a["subject"]),
                )
                grouped.setdefault(key, []).extend(a["rolls"])

        def _sanitize(s: str) -> str:
            """Remove characters not allowed in Windows filenames."""
            bad = '<>:"/\\|?*'
            for ch in bad:
                s = s.replace(ch, "_")
            return s.replace(" ", "_")

        for (date, slot, room, subj), rolls in grouped.items():
            # Keep order but also ensure unique
            rolls_unique = list(dict.fromkeys(rolls))

            # Build filename: YYYY_MM_DD_<SESSION>_<ROOM>_<SUBCODE>.pdf
           # Remove unwanted time portion like "00:00:00"
            date_only = str(date).split()[0]

            date_sanitized = (
                date_only
                .replace("-", "_")
                .replace("/", "_")
                .replace(" ", "_")
            )


            filename = f"{date_sanitized}_{slot}_{room}_{subj}.pdf"
            filename = _sanitize(filename)  # extra safety
            out_path = os.path.join(pdf_outdir, filename)

            # Subject name: if you have a mapping, use it; for now just use code
            subject_name = subj
            date_clean = str(date).split()[0]

            try:
                build_attendance_pdf(
                    out_path=out_path,
                    date_str=date_clean,
                    shift=slot,
                    room_no=room,
                    subject_code=subj,
                    subject_name=subject_name,
                    roll_list=rolls_unique,
                    roll_to_name=self.roll_name_map,
                    photos_dir=photos_dir,
                    no_image_icon=no_image_icon,
                    logger=self.logger,
                )
                self.logger.info("Created attendance PDF: %s", out_path)
            except Exception:
                # Don't stop the whole run; just log and continue.
                self.logger.error(
                    "Error while generating attendance for %s %s %s %s",
                    date, slot, room, subj,
                )
                continue

        self.logger.info("Finished generating all attendance PDFs.")