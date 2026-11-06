# GitHub Copilot Agent Instructions — USIU-Africa Accessible Lecturer Suite (`v2.2`)

You are working in the **USIU-Africa Accessible Lecturer Assessment & Blackboard Grader Suite** repository (`Mercy-Em-t/USIU_Lecturere`).

## 1. Core Architectural Invariants (MUST FOLLOW)
1. **Zero External Cloud / CDN Leaks:** Never add external CDN `<script>` tags or third-party cloud API calls that transmit student PII or essays (`66xxxx`). All grading and text extraction must run 100% locally (`127.0.0.1`).
2. **Low-Vision Accessibility First:** Any UI changes in `index.html`, `survey.html`, or `extension/` must maintain **22px–38px Giant Ultra-Bold Typography** (`font-weight: 800-900`), high contrast (`#ffd166` / `#ffffff` on `#030508` Obsidian or `#000000` on `#fffdf5` Cream), and Web Speech API (`window.speechSynthesis`) read-aloud support.
3. **Zero-Dependency Standard Library Portability:** Both `src/usiu_blackboard_grader.py` / `src/usiu_lecturer_server.py` (Python 3.10+) and `src/USIULecturerServer.java` (Java 21 LTS) must run using pure standard library modules so GitHub Actions, Codespaces, and university workstations require zero `pip install` or Maven setup.

## 2. Commands for Copilot Agent Execution

### Run the Automated Unit & Integration Test Suite (8 Tests)
```bash
python tests/test_usiu_suite.py
```

### Run the Multi-Format CLI Grader (`.txt`, `.docx`, `.pdf`, `.zip`)
```bash
python src/usiu_blackboard_grader.py \
  --submissions-dir data/sample_submissions \
  --out-csv data/outputs/USIU_Blackboard_GradeCenter_Upload.csv \
  --out-json data/outputs/USIU_Grading_Audit_Report.json
```

### Start the Local Python REST & SQLite 3NF Server (`:8085`)
```bash
python src/usiu_lecturer_server.py --host 127.0.0.1 --port 8085
```

### Compile & Test the Enterprise Java 21 Server (`:8086`)
```bash
javac src/USIULecturerServer.java
java -cp src USIULecturerServer --cli-test
```

### Note on `src/usiu_lecturer_discovery_survey_form.gs`
- `src/usiu_lecturer_discovery_survey_form.gs` uses Google Workspace's proprietary `FormApp` and `SpreadsheetApp` globals, which execute inside `https://script.google.com`.
- For local/GitHub agent execution without Google OAuth, use the built-in Giant-Print Faculty Discovery Survey at `survey.html` (`GET /survey` and `POST /api/survey/submit` on `:8085`).
