#file to generate attendence sheet
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def _make_card(roll, name, photo_path, no_image_path, styles):
    """Return a small table: [photo | text block] for one student."""
    # Try to load the student's photo, else "no image" placeholder
    img_path = photo_path if (photo_path and os.path.exists(photo_path)) else no_image_path
    try:
        img = Image(img_path, width=40, height=40)
    except Exception:
        # If even placeholder fails, use an empty spacer
        img = Spacer(40, 40)

    # Name line
    name_txt = name if name else "(name not found)"
    name_para = Paragraph(name_txt, styles["Normal"])

    roll_para = Paragraph(f"Roll: {roll}", styles["Normal"])
    sign_para = Paragraph("Sign:__________________", styles["Normal"])

    text_flow = [name_para, roll_para, sign_para]

    card_table = Table([[img, text_flow]], colWidths=[45, 110])
    card_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
    ]))
    return card_table


def build_attendance_pdf(
    out_path,
    date_str,
    shift,
    room_no,
    subject_code,
    subject_name,
    roll_list,
    roll_to_name,
    photos_dir,
    no_image_icon,
    logger=None,
):
    """
    Build a single attendance PDF at `out_path`.
    - date_str: 'YYYY-MM-DD' or similar
    - shift: 'Morning' or 'Evening'
    - room_no: room code string
    - subject_code: e.g. 'CE1101'
    - subject_name: e.g. 'Mathematics - II (MA102)' (can be same as code)
    - roll_list: list of roll numbers (strings)
    - roll_to_name: dict roll->name
    - photos_dir: folder containing ROLL.jpg
    - no_image_icon: path to 'no image available' PNG/JPG
    """

    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        doc = SimpleDocTemplate(out_path, pagesize=A4,
                                leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=40)
        styles = getSampleStyleSheet()
        story = []

        # ----- Header -----
        title = Paragraph("IITP Attendance System", styles["Title"])
        story.append(title)
        story.append(Spacer(1, 6))

        # First info line
        student_count = len(roll_list)
        info1 = (
            f"Date: {date_str} | Shift: {shift} | "
            f"Room No: {room_no} | Student count: {student_count}"
        )
        story.append(Paragraph(info1, styles["Normal"]))
        story.append(Spacer(1, 4))

        # Second info line
        subj_line = f"Subject: {subject_name} ( {subject_code} ) | Stud Present: | Stud Absent:"
        story.append(Paragraph(subj_line, styles["Normal"]))
        story.append(Spacer(1, 10))

        # ----- Cards grid -----
        # Create per-student cards
        cards = []

        def find_photo_path(roll_str: str) -> str | None:
            """
            Try common extensions for this roll; return path if found,
            else None (so _make_card will use no_image_icon).
            """
            roll_str = roll_str.strip()
            for ext in (".jpg", ".jpeg", ".png"):
                candidate = os.path.join(photos_dir, roll_str + ext)
                if os.path.exists(candidate):
                    return candidate
            return None

        for roll in roll_list:
            roll_str = str(roll).strip()
            name = roll_to_name.get(roll_str, "(name not found)")
            photo_path = find_photo_path(roll_str)  # may be None
            card = _make_card(roll_str, name, photo_path, no_image_icon, styles)
            cards.append(card)


        # Lay them out 3 per row (like sample)
        ncols = 3
        rows = []
        row = []
        for card in cards:
            row.append(card)
            if len(row) == ncols:
                rows.append(row)
                row = []
        if row:
            # Pad last row with empty cells
            while len(row) < ncols:
                row.append(Spacer(1, 60))
            rows.append(row)

        table = Table(rows, colWidths=[170, 170, 170])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 1, colors.black),
        ]))

        story.append(table)
        story.append(Spacer(1, 20))

        # Invigilator section
        story.append(Paragraph("Invigilator Name & Signature", styles["Normal"]))
        story.append(Spacer(1, 4))

        inv_table = Table(
            [["Sl No.", "Name", "Signature"]] + [[""] * 3 for _ in range(5)],
            colWidths=[50, 200, 150]
        )
        inv_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        story.append(inv_table)

        doc.build(story)
        if logger:
            logger.info("Created attendance PDF: %s", out_path)

    except Exception as e:
        if logger:
            logger.exception("Failed to build attendance PDF %s: %s", out_path, e)
        else:
            print(f"Error creating PDF {out_path}: {e}")
        # Let caller decide whether to continue or not
        raise
