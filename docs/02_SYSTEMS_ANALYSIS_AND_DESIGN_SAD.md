# Systems Analysis and Design (SAD) Master Specification
## Grounded in Dennis, Wixom & Roth (5th Edition) — Phases 1 to 4

- **Project Title:** USIU-Africa Accessible Lecturer Assessment & Blackboard Grader Suite (`v2.0`)
- **System Sponsor:** Faculty of SST, CSB, and SHSS — United States International University - Africa
- **Target LMS:** `https://blackboard.usiu.ac.ke` (`Blackboard Learn v4001.4.0`)

---

## Phase 1: Planning & Feasibility Analysis (Gate 1: PASSED)

### 1.1 System Request Summary
- **Business Need:** Low-vision university lecturers face severe visual fatigue when reading 50–120 student papers per semester across tiny LMS fonts, while ad-hoc LLM prompting produces inconsistent "vibes-based" grading that violates criterion-referenced academic standards.
- **Tangible Value:** Reduces grading and Grade Center entry time by **68%** (from 18 minutes/paper to < 5.5 minutes/paper) while eliminating manual transcription errors.
- **Intangible Value:** Full WCAG 2.1 AAA low-vision accessibility, zero student PII cloud exposure (Kenya Data Protection Act 2019 compliance), and verifiable Senate grade-appeal audit trails.

### 1.2 Economic Feasibility Analysis (Verified via `feasibility_calc.py`)

$$NPV = \sum_{t=0}^N \frac{CF_t}{(1 + r)^t}, \quad ROI = \frac{\text{Total PV Benefits} - \text{Total PV Costs}}{\text{Total PV Costs}} \times 100\%$$

| Financial Metric | Year 0 (Dev) | Year 1 | Year 2 | Year 3 | Total (PV @ 10%) |
|---| ---: | ---: | ---: | ---: | ---: |
| **Total Benefits (Nominal)** | \$0.00 | \$30,000.00 | \$42,000.00 | \$55,000.00 | - |
| **PV of Benefits (10%)** | \$0.00 | \$27,272.73 | \$34,710.74 | \$41,322.31 | **\$103,305.79** |
| **Total Costs (Nominal)** | \$35,000.00 | \$8,000.00 | \$9,000.00 | \$10,000.00 | - |
| **PV of Costs (10%)** | \$35,000.00 | \$7,272.73 | \$7,438.02 | \$7,513.15 | **\$57,223.89** |
| **Net Present Value (Annual)** | -\$35,000.00 | \$20,000.00 | \$27,272.73 | \$33,809.17 | **\$46,081.89** |
| **Cumulative Net Cash Flow (NPV)** | -\$35,000.00 | -\$15,000.00 | \$12,272.73 | \$46,081.89 | - |

- **Cumulative Net Present Value (NPV):** **\$46,081.89** ($NPV > 0$)
- **Return on Investment (ROI):** **80.53%**
- **Break-Even Point (Payback Period):** **1.55 Years (~18.6 Months)**

---

## Phase 2: Process & Data Modeling (Gate 2: PASSED)

### 2.1 Context Diagram & Level 0 Data Flow Diagram (DFD)
Validated via `dfd_validator.py` with **0 Black Holes, 0 Miracles, 0 Illegal Flows (`status: PASS`)**:

```mermaid
flowchart TB
    E1["External Entity E1:<br/>USIU Lecturer"]
    E2["External Entity E2:<br/>USIU Blackboard Learn LMS"]

    P1(["1.0 Ingest Student<br/>Submissions"])
    P2(["2.0 Evaluate Against<br/>Locked Rubric"])
    P3(["3.0 Synthesize Low-Vision<br/>Audio Review"])
    P4(["4.0 Synchronize<br/>Blackboard Gradebook"])

    D1[("D1: Locked Rubrics Store")]
    D2[("D2: Student Submissions Store")]
    D3[("D3: Grading Audit Trail Store")]

    E2 -->|"Assignment ZIP or REST Attempts"| P1
    E1 -->|"Drag-and-Drop Submission Files"| P1
    P1 -->|"Normalized Submission Text"| D2
    D2 -->|"Student Submission Payload"| P2
    D1 -->|"4-Pillar Rubric Weights"| P2
    P2 -->|"Criterion Scores & Evidence Quotes"| D3
    D3 -->|"Staged Assessment Receipt"| P3
    P3 -->|"Giant-Print Display & TTS Speech"| E1
    E1 -->|"Lecturer Score Override & Approval"| P3
    P3 -->|"Approved Final Grade & Feedback"| P4
    P4 -->|"Grade Center CSV or REST PATCH"| E2
    P4 -->|"Blackboard Sync Confirmation"| D3
```

### 2.2 Entity-Relationship Diagram (ERD) & 3NF Normalization Proof
Validated via `normalization_analyzer.py` (`current_normal_form: "3NF (Third Normal Form)"`, `is_1nf: true`, `is_2nf: true`, `is_3nf: true`):

- **1NF Resolution:** Repeating rubric pillars (`criterion_1..4`) are decomposed out of `ASSESSMENTS` into a child relation `ASSESSMENT_CRITERIA_SCORES` with composite primary key `(student_id, criterion_id)`.
- **2NF Resolution:** Non-key attributes in `ASSESSMENT_CRITERIA_SCORES` (`earned`, `evidence_quote`) depend on the **whole** composite key `(student_id, criterion_id)`.
- **3NF Resolution:** Course and rubric metadata are isolated in `RUBRICS` (`data/usiu_locked_rubrics.json`), eliminating transitive dependencies.

```mermaid
erDiagram
    RUBRICS ||--o{ ASSESSMENTS : governs
    ASSESSMENTS ||--|{ ASSESSMENT_CRITERIA_SCORES : decomposes_into

    RUBRICS {
        string rubric_id PK
        string title
        string school
        int total_points
    }

    ASSESSMENTS {
        string student_id PK
        string student_name
        string source_filename
        string rubric_id FK
        int word_count
        int citations_detected
        float total_score
        string letter_grade
        float gpa_points
        string standing
        string feedback_for_blackboard
        boolean overridden_by_lecturer
        string graded_at
    }

    ASSESSMENT_CRITERIA_SCORES {
        string student_id PK,FK
        string criterion_id PK
        string criterion_name
        float weight
        float earned
        string evidence_quote
    }
```

---

## Phase 3: Architecture, Structure Chart & Data Sizing (Gate 3: PASSED)

### 3.1 Multi-Tier Local-First System Architecture

```mermaid
flowchart LR
    subgraph Presentation_Tier["Presentation Tier (WCAG AAA Low-Vision)"]
        WebHub["index.html<br/>(175% Giant Print + Drag & Drop)"]
        Ext["Chrome/Edge Extension MV3<br/>(extension/content_script.js)"]
    end

    subgraph Application_Tier["Dual-Engine Application Tier (127.0.0.1)"]
        PySrv["Python 3 REST Server<br/>(src/usiu_lecturer_server.py :8085)"]
        JavaSrv["Java 21 LTS REST Server<br/>(src/USIULecturerServer.java :8086)"]
        CoreEngine["Deterministic Grader & Extractors<br/>(src/usiu_blackboard_grader.py)"]
    end

    subgraph Data_And_LMS_Tier["Persistence & LMS Integration Tier"]
        SQLite[("SQLite 3NF DB<br/>(usiu_grading_store.sqlite3)")]
        CSV["Grade Center CSV & JSON<br/>(data/outputs/)"]
        BB["USIU Blackboard Learn<br/>(https://blackboard.usiu.ac.ke)"]
    end

    WebHub <-->|"HTTP JSON / Multipart"| PySrv
    WebHub <-->|"HTTP JSON"| JavaSrv
    Ext <-->|"Service Worker Bridge"| PySrv
    Ext <-->|"Authenticated Session / DOM"| BB
    PySrv --> CoreEngine
    CoreEngine --> SQLite
    CoreEngine --> CSV
    CoreEngine <-->|"REST API v1/v2"| BB
```

### 3.2 Modular Structure Chart (Functional Cohesion & Data Coupling)
All modules communicate strictly via typed data parameters (**Data Coupling**), avoiding global control flags:
- `parse_student_identity_from_filename(filename) -> (student_id, student_name)`
- `extract_submission_bytes(filename, raw_bytes) -> plain_text`
- `evaluate_submission_deterministic(student_id, student_name, text, rubric) -> assessment_dict`
- `recalculate_with_overrides(assessment, criterion_overrides, custom_feedback) -> updated_assessment`
- `format_blackboard_csv_string(results) -> rfc4180_csv`

### 3.3 Volumetric Storage Estimation
$$\text{Total Volumetric Size} = \text{RowSize} \times \text{RowCount} \times 1.35\text{ (Index & WAL Overhead)}$$
- Average `ASSESSMENTS` + 4 `ASSESSMENT_CRITERIA_SCORES` rows per student $\approx 2.4\text{ KB}$.
- At 500 students/semester across 6 semesters (3-year retention = 3,000 graded papers):
  $$2.4\text{ KB} \times 3,000 \times 1.35 \approx 9.72\text{ MB}$$
- Easily fits inside a single lightweight local SQLite file with sub-millisecond query latency.

---

## Phase 4: Implementation, Testing & Transition Plan (Gate 4: PASSED)

1. **4-Stage Testing Verification (`tests/test_usiu_suite.py`):**
   - **Unit Tests:** Verify USIU grade boundaries (`A` to `F`), Blackboard filename regex parsing, and zero-drift determinism.
   - **Integration Tests:** Verify `.txt`, `.docx`, `.pdf`, and Blackboard `.zip` ingestion into SQLite 3NF tables and CSV export.
2. **Conversion Strategy (Parallel + Pilot Cutover):**
   - Lecturers run the **Offline ZIP-in / CSV-out** mode alongside standard Blackboard Grade Center during Midterm grading, transitioning to full **Chrome/Edge Extension In-Page Assisted Grading** for Final Projects.
3. **Lewin's Change Management Model (Unfreeze → Change → Refreeze):**
   - **Unfreeze:** Demonstrate how ad-hoc ChatGPT prompting causes unfair score drift on identical essays.
   - **Change:** Provide 1-click launcher (`Run_USIU_Lecturer_Grader.bat`) and voice-guided shortcuts (`Space`, `N`, `P`).
   - **Refreeze:** Standardize departmental rubrics in `data/usiu_locked_rubrics.json` across SST, CSB, and SHSS.
