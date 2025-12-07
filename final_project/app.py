# app.py
import streamlit as st
import tempfile,os,shutil
import logging

from seating_allocator import SeatingAllocator

def setup_logging(logfile='seating.log'):
    logger = logging.getLogger('seating')

    # Prevent multiple handlers when Streamlit reloads
    if getattr(logger, "_is_configured", False):
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

    # 1) Main log file (INFO + ERROR + DEBUG)
    fh = logging.FileHandler(logfile, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 2) Console output (only for display in Streamlit terminal)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Mark as configured to avoid re-attaching handlers
    logger._is_configured = True

    return logger

def close_logger(logger):
    """Release file handles so TemporaryDirectory can clean up on Windows."""
    if logger is None:
        return
    # Copy the list so we can modify logger.handlers while iterating
    for h in list(logger.handlers):
        try:
            h.flush()
        except Exception:
            pass
        try:
            h.close()
        except Exception:
            pass
        logger.removeHandler(h)


def run_allocation(uploaded_file, buffer, density):
    # This temp dir (and everything inside) will be deleted automatically
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save uploaded Excel to a temp path
        excel_path = os.path.join(tmpdir, uploaded_file.name)
        with open(excel_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Create output folder FIRST
        outdir = os.path.join(tmpdir, "output")
        os.makedirs(outdir, exist_ok=True)

        # Now it's safe to create log files inside outdir
        logger = setup_logging(
            logfile=os.path.join(outdir, "seating.log"),
        )

        # Run allocation pipeline
        alloc = SeatingAllocator(
            input_file=excel_path,
            buffer=buffer,
            density=density,
            outdir=outdir,
            logger=logger,
        )
        with st.spinner("Reading excel sheet...", show_time=True):
            alloc.load_inputs()
        st.success("Done: Reading excel sheet...")
        with st.spinner("Allocation in progress...", show_time=True):
            alloc.allocate_all_days()
        st.success("Done: Allocation in progress...")
        with st.spinner("Saving outputs...", show_time=True):
            alloc.write_outputs()
        st.success("Done: Saving outputs...")

        # Generate attendance PDFs
        photos_dir = "photos"  # keep this dir next to the app
        no_image_icon = os.path.join(photos_dir, "no_image_available.jpg")
        alloc.generate_attendance_pdfs(photos_dir, no_image_icon)

        # Zip the entire output folder
        zip_base = os.path.join(tmpdir, "output")
        with st.spinner("Compressing output to zip..", show_time=True):
            shutil.make_archive(zip_base, "zip", outdir)
        zip_path = zip_base + ".zip"

        # Read the zip into memory BEFORE TemporaryDirectory is cleaned up
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        # Very important on Windows: release seating.log
        close_logger(logger)

        # Return bytes, not a path inside the soon-to-be-deleted temp dir
        return zip_bytes


st.title("Exam scheduler")

uploaded = st.file_uploader("Upload input Excel file", type=["xlsx"])
buffer = st.number_input("Buffer seats per room", 0, 50, 0)
density = st.radio("Seating density", ["Dense", "Sparse"])

if st.button("Generate schedule") and uploaded:
    with st.spinner("Generating schedule..."):
        try:
            zip_bytes = run_allocation(uploaded, buffer, density)
            st.download_button(
                "Download schedule",
                data=zip_bytes,
                file_name="schedule.zip",
                mime="application/zip",
            )
        except Exception as e:
            st.error(f"Error: {e}")
else:
    if not uploaded:
        st.warning("Please upload an Excel file.")