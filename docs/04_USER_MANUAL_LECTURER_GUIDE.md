# 📘 USIU-AFRICA LECTURER USER MANUAL (GIANT-PRINT EDITION)
## Accessible Assessment & Blackboard Grader Suite (`v2.1`)

- **Designed For:** USIU-Africa Faculty (SST, Chandaria School of Business, SHSS)
- **Target LMS:** `https://blackboard.usiu.ac.ke`
- **Accessibility Features:** **140%–220% Giant Ultra-Bold Typography**, **High-Contrast Obsidian/Cream Themes**, **1-Click Voice Read-Aloud (`🔊 READ GRADE ALOUD`)**, and **Zero-Mouse Keyboard Shortcuts**.

---

## 1. HOW TO OPEN THE GRADING SUITE (1 CLICK)

You have **two easy ways** to launch your Grading Hub on Windows:

### Option A: The 1-Click Desktop Launcher (Recommended)
1. Open the **`USIU_Lecturere`** folder on your Desktop.
2. Double-click **[`Run_USIU_Lecturer_Grader.bat`](../Run_USIU_Lecturer_Grader.bat)**.
3. It automatically starts your private local grading engine (`http://127.0.0.1:8085`) and opens the **Giant-Print Grading Hub** in your web browser.

### Option B: Instant Offline Browser Mode (Zero Setup)
1. Simply double-click **[`index.html`](../index.html)** in the `USIU_Lecturere` folder.
2. It opens directly in Chrome or Microsoft Edge in **140% Giant Bold Print** (`26px`) and works completely offline.

---

## 2. ADJUSTING TEXT SIZE, CONTRAST & VOICE READ-ALOUD

At the very top of the screen is your **Low-Vision Accessibility Bar**:

| Big Button | What It Does | Keyboard Shortcut |
| :--- | :--- | :--- |
| **`🔍 110% BOLD`** | Sets text to Large Bold (`22px`) | `Alt + Z` (Cycles sizes) |
| **`🔍 140% GIANT`** | **Default Giant Bold (`26px`)** | `Alt + Z` |
| **`🔍 175% EXTRA`** | Extra-Giant Bold (`32px`) | `Alt + Z` |
| **`🔍 220% ULTRA`** | Poster-Size Ultra-Giant Bold (`38px`) | `Alt + Z` |
| **`🌓 CREAM / DARK`** | Switches between **Obsidian Dark** (`#030508` with Gold/White text) and **Warm Cream** (`#fffdf5` with Pure Black/Navy text) | `Alt + C` |
| **`🔊 READ GRADE ALOUD`** | Reads the current student's Name, USIU ID, Final Score, Letter Grade, GPA, and Constructive Feedback aloud | `Spacebar` |
| **`⏹️ STOP AUDIO`** | Immediately stops speech playback | — |

---

## 3. KEYBOARD-ONLY (EYES-FREE) GRADING SHORTCUTS

You never have to hunt for a small mouse cursor. While on the main page:
- Press **`Spacebar`** → Reads the current student's full grade and feedback aloud.
- Press **`N`** → Moves to the **Next Student** and automatically reads their grade aloud.
- Press **`P`** → Moves to the **Previous Student** and automatically reads their grade aloud.
- Press **`1`**, **`2`**, **`3`**, or **`4`** → Reads **Rubric Criterion #1, #2, #3, or #4** aloud, including the points earned and the **exact quote** extracted from the student's paper.
- Press **`Alt + Z`** → Cycles text size (`110%` → `140%` → `175%` → `220%`).
- Press **`Alt + C`** → Switches between **Obsidian Dark** and **High-Contrast Cream**.

---

## 4. CONFIGURING YOUR ASSIGNMENT ("HOW TO MARK" & "WHAT TO LOOK FOR")

Before grading a new assignment, you can tell the system **exactly how to mark** and **which concepts/keywords to look for**:

1. Under **STEP 1**, either pick a ready-made USIU School Rubric from the dropdown:
   - **SST / General:** Standardized Research & Term Paper (`APT3040` / `SWE3020`)
   - **CSB:** Chandaria School of Business Case Study (`BUS4010` / `MBA6010`)
   - **SHSS:** Humanities & International Relations Policy Essay (`IRL3020` / `PSY3010`)
2. Or click the big **`⚙️ Configure Assignment & Rubric`** button to open the **Configuration Studio**:
   - **Assignment / Rubric Title & Course Code:** e.g., `APT3040 Midterm Paper`.
   - **Target Word Count:** e.g., `220` words or `1000` words (papers shorter than your target receive a proportional depth score).
   - **Expected APA 7th Citations:** e.g., `3` peer-reviewed `(Author, Year)` citations for full empirical bonus.
   - **4-Pillar Weights & Keywords to Look For:** For each of the 4 pillars, type the point weight and the comma-separated concepts you expect students to discuss (for example: `swot, pestel, porter, value chain, kenya, roi`).
3. Click **`💾 Save Custom Rubric & Re-Mark All Submissions`**. The system locks your rubric so every student is marked by the exact same standard, re-grades all loaded papers, and announces the update aloud.

---

## 5. LOADING STUDENT SUBMISSIONS (DRAG & DROP OR BLACKBOARD BULK `.ZIP`)

### Method 1: Drag & Drop Individual Papers or a Blackboard `.zip` Archive
1. In Blackboard Grade Center, click the column header arrow next to your assignment and select **"Assignment File Download"** → **"Download Assignment Files NOW"**. Blackboard saves one `.zip` file containing the entire class's submissions.
2. Drag that `.zip` file (or individual `.pdf`, `.docx`, `.txt`, or `.md` student papers) onto the giant green dashed box:
   **`📂 DRAG & DROP STUDENT SUBMISSIONS OR BLACKBOARD BULK .ZIP HERE`** (or click the box to browse).
3. The system automatically:
   - Extracts each student's USIU ID (`66xxxx`) and full name from Blackboard's filename (`Assignment_665421_attempt_2026-11-06_Amina_Wanjiku.docx`),
   - Reads the full `.pdf`, `.docx`, or `.txt` essay,
   - Grades all 4 pillars and extracts verbatim student quotes,
   - Reads the first student's grade aloud!

---

## 6. REVIEWING & ADJUSTING A STUDENT'S MARK

You are always in 100% control of the final mark:
1. Select a student from **STEP 2** (or press **`N`** / **`P`**).
2. To adjust points on any of the 4 rubric pillars:
   - Click the giant **`➖ 1 PT`** or **`➕ 1 PT`** buttons (or drag the thick green slider).
   - The system **immediately recalculates** the Total Score out of 100, the official **USIU Letter Grade (`A` to `F`)**, and the **GPA points (`4.0` to `0.0`)**, and **reads the new score aloud**.
3. To customize the student's feedback, type directly into the big **`✍️ CONSTRUCTIVE FEEDBACK TO POST ON USIU BLACKBOARD`** box at the bottom of the card.

---

## 7. SENDING GRADES BACK TO USIU BLACKBOARD

You have **two safe, official ways** to send your approved marks to `https://blackboard.usiu.ac.ke`:

### Way 1: Official Blackboard Grade Center CSV Upload (Works 100% of the Time)
1. Under **STEP 3**, click **`⬇️ Grade Center CSV`**.
2. This downloads `USIU_Blackboard_GradeCenter_Upload.csv` containing `Username`, `Student ID`, `Full Name`, `Score`, `USIU Letter Grade`, and `Feedback to Learner`.
3. In USIU Blackboard, open **Grade Center → Full Grade Center → Work Offline → Upload** and select that CSV file.

### Way 2: In-Page Chrome / Microsoft Edge Extension (`blackboard.usiu.ac.ke`)
1. Open Chrome (`chrome://extensions`) or Edge (`edge://extensions`).
2. Turn ON **Developer mode** (top right).
3. Click **Load unpacked** and select the **[`extension/`](../extension/)** folder inside `USIU_Lecturere`.
4. Log into `https://blackboard.usiu.ac.ke` as normal. A giant bold **🎓 USIU Accessible Grader** panel appears in the bottom-right corner of Blackboard:
   - Click **`📥 Grade Page Text`** to grade the student attempt open on your screen.
   - Click **`🔊 Read Aloud`** to listen to the mark and feedback.
   - Click **`📤 Post / Fill Grade & Feedback on Blackboard`** to automatically fill Blackboard's Grade and Feedback boxes so you only have to click Submit!
