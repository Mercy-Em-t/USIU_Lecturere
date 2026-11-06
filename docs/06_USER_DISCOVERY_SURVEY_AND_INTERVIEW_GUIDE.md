# 🎤 USER DISCOVERY, MOM-TEST INTERVIEW GUIDE & GOOGLE FORM SUITE
## USIU-Africa Accessible Lecturer Assessment & Blackboard Grader Suite (`v2.1`)

- **Google Apps Script Generator:** [`src/usiu_lecturer_discovery_survey_form.gs`](../src/usiu_lecturer_discovery_survey_form.gs)
- **Methodology:** Rob Fitzpatrick's *The Mom Test* + ISO/IEC/IEEE 29148 Stakeholder Elicitation + Noriaki Kano Satisfaction Model
- **Target Segment:** USIU-Africa Lecturers, Adjunct Faculty, and Teaching Assistants across SST, Chandaria School of Business (CSB), and SHSS (particularly low-vision faculty or instructors grading high-volume written cohorts of 30–150+ students).

---

## 1. FALSIFIABLE PROBLEM-SOLUTION FIT HYPOTHESES

Before scaling or modifying any feature, we test three strict, falsifiable hypotheses with concrete **Pass/Fail thresholds**:

| Hypothesis Type | Falsifiable Statement | Measurement Item in Survey | Pass / Fail Threshold |
| :--- | :--- | :--- | :--- |
| **H1: Customer & Visual Ergonomics Hypothesis** (*Do they experience severe visual/ergonomic pain during grading?*) | Low-vision and high-volume USIU lecturers experience significant eye strain when reading 30+ student papers and tiny Blackboard Grade Center cells, actively forcing them to zoom (`>125%`), switch contrast modes, print papers, or take forced breaks. | **Q6** (1–5 Eye Strain Scale) & **Q7** (Actual Visual Adjustments Used) | **PASS:** $\ge 7\text{ out of }10$ respondents score $\ge 4/5$ on Q6 **AND** report doing at least 1 active visual workaround in Q7. |
| **H2: Workflow Bottleneck Hypothesis** (*Is the Blackboard file-handling & grade-entry loop a major time sink?*) | Lecturers spend **6+ hours per section** opening individual `.pdf`/`.docx` files, switching tabs, and manually typing scores and feedback into Blackboard Grade Center. | **Q4** (Walkthrough of Last Batch), **Q5** (Hours Spent), & **Q8** (Biggest Frustration) | **PASS:** $\ge 7\text{ out of }10$ respondents report spending $\ge 6\text{ hours}$ per section (Q5) and cite file-opening / Grade Center entry friction in Q4/Q8. |
| **H3: Alternative Inadequacy & Zero-Drift Hypothesis** (*Are ad-hoc AI chatbots failing academic consistency & privacy requirements?*) | Lecturers who have tried copy-pasting essays into ChatGPT/LLMs experienced inconsistent marks ("vibes drift"), excessive copy-paste fatigue, or student data privacy concerns, and refuse to use any tool that gives identical papers different marks. | **Q9**, **Q10** (What Broke with AI), **Q12** (Local Privacy), & **Q14** (Score Drift Dealbreaker) | **PASS:** $\ge 8\text{ out of }10$ respondents rate local privacy $\ge 4/5$ (Q12) **AND** classify score drift as a dealbreaker in Q14. |

---

## 2. THE 15 "MOM-TEST" SURVEY & INTERVIEW QUESTIONS

Every question in [`src/usiu_lecturer_discovery_survey_form.gs`](../src/usiu_lecturer_discovery_survey_form.gs) asks about **concrete past behavior** (last semester's grading marathon) rather than hypothetical future promises:

### Section A: Course Load & Submission Formats
1. **Academic Division:** Which school or academic division do you primarily teach in? (`SST`, `CSB`, `SHSS`, `Other`)
2. **Actual Grading Volume:** Across all your course sections last semester, approximately how many total student written submissions did you personally grade? (`<30`, `30–60`, `61–120`, `121–200`, `200+`)
3. **Real File Formats Encountered:** In what file formats did students actually submit their written assignments on Blackboard last semester? (`.pdf`, `.docx`, inline Blackboard text, `.txt`/`.zip`, scanned images)

### Section B: Problem Discovery — Visual Fatigue & Blackboard Friction
4. **Last Batch Step-by-Step Walkthrough (*Core Mom-Test Probe*):** *"Walk us through the exact step-by-step process you used the last time you graded a batch of 30+ assignments on Blackboard (from opening the first student's paper to recording the final mark in Grade Center)."*
5. **Time Invested:** During your last major grading marathon, how many total hours did it take you to finish marking and entering feedback for a single course section?
6. **Quantified Eye Strain (1–5 Scale):** When reading student papers and navigating Blackboard Grade Center on your screen for more than 1 hour, how severe was your eye strain, visual fatigue, or headache?
7. **Proven Visual Workarounds:** Which of the following visual or physical adjustments did you actually do on your computer during your last grading session? (Zoomed `125%–175%`, Dark/Cream mode, Screen reader / Read-Aloud TTS, Printed on physical paper, Forced eye breaks)
8. **Single Biggest Pain Point:** *"What was the single most frustrating or exhausting part of your last grading session on Blackboard?"*

### Section C: Rubric Consistency, AI Drift & Feature Prioritization
9. **Current Workarounds Tried:** What tools or workarounds have you tried in the past 12 months to speed up grading or feedback? (ChatGPT copy-pasting, Word comment banks, Blackboard rubric grid, Offline Grade Center CSV + Excel, TA pre-check, 100% manual)
10. **Why Current AI Tools Failed:** *"If you have ever tried using an AI chatbot (like ChatGPT) or a rubric tool to help grade student papers, what broke, went wrong, or frustrated you about the results?"*
11. **What Lecturers Actually Look For (Config Studio Mapping):** When you mark a written assignment, what are the top 4 things you actually look for to distinguish an `A` (`90%+`) paper from a `C` (`70%`) paper? (Thesis clarity, APA 7th citations, SWOT/PESTEL/Course frameworks, Critical evaluation, Structure/Word count, Kenya/East Africa context)
12. **Local-First Privacy Requirement (1–5 Scale):** How important is it that student essays and Student IDs (`66xxxx`) remain 100% on your local computer / USIU session without being uploaded to public third-party cloud AI servers?
13. **Kano Functional Probe (Giant Print + Spacebar Audio Read-Aloud):** How would you feel if your grading workspace automatically opened in Giant Ultra-Bold Print (`140%–220%`) and read each student's paper, rubric quotes, and grade aloud to you at the press of the Spacebar?
14. **Kano Dysfunctional Probe (Zero-Drift Locked Rubric):** How would you feel if a grading assistant gave two identical student papers different marks at different times of the day (score drift) without showing you exact quotes from the student's text?
15. **Magic Wand Question:** *"If you could wave a magic wand and eliminate ONE repetitive step between downloading student papers from Blackboard and posting final grades, what would that step be?"*

---

## 3. HOW TO DEPLOY THE LIVE GOOGLE FORM IN 60 SECONDS

1. Go to **[https://script.google.com](https://script.google.com)** while signed into your Google account and click **New project**.
2. Open **[`src/usiu_lecturer_discovery_survey_form.gs`](../src/usiu_lecturer_discovery_survey_form.gs)**, copy all the code, paste it into the Apps Script editor (replacing `myFunction`), and press **`Ctrl + S`** to save.
3. Click the **Run** button at the top of the Apps Script editor (`createUSIULecturerDiscoverySurvey`).
4. Approve the one-time Google Forms & Google Sheets permission dialog.
5. Look at the **Execution log** at the bottom of the screen — it prints three live links:
   - **`🔗 LIVE SURVEY URL`**: Send this link directly to your lecturer and her USIU colleagues on WhatsApp or email.
   - **`✏️ FORM EDITOR URL`**: Customize colors/headers or view summary charts.
   - **`📊 RESPONSES GOOGLE SHEET URL`**: Automatically collects every lecturer's answers into a structured Google Sheet so we can feed their exact pain points and rubric keywords straight back into [`data/usiu_locked_rubrics.json`](../data/usiu_locked_rubrics.json)!
