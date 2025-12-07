import streamlit as st
import pandas as pd
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def count_faculty_columns(df, cgpa_col='CGPA'):
    """Dynamically count faculty columns after CGPA"""
    try:
        idx = df.columns.get_loc(cgpa_col)
        faculty_cols = df.columns[idx + 1:].tolist()
        logger.info(f"Found {len(faculty_cols)} faculty columns: {faculty_cols}")
        return faculty_cols
    except Exception as e:
        logger.error(f"Error counting faculty columns: {str(e)}")
        raise

def allocate_students(df, cgpa_col='CGPA'):
    """
    Allocate students to faculties using mod n algorithm:
    1. Sort students by CGPA (descending)
    2. Use mod n to determine which faculty column to allocate
    3. In each cycle of n students, each faculty gets exactly one student
    """
    try:
        # Sort by CGPA descending
        df_sorted = df.sort_values(by=cgpa_col, ascending=False).reset_index(drop=True)
        logger.info(f"Sorted {len(df_sorted)} students by CGPA (descending)")

        # Get faculty columns dynamically
        faculty_cols = count_faculty_columns(df_sorted, cgpa_col)
        n_faculties = len(faculty_cols)

        allocations = []

        # Allocate: i-th student (after sorting) gets faculty at position (i mod n)
        for i in range(len(df_sorted)):
            row = df_sorted.iloc[i]

            # Faculty column index based on mod n
            fac_index = i % n_faculties
            allocated_faculty = faculty_cols[fac_index]

            allocations.append({
                'Roll': row['Roll'],
                'Name': row['Name'],
                'Email': row['Email'],
                'CGPA': row['CGPA'],
                'Allocated': allocated_faculty
            })

        alloc_df = pd.DataFrame(allocations)
        logger.info(f"Successfully allocated {len(alloc_df)} students")
        return alloc_df

    except Exception as e:
        logger.error(f"Error in allocation: {str(e)}")
        raise

def compute_faculty_preference_stats(df, cgpa_col='CGPA'):
    """
    Compute statistics of how many times each faculty was selected at each preference level (1-n)
    """
    try:
        faculty_cols = count_faculty_columns(df, cgpa_col)
        n_faculties = len(faculty_cols)

        # Initialize statistics dictionary
        pref_stats = {}
        for fac in faculty_cols:
            pref_stats[fac] = {i: 0 for i in range(1, n_faculties + 1)}

        # Count preferences
        for _, row in df.iterrows():
            for fac in faculty_cols:
                try:
                    pref_value = int(row[fac])
                    if 1 <= pref_value <= n_faculties:
                        pref_stats[fac][pref_value] += 1
                except Exception as e:
                    logger.warning(f"Invalid preference value for faculty {fac}: {row[fac]}")

        # Create DataFrame
        pref_df = pd.DataFrame(pref_stats).T
        pref_df.columns = [f'Count Pref {i}' for i in range(1, n_faculties + 1)]
        pref_df.index.name = 'Fac'
        pref_df = pref_df.reset_index()

        logger.info("Successfully computed faculty preference statistics")
        return pref_df

    except Exception as e:
        logger.error(f"Error computing preference stats: {str(e)}")
        raise

# Streamlit UI
st.set_page_config(page_title="BTP/MTP Faculty Allocation", layout="wide")

st.title("BTP/MTP Faculty Allocation System")
st.markdown("""
This application allocates students to faculties based on:
- **Dynamic faculty detection**
- **CGPA sorted in (descending order)**
- **Round-robin Allocation**
""")

st.divider()

# File upload
uploaded_file = st.file_uploader(
    "Upload Student Preferences CSV File",
    type=['csv'],
    help="CSV file with columns: Roll, Name, Email, CGPA, followed by faculty preference columns"
)

if uploaded_file is not None:
    try:
        # Read the input file
        input_df = pd.read_csv(uploaded_file)
        logger.info(f"File uploaded: {uploaded_file.name}, Shape: {input_df.shape}")

        st.success(f"File uploaded successfully!")

        # Display input data preview
        with st.expander("Visualize Student Preferences"):
            st.dataframe(input_df.head(10))

        # Process button
        if st.button("Initialize allocation", type="primary"):
            with st.spinner("Processing allocation..."):
                try:
                    # Perform allocation
                    allocation_df = allocate_students(input_df)
                    pref_stats_df = compute_faculty_preference_stats(input_df)

                    # st.divider()
                    # st.subheader("Summary Statistics")

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Number of Students", len(allocation_df))
                    with col_b:
                        st.metric("Number of Faculties", len(count_faculty_columns(input_df)))
                    with col_c:
                        st.metric("Average CGPA", f"{allocation_df['CGPA'].mean():.2f}")

                    st.success("Allocation completed successfully!")

                    # Display results
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Allocation Results")
                        # st.dataframe(allocation_df, height=400)

                        # Download allocation
                        csv1 = allocation_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Allocation CSV",
                            data=csv1,
                            file_name="output_btp_mtp_allocation.csv",
                            mime="text/csv",
                            key="download_allocation"
                        )

                    with col2:
                        st.subheader("Faculty Preference Statistics")
                        # st.dataframe(pref_stats_df, height=400)

                        # Download stats
                        csv2 = pref_stats_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Statistics CSV",
                            data=csv2,
                            file_name="fac_preference_count.csv",
                            mime="text/csv",
                            key="download_stats"
                        )

                    # Summary statistics
                    # st.divider()
                    # st.subheader("Summary Statistics")
                    #
                    # col_a, col_b, col_c = st.columns(3)
                    # with col_a:
                    #     st.metric("Total Students", len(allocation_df))
                    # with col_b:
                    #     st.metric("Total Faculties", len(count_faculty_columns(input_df)))
                    # with col_c:
                    #     st.metric("Avg CGPA", f"{allocation_df['CGPA'].mean():.2f}")

                    # Faculty allocation distribution
                    # st.subheader("Faculty Allocation Distribution")
                    # fac_dist = allocation_df['Allocated'].value_counts().reset_index()
                    # fac_dist.columns = ['Faculty', 'Student Count']
                    # st.bar_chart(fac_dist.set_index('Faculty'))

                except Exception as e:
                    st.error(f"Error during processing: {str(e)}")
                    logger.error(f"Processing error: {str(e)}", exc_info=True)

    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        logger.error(f"File reading error: {str(e)}", exc_info=True)

else:
    st.info("Please upload a CSV file")

    st.markdown("""
    ### Input File Format:
    - **Columns**: `Roll`, `Name`, `Email`, `CGPA`, followed by faculty preference columns
    - **Lower Preference Value:** High Priority, **Higher Preference:** Lower Priority**
    """)

#     ### Allocation Algorithm:
#     1. Students are sorted by CGPA in descending order
#     2. Faculties are assigned in round-robin fashion (mod n)
#     3. In each cycle of n students, each faculty gets exactly one student
# Footer
# st.divider()
