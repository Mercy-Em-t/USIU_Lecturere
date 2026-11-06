# 🎓 USIU-Africa Accessible Lecturer Assessment & Blackboard Suite (`v2.0`)

> **Localized for United States International University - Africa (USIU-Africa)**  
> **Target LMS:** `https://blackboard.usiu.ac.ke` (`Blackboard Learn v4001.4.0 • rel.58+b22e012`)  
> **Standards:** ISO/IEC/IEEE 29148:2018 SRS • Dennis, Wixom & Roth SAD (3NF / DFD) • WCAG 2.1 AAA Low-Vision & Audio Ergonomics • Kenya Data Protection Act (KDPA 2019)

This repository provides a complete, local-first assessment, multi-format document ingestion, and Blackboard Learn synchronization suite tailored for **USIU-Africa** faculty across the **School of Science & Technology (SST)**, **Chandaria School of Business (CSB)**, and **School of Humanities & Social Sciences (SHSS)**.

---

## ✨ Key Capabilities in `v2.0`

1. **Multi-Format Drag-and-Drop Ingestion (`.pdf`, `.docx`, `.txt`, `.md`, & Blackboard `.zip` Bulk Archives):**
   - Drop an entire Blackboard Grade Center **"Download Assignment Files"** `.zip` archive or individual student `.pdf`, `.docx`, and `.txt` papers directly into the Giant-Print Hub.
   - Automatically parses Blackboard's bulk filename convention (`AssignmentName_StudentID_attempt_YYYY-MM-DD-HH-MM-SS_Filename.docx`) and USIU 6-digit IDs (`66xxxx`).
2. **Low-Vision Accessibility & Voice-First Keyboard Navigation:**
   - **Giant-Print Scaling:** `100%` (`20px`), `135%` (`25px`), and `175%` (`30px`) with **Obsidian Dark (`#05070b`)** and **High-Contrast Cream (`#fffdf5`)** themes.
   - **Audio Read-Aloud:** 1-click Web Speech API + offline Windows SAPI5 (`--speak`) voice synthesis.
   - **Zero-Mouse Shortcuts:** `Space` (Read Grade Aloud), `N` / `P` (Next/Previous Student), `1–4` (Hear Rubric Criterion 1–4), `Alt+Z` (Cycle Zoom), `Alt+C` (Toggle Contrast).
3. **Locked 4-Pillar USIU School Rubrics + Interactive Lecturer Sliders:**
   - Eliminates inconsistent "vibes" prompting by enforcing locked school rubrics (`standard_research_paper`, `csb_business_case_study`, `shss_humanities_essay`) mapped to the official **USIU-Africa Grading Scale (`A` to `F`, GPA `4.0` to `0.0`)** with verbatim student evidence quotes and interactive slider overrides.
4. **Dual-Engine Local Backend (Python 3 REST/SQLite 3NF + Enterprise Java 21 Server):**
   - Runs 100% locally (`127.0.0.1`) so student PII never leaves the lecturer's machine.
5. **Packaged Chrome/Edge Extension (Manifest V3) for `blackboard.usiu.ac.ke`:**
   - Installable from [`extension/`](extension/) or [`data/outputs/USIU_Blackboard_Accessible_Extension_v2.0.zip`](data/outputs/USIU_Blackboard_Accessible_Extension_v2.0.zip) — injects a floating High-Contrast & Audio Grader drawer directly inside Blackboard.

---

## 📂 Complete Repository Architecture

```text
USIU_Lecturere/
├── README.md                                                  # Master Project Guide & Quick Start
├── index.html                                                 # Low-Vision Giant-Print Web Hub (Drag-and-Drop + Voice Shortcuts)
├── Run_USIU_Lecturer_Grader.bat                               # 1-Click Windows Launcher (CLI + Local Server + Web Hub)
├── src/
│   ├── usiu_blackboard_grader.py                              # Multi-Format Grader (.pdf, .docx, .txt, .zip) & SAPI TTS
│   ├── usiu_lecturer_server.py                                # Python 3 HTTP/REST & SQLite 3NF Local Server (:8085)
│   ├── USIULecturerServer.java                                # Enterprise Java 21 Pure-JDK HTTP/CLI Grading Server (:8086)
│   ├── usiu_bb_browser_bridge.js                              # Authenticated Session Bridge for blackboard.usiu.ac.ke
│   └── usiu_lecturer_discovery_survey_form.gs                 # Google Apps Script (FormApp) to Auto-Build Faculty Survey
├── extension/                                                 # Packaged Chrome/Edge Manifest V3 Browser Extension
│   ├── manifest.json                                          # MV3 Manifest targeting https://blackboard.usiu.ac.ke/*
│   ├── background.js                                          # Service Worker Bridge to Local Server (:8085)
│   ├── content_script.js                                      # In-Page Floating Accessible Sidecar & DOM Grade Form Filler
│   ├── popup.html                                             # High-Contrast Extension Popup
│   └── popup.js                                               # Popup Launcher Logic
├── docs/                                                      # Full System Engineering & Formal Documentation
│   ├── 01_REQUIREMENTS_ENGINEERING_ISO_29148_SRS.md           # 10-Phase ISO/IEC/IEEE 29148 SRS (Kano, Risk, Jackson-Zave)
│   ├── 02_SYSTEMS_ANALYSIS_AND_DESIGN_SAD.md                  # Dennis, Wixom & Roth SAD (Feasibility NPV/ROI, DFD, 3NF ERD)
│   ├── 03_PSEUDOCODE_AND_PROGRAM_SPECIFICATIONS.md            # Formal Algorithmic Pseudocode for Every Program File
│   ├── 04_USER_MANUAL_LECTURER_GUIDE.md                       # Step-by-Step Giant-Print Lecturer User Manual
│   ├── 05_TECHNICAL_ARCHITECTURE_AND_MAINTENANCE_MANUAL.md    # Technical Architecture, REST API, SQLite 3NF & Security Manual
│   └── 06_USER_DISCOVERY_SURVEY_AND_INTERVIEW_GUIDE.md        # Mom-Test Hypotheses, 15 Interview Questions & Google Form Guide
├── tests/
│   └── test_usiu_suite.py                                     # Automated Unit & Integration Test Suite (100% Pass)
└── data/
    ├── usiu_grading_scale_and_policies.json                   # Official USIU-Africa Grading Scale (A to F, GPA 4.0-0.0)
    ├── usiu_locked_rubrics.json                               # Locked Rubrics for SST, CSB, and SHSS
    ├── blackboard_endpoints_manifest.json                     # Verified USIU Blackboard v4001.4.0 REST API Endpoints
    ├── sample_submissions/                                    # Multi-Format Sample Cohort (.txt, .docx, .pdf)
    │   ├── 665421_Amina_Wanjiku.txt                           # Graded: 97.8/100 (A  | GPA 4.0)
    │   ├── 668312_Faith_Chepkoech.txt                         # Graded: 95.0/100 (A  | GPA 4.0)
    │   ├── 666104_Kelvin_Mwangi.txt                           # Graded: 89.8/100 (A- | GPA 3.7)
    │   ├── 667890_Brian_Otieno.txt                            # Graded: 62.6/100 (D  | GPA 1.0)
    │   ├── 669102_Zainab_Hassan.docx                          # Graded: 97.8/100 (A  | GPA 4.0) [Word XML]
    │   └── 669205_David_Kimani.pdf                            # Graded: 89.8/100 (A- | GPA 3.7) [PDF Stream]
    └── outputs/
        ├── USIU_Blackboard_GradeCenter_Upload.csv             # Ready for Blackboard "Work Offline -> Upload"
        ├── USIU_Grading_Audit_Report.json                     # Criterion-by-Criterion Audit Trail with Verbatim Quotes
        ├── Blackboard_Bulk_Submissions_Sample.zip             # Sample Blackboard Bulk Assignment ZIP for Drag-and-Drop
        └── USIU_Blackboard_Accessible_Extension_v2.0.zip      # Distributable Chrome/Edge Manifest V3 Extension Archive
```

---

## 🚀 Quick Start (Python, Java & Browser Extension)

### 1. Start the Local Python REST Server & Accessible Hub
```bash
python src/usiu_lecturer_server.py --port 8085
```
Then open **`http://127.0.0.1:8085`** (or double-click **[`index.html`](index.html)** directly for serverless mode).

### 2. Run the Enterprise Java 21 Grading Engine
```bash
javac src/USIULecturerServer.java
java -cp src USIULecturerServer --cli-test
# Or start the Java HTTP server on port 8086:
java -cp src USIULecturerServer --port 8086
```

### 3. Load the Chrome / Microsoft Edge Extension
1. Open `chrome://extensions` or `edge://extensions` and enable **Developer mode**.
2. Click **Load unpacked** and select the **[`extension/`](extension/)** folder (or extract [`USIU_Blackboard_Accessible_Extension_v2.0.zip`](data/outputs/USIU_Blackboard_Accessible_Extension_v2.0.zip)).
3. Navigate to `https://blackboard.usiu.ac.ke` — the **🎓 USIU Accessible Grader** floating sidecar will appear in the bottom-right corner.

### 4. Run the Automated Test Suite
```bash
python tests/test_usiu_suite.py
```
