import pandas as pd
import math
import streamlit as st
import os
import re
import  zipfile
import shutil

st.title("Excel Upload with Integer Input")

# Upload Excel sheet
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])

# Take integer input
num = st.number_input("Enter an integer", min_value=0, step=1)

# Submit button
if st.button("Submit"):
    if uploaded_file is not None and num is not None:
    
        for folder in ["branchwise_mix", "uniform_mix", "Student_groups"]:
            if os.path.exists(folder) and os.path.isdir(folder):
                shutil.rmtree(folder)
                print(f"Deleted folder: {folder}")

        excel_file = "Final_groups.xlsx"
        if os.path.exists(excel_file) and os.path.isfile(excel_file):
            os.remove(excel_file)
            print(f"Deleted file: {excel_file}")
        

        df = pd.read_excel(uploaded_file)       


        df["Branch"] = df["Roll"].str.extract(r'([A-Z]+)')


        # In[30]:


        os.makedirs("student_groups", exist_ok=True)


        # In[31]:


        # Loop through each branch group
        for branch, group in df.groupby("Branch"):

            # Define the file name for this branch
            filename = f"student_groups/{branch}.csv"

            # Save only this branch's students to a CSV file
            group.to_csv(filename, index=False)

            # (Optional) print progress
            print(f"Saved {filename}")


        # In[32]:


        bw_dictionary = {}   # start with an empty dictionary

        # Step 1: loop through all files in the folder
        for file in os.listdir("student_groups"):

            # Step 2: check if the file is a CSV
            if file.endswith(".csv"):

                # Step 3: get the branch name (remove .csv from filename)
                branch_name = file.replace(".csv", "")

                # Step 4: get the full file path
                file_path = os.path.join("student_groups", file)

                # Step 5: read the CSV into a DataFrame
                data = pd.read_csv(file_path)

                # Step 6: store it in the dictionary with branch name as key
                bw_dictionary[branch_name] = data


        # In[33]:


        bw_dictionary["AI"]


        # In[34]:


        # Convert dictionary items into a list of (branch_name, DataFrame)
        items = list(bw_dictionary.items())

        # Sort that list by number of rows in each DataFrame (largest first)
        items_sorted = sorted(items, key=lambda pair: len(pair[1]), reverse=True)

        # Convert back to dictionary
        bw_dictionary_sorted = dict(items_sorted)


        # In[35]:


        def create_branchwiseMix_groups(df, bw_dictionary_sorted, n):
            # Count total students directly from the original DataFrame
            total_students = len(df)

            # Students per group (ceil)
            x = math.ceil(total_students / n)

            # Show info
            print("Total students = {}".format(total_students))
            print("Groups = {}, Students per group (ceil) = {}".format(n, x))

            # Store branch DataFrames (copied) in a dictionary
            branch_students = {}
            for branch, data in bw_dictionary_sorted.items():
                branch_students[branch] = data.copy()

            # Create n empty groups
            groups = []
            for _ in range(n):
                groups.append([])

            # Round-robin allocation
            still_students_left = True

            while still_students_left:
                still_students_left = False   # assume no students left

                # Check if any branch still has students
                for branch_name, branch_df in branch_students.items():
                    if len(branch_df) > 0:   # this branch has students
                        still_students_left = True
                        break   # stop checking, at least one branch is non-empty

                # If all branches empty → stop loop
                if not still_students_left:
                    break

                # Assign one student from each branch (if available)
                for branch_name, branch_df in branch_students.items():
                    if len(branch_df) > 0:  # take student only if available
                        student = branch_df.iloc[0].to_dict()   # first student as dict
                        branch_students[branch_name] = branch_df.iloc[1:]  # remove that student

                        # Place student into the first group that is not full
                        for group in groups:
                            if len(group) < x:
                                group.append(student)
                                break

            # Save groups as CSV files
            folder = "branchwise_mix"
            os.makedirs(folder, exist_ok=True)

            for i, group in enumerate(groups, start=1):
                pd.DataFrame(group).to_csv(os.path.join(folder, f"group{i}.csv"), index=False)

            print("Groups created and saved in folder '{}'".format(folder))


        # In[45]: function calling uniform mix


        create_branchwiseMix_groups(df,bw_dictionary_sorted, num)


        # In[43]:


        def create_uniformMix_groups(df, bw_dictionary_sorted, n):
            # total students
            total_students = len(df)
            x = math.ceil(float(total_students) / float(n))   # students per group

            print("Total students = {}".format(total_students))
            print("Groups = {}, Students per group (ceil) = {}".format(n, x))

            groups = []
            current_group = []

            # go branch by branch
            for branch, data in bw_dictionary_sorted.items():
                students = data.to_dict("records")

                # take students in chunks
                for i in range(0, len(students), x):
                    chunk = students[i:i+x]
                    current_group.extend(chunk)

                    # whenever current_group reaches size x → store it
                    while len(current_group) >= x:
                        groups.append(current_group[:x])   # first x students
                        current_group = current_group[x:] # remove them

            # add leftover students
            if current_group:
                groups.append(current_group)

            # save groups as CSV files
            os.makedirs("uniform_mix", exist_ok=True)

            for i, group in enumerate(groups, start=1):
                pd.DataFrame(group).to_csv(os.path.join("uniform_mix", "group{}.csv".format(i)), index=False)

            print("Groups created and saved in folder: {}".format(os.path.abspath("uniform_mix")))



        # In[44]://Function calling branchwise groups


        create_uniformMix_groups(df, bw_dictionary_sorted, num)



########### CREATING EXCEL OF STATS FOR UNIFORM AND BRANCHWISE MIX
       
        student_groups_folder = "Student_groups"
        uniform_mix_folder = "uniform_mix"
        branchwise_mix_folder = "branchwise_mix"

        #Get branch names from Student_groups folder
        branch_names = []

        for i in os.listdir(student_groups_folder):
            if i.endswith(".csv"):                # only take CSV files
                name = i.replace(".csv", "")      # remove ".csv" extension
                branch_names.append(name)         # add branch name to listbranch_names.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else -1)

        #print("Branches found:", branch_names)
        print(branch_names)

        # -------------------------
        # Step 2: Function to process a folder of group CSVs
        # -------------------------
        def process_groups(folder_passed, branch_names):
            group_data = []   # this will store one row per group

            # Get all files inside the folder
            files = os.listdir(folder_passed)

            # Keep only CSV files
            csv_files = []
            for i in files:                       
                if i.endswith(".csv"):
                    csv_files.append(i)
            # Sort files so group1, group2, ... stay in order
            # csv_files.sort()
            csv_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else -1)
            print(csv_files)

            group_number = 1
            for i in csv_files:
                filepath = os.path.join(folder_passed, i)
                df = pd.read_csv(filepath)

                # -------------------------------
                # Manual branch counting
                # -------------------------------
                branch_column = df["Branch"]
                counts = {}
                for branch in branch_column:
                    if branch in counts:
                        counts[branch] += 1
                    else:
                        counts[branch] = 1

                # Debug: show counts for each group
                print(f"Counts in {i} ->", counts)

                # Make a row for this group
                row = {"Group": f"Group{group_number}"}
                for branch in branch_names:
                    if branch in counts:
                        row[branch] = counts[branch]
                    else:
                        row[branch] = 0   # if no students of this branch, put 0

                group_data.append(row)
                group_number += 1

            # Convert collected rows into a dataframe
            result_df = pd.DataFrame(group_data, columns=["Group"] + branch_names)
            return result_df

        # -------------------------
        # Step 3: Process both folders
        # -------------------------
        branchwise_df = process_groups(branchwise_mix_folder, branch_names)
        uniform_df = process_groups(uniform_mix_folder, branch_names)

        # -------------------------
        # Step 4: Save into Excel
        # -------------------------
        output_file = "final_groups.xlsx"

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            branchwise_df.to_excel(writer, sheet_name="Branchwise_Mix", index=False)
            uniform_df.to_excel(writer, sheet_name="Uniform_Mix", index=False)

        print("✅ Excel file created:", output_file)




        # In[48]:


    def create_zip_with_folders(zip_name="assignment.zip"):
        folders = ["Student_groups", "branchwise_mix", "uniform_mix"]
        excel_file = "final_groups.xlsx"  # the extra Excel file to include

        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add folders
            for folder in folders:
                if os.path.exists(folder):
                    for root, dirs, files in os.walk(folder):
                        # skip hidden folders like .ipynb_checkpoints
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                        for file in files:
                            if not file.startswith('.'):  # skip hidden files
                                file_path = os.path.join(root, file)
                                # preserve folder structure in zip
                                arcname = os.path.relpath(file_path, start=os.path.dirname(folder))
                                zipf.write(file_path, arcname)

            # Add the Excel file
            if os.path.exists(excel_file):
                print("exists")
                zipf.write(excel_file, arcname=os.path.basename(excel_file))

        print("ZIP file created:", os.path.abspath(zip_name))


        # In[49]:


    create_zip_with_folders()






    ### DOWNLOAD ZIP FILE USING STREAMLIT###

    # Path to your zip file
    zip_file_path = "assignment.zip"

    # Check if the file exists
    if os.path.exists(zip_file_path):
        with open(zip_file_path, "rb") as f:
            st.download_button(
                label="Download Assignment ZIP",
                data=f,
                file_name="assignment.zip",
                mime="application/zip"
            )
    else:
        st.warning("⚠️ ZIP file not found. Please create it first.")

else:
        st.warning("Please upload an Excel file and enter an integer before submitting.")



