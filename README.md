# Student Grouping Assignment Tool

This project is a **Streamlit web app** that allows users to upload an Excel file of student data and automatically generates student groups in multiple formats. The tool creates **branch-wise groups**, **uniformly mixed groups**, and a **summary Excel file**, and finally packages everything into a downloadable ZIP file.

---

## 🚀 Features
- Upload student data from an **Excel file** (`.xlsx` or `.xls`).
- Enter the **number of groups** to divide students into.
- Automatically detects **branch names** from student roll numbers.
- Generates:
  - **Branchwise Mix Groups** – Students distributed across groups, balanced by branch.
  - **Uniform Mix Groups** – Students distributed evenly across groups regardless of branch.
  - **Branchwise Student Lists** – Separate CSVs for each branch.
- Creates a **Final Excel file (`final_groups.xlsx`)** with group composition statistics.
- Provides a **ZIP download (`assignment.zip`)** containing:
  - `student_groups/` – CSV files for each branch.
  - `branchwise_mix/` – Groups formed branchwise.
  - `uniform_mix/` – Groups formed uniformly.
  - `final_groups.xlsx` – Summary statistics.
  
---

## 📂 Project Structure (Generated after running)

### ├── student_groups/ # Per-branch student lists (CSV files)
### ├── branchwise_mix/ # Grouped student lists (branchwise mix)
### ├── uniform_mix/ # Grouped student lists (uniform mix)
### ├── final_groups.xlsx # Excel file with group statistics
### ├── assignment.zip # Downloadable ZIP containing all outputs
### └── tut01.py # Main Streamlit application


---

## ⚙️ Requirements
Make sure you have the following installed:

- Python 3.x
- Required libraries:
  ```bash
  pip install pandas streamlit openpyxl
## ▶️ How to Run

1. Save your student data in an Excel file with at least a Roll column.

2. The branch name is extracted from the roll number (e.g., AI123 → branch AI).

3. Run the Streamlit app: streamlit run tut01.py 

4. Upload your Excel file via the UI.

5. Enter the number of groups.

6. Click Submit.

7. Download the assignment.zip file.

##📊 Output Explanation

student_groups/
CSV files containing students separated by branch.

branchwise_mix/
Groups created by distributing students round-robin across branches.

uniform_mix/
Groups created evenly without strict branch balancing.

final_groups.xlsx
Contains two sheets:

Branchwise_Mix → Branch distribution in each group.

Uniform_Mix → Branch distribution in each group.
