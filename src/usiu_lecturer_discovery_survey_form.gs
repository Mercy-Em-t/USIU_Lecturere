/**
 * usiu_lecturer_discovery_survey_form.gs — Ready-to-Run Google Apps Script (FormApp)
 * Project: USIU-Africa Accessible Lecturer Assessment & Blackboard Grader Suite (v2.1)
 *
 * HOW TO RUN THIS SCRIPT (1 MINUTE):
 *   1. Open https://script.google.com and click "New project".
 *   2. Delete any default code in `Code.gs` and paste this entire file.
 *   3. Click "Save" (Ctrl+S) and click "Run" (execution function: `createUSIULecturerDiscoverySurvey`).
 *   4. Approve the standard Google Form permission prompt when asked.
 *   5. Check the "Execution log" at the bottom of the screen for:
 *      - Live Respondent URL (share with USIU lecturers via WhatsApp / Email)
 *      - Form Editor URL (view responses & charts)
 *      - Linked Google Sheet URL (automatic response tabulation)
 *
 * DESIGN METHODOLOGY:
 *   Strictly follows Rob Fitzpatrick's "The Mom Test" and ISO/IEC/IEEE 29148 Elicitation Rules:
 *   - Asks ONLY about concrete past behaviors (last semester's grading, actual hours spent,
 *     real visual fatigue incidents, and actual workarounds used).
 *   - NEVER pitches the solution or asks leading "Would you use our app?" questions.
 */

function createUSIULecturerDiscoverySurvey() {
  const formTitle = "USIU-Africa Faculty Workflow & Assessment Accessibility Study";
  const formDescription =
    "This 4-minute research survey investigates the real-world experiences, visual ergonomics, " +
    "and Blackboard Grade Center workflows of university lecturers and teaching assistants across " +
    "SST, Chandaria School of Business (CSB), and SHSS.\n\n" +
    "All responses are confidential and focus on your actual experiences during your most recent " +
    "grading cycle (Midterms, Case Studies, or Term Papers).";

  const form = FormApp.create(formTitle);
  form.setDescription(formDescription);
  form.setCollectEmail(false);
  form.setProgressBar(true);
  form.setConfirmationMessage(
    "Thank you! Your insights directly inform accessible assessment and Blackboard workflow tooling for USIU-Africa faculty."
  );

  // =========================================================================
  // SECTION 1: FACULTY CONTEXT, COURSE LOAD & ASSESSMENT VOLUME
  // =========================================================================
  form.addSectionHeaderItem()
    .setTitle("Section 1: Course Load & Recent Assessment Volume")
    .setHelpText("Please answer based on the most recent semester you taught.");

  // Q1
  form.addMultipleChoiceItem()
    .setTitle("1. Which school or academic division do you primarily teach in?")
    .setChoiceValues([
      "School of Science & Technology (SST — e.g., APT, IST, SWE)",
      "Chandaria School of Business (CSB — e.g., BUS, MKT, FIN, MBA)",
      "School of Humanities & Social Sciences (SHSS — e.g., IRL, PSY, CMS)",
      "School of Pharmacy & Health Sciences / Other Division"
    ])
    .setRequired(true);

  // Q2
  form.addMultipleChoiceItem()
    .setTitle("2. Across all your course sections last semester, approximately how many total student written submissions (essays, case studies, lab reports, or projects) did you personally grade?")
    .setChoiceValues([
      "Fewer than 30 submissions",
      "30 – 60 submissions",
      "61 – 120 submissions",
      "121 – 200 submissions",
      "More than 200 submissions"
    ])
    .setRequired(true);

  // Q3
  form.addCheckboxItem()
    .setTitle("3. In what file formats did students actually submit their written assignments on Blackboard last semester? (Select all that apply)")
    .setChoiceValues([
      "PDF Documents (.pdf)",
      "Microsoft Word Documents (.docx / .doc)",
      "Pasted directly into the Blackboard inline text box",
      "Plain Text / Markdown / Code archives (.txt, .md, .zip)",
      "Scanned handwritten pages or image PDFs"
    ])
    .setRequired(true);

  // =========================================================================
  // SECTION 2: PROBLEM DISCOVERY — VISUAL FATIGUE & BLACKBOARD FRICTION
  // =========================================================================
  form.addPageBreakItem()
    .setTitle("Section 2: Visual Ergonomics & Grading Bottlenecks (The Mom Test)")
    .setHelpText("Think back to the last major assignment or exam batch you graded.");

  // Q4
  form.addParagraphTextItem()
    .setTitle("4. Walk us through the exact step-by-step process you used the last time you graded a batch of 30+ assignments on Blackboard (from opening the first student's paper to recording the final mark in Grade Center).")
    .setHelpText("For example: Did you read inside Blackboard's browser viewer, download individual files, download a bulk ZIP, or type marks into Excel first?")
    .setRequired(true);

  // Q5
  form.addMultipleChoiceItem()
    .setTitle("5. During your last major grading marathon, how many total hours did it take you to finish marking and entering feedback for a single course section?")
    .setChoiceValues([
      "Under 2 hours",
      "2 – 5 hours",
      "6 – 10 hours",
      "11 – 20 hours",
      "More than 20 hours across multiple days"
    ])
    .setRequired(true);

  // Q6
  form.addScaleItem()
    .setTitle("6. When reading student papers and navigating Blackboard Grade Center on your screen for more than 1 hour, how severe was your eye strain, visual fatigue, or headache?")
    .setBounds(1, 5)
    .setLabels("1 = No eye strain at all", "5 = Severe visual fatigue / had to stop working")
    .setRequired(true);

  // Q7
  form.addCheckboxItem()
    .setTitle("7. Which of the following visual or physical adjustments did you actually do on your computer during your last grading session? (Select all that apply)")
    .setChoiceValues([
      "Zoomed the browser window or Word/PDF document above 125% – 175%",
      "Switched my screen to Dark Mode, High-Contrast Mode, or Night Light / Warm Cream",
      "Used a screen reader or Read-Aloud (Text-to-Speech) audio tool to listen to student papers",
      "Printed student papers on physical paper because reading on screen hurt my eyes",
      "Took frequent forced breaks because small fonts or low contrast caused eye strain",
      "None of the above"
    ])
    .setRequired(true);

  // Q8
  form.addParagraphTextItem()
    .setTitle("8. What was the single most frustrating or exhausting part of your last grading session on Blackboard?")
    .setHelpText("Be as specific as possible (e.g., tiny Grade Center cells, session timeouts losing your typed feedback, repetitive clicking, etc.).")
    .setRequired(true);

  // =========================================================================
  // SECTION 3: RUBRIC CONSISTENCY, AI PROMPT DRIFT & ALTERNATIVES
  // =========================================================================
  form.addPageBreakItem()
    .setTitle("Section 3: Rubric Consistency, Current Workarounds & Priorities")
    .setHelpText("Tell us how you currently maintain grading consistency across dozens of papers.");

  // Q9
  form.addCheckboxItem()
    .setTitle("9. When marking a large class, what tools or workarounds have you tried in the past 12 months to speed up grading or feedback? (Select all that apply)")
    .setChoiceValues([
      "Copy-pasting student essays into ChatGPT / Claude / Gemini for draft feedback",
      "Keeping a Word/Notepad file of reusable feedback comments to copy-paste",
      "Using Blackboard's built-in interactive rubric grid",
      "Downloading the Blackboard Offline Grade Center CSV, marking in Excel, and re-uploading",
      "Having a Teaching Assistant / Work-Study student pre-check formatting or citations",
      "Grading 100% manually paper-by-paper without external tools"
    ])
    .setRequired(true);

  // Q10
  form.addParagraphTextItem()
    .setTitle("10. If you have ever tried using an AI chatbot (like ChatGPT) or a rubric tool to help grade student papers, what broke, went wrong, or frustrated you about the results?")
    .setHelpText("For example: Did it give different scores to similar papers ('vibes grading'), hallucinate feedback, require too much copy-pasting, or raise data privacy concerns?")
    .setRequired(false);

  // Q11
  form.addCheckboxItem()
    .setTitle("11. When you mark a written assignment, what are the top 4 things you actually look for to distinguish an 'A' (90%+) paper from a 'C' (70%) paper? (Select up to 4)")
    .setChoiceValues([
      "Clear Thesis Statement, Problem Formulation & Core Objective",
      "Peer-Reviewed Empirical Evidence & Accurate APA 7th In-Text Citations (Author, Year)",
      "Application of Course Frameworks (e.g., SWOT, PESTEL, Porter's 5 Forces, IR Theory, System Architecture)",
      "Critical Evaluation, Methodology, Counter-Arguments & Analytical Depth",
      "Academic Structure, Coherence, Word Count Depth & Reference List Formatting",
      "Local / Regional Contextualization (e.g., Kenya / East Africa case data)"
    ])
    .setRequired(true);

  // Q12
  form.addScaleItem()
    .setTitle("12. How important is it that student essays and Student IDs (66xxxx) remain 100% on your local computer / USIU session without being uploaded to public third-party cloud AI servers?")
    .setBounds(1, 5)
    .setLabels("1 = Not a concern", "5 = Mandatory requirement (Data Privacy / KDPA)")
    .setRequired(true);

  // Q13 (Kano Functional Question — Voice Read-Aloud & Giant Print)
  form.addMultipleChoiceItem()
    .setTitle("13. How would you feel if your grading workspace automatically opened in Giant Ultra-Bold Print (140%–220%) and read each student's paper, rubric quotes, and grade aloud to you at the press of the Spacebar?")
    .setChoiceValues([
      "I would love it (Delighter / Attractive)",
      "I expect it to work that way (Must-Be)",
      "I am neutral",
      "I can live with it",
      "I would dislike it"
    ])
    .setRequired(true);

  // Q14 (Kano Dysfunctional Question — Locked Rubric Consistency)
  form.addMultipleChoiceItem()
    .setTitle("14. How would you feel if a grading assistant gave two identical student papers different marks at different times of the day (score drift) without showing you exact quotes from the student's text?")
    .setChoiceValues([
      "I would dislike it / refuse to use it (Mandatory dealbreaker)",
      "I can live with it",
      "I am neutral",
      "I expect it",
      "I would like it"
    ])
    .setRequired(true);

  // Q15
  form.addParagraphTextItem()
    .setTitle("15. If you could wave a magic wand and eliminate ONE repetitive step between downloading student papers from Blackboard and posting final grades, what would that step be? (Optional: Leave your name/WhatsApp if you want to pilot the USIU Accessible Grader Suite)")
    .setRequired(false);

  // Create & Link a Google Sheet automatically to store faculty responses
  const sheet = SpreadsheetApp.create("USIU_Lecturer_Discovery_Survey_Responses");
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());

  Logger.log("=========================================================================");
  Logger.log("✅ USIU-AFRICA LECTURER DISCOVERY SURVEY CREATED SUCCESSFULLY!");
  Logger.log("🔗 LIVE SURVEY URL (Share with Lecturers): " + form.getPublishedUrl());
  Logger.log("✏️ FORM EDITOR URL:                        " + form.getEditUrl());
  Logger.log("📊 RESPONSES GOOGLE SHEET URL:             " + sheet.getUrl());
  Logger.log("=========================================================================");

  return {
    publishedUrl: form.getPublishedUrl(),
    editUrl: form.getEditUrl(),
    spreadsheetUrl: sheet.getUrl()
  };
}
