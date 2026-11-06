#!/usr/bin/env python3
"""
test_usiu_suite.py — Automated Unit & Integration Test Suite for USIU-Africa Accessible Lecturer Grader v2.0
Verifies:
  1. Multi-format document ingestion (.txt, .docx, .pdf, Blackboard bulk .zip)
  2. Blackboard filename convention parsing (`Assignment_StudentID_attempt_YYYY-MM-DD-HH-MM-SS_Name.docx`)
  3. Zero-drift deterministic rubric evaluation across SST, CSB, and SHSS rubrics
  4. Official USIU-Africa grading scale mapping (A to F, GPA 4.0 to 0.0)
  5. Lecturer human-in-the-loop criterion override & instant recalculation
  6. SQLite 3NF persistence (`USIUGradingDatabase`) and RFC-4180 Blackboard CSV generation
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
DATA_DIR = ROOT_DIR / "data"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from usiu_blackboard_grader import (
    evaluate_submission_deterministic,
    extract_submission_text,
    format_blackboard_csv_string,
    get_rubric_by_id,
    ingest_zip_bytes,
    load_all_rubrics,
    parse_student_identity_from_filename,
    recalculate_with_overrides,
    save_custom_rubric,
    score_to_usiu_letter,
)
from usiu_lecturer_server import USIUGradingDatabase


class TestUSIUAccessibleGraderSuite(unittest.TestCase):

    def test_usiu_grade_scale_boundaries(self):
        self.assertEqual(score_to_usiu_letter(94.3)[:2], ("A", 4.0))
        self.assertEqual(score_to_usiu_letter(88.0)[:2], ("A-", 3.7))
        self.assertEqual(score_to_usiu_letter(85.0)[:2], ("B+", 3.3))
        self.assertEqual(score_to_usiu_letter(80.5)[:2], ("B", 3.0))
        self.assertEqual(score_to_usiu_letter(74.0)[:2], ("C+", 2.3))
        self.assertEqual(score_to_usiu_letter(62.5)[:2], ("D", 1.0))
        self.assertEqual(score_to_usiu_letter(45.0)[:2], ("F", 0.0))

    def test_blackboard_filename_identity_parser(self):
        sid, sname = parse_student_identity_from_filename(
            "TermPaper_665421_attempt_2026-11-06-10-15-00_Amina_Wanjiku_Final.docx"
        )
        self.assertEqual(sid, "665421")
        self.assertEqual(sname, "Amina Wanjiku")

        sid2, sname2 = parse_student_identity_from_filename("668312_Faith_Chepkoech.txt")
        self.assertEqual(sid2, "668312")
        self.assertEqual(sname2, "Faith Chepkoech")

    def test_multi_format_extraction_txt_docx_pdf_zip(self):
        sample_dir = DATA_DIR / "sample_submissions"
        txt_content = extract_submission_text(sample_dir / "665421_Amina_Wanjiku.txt")
        docx_content = extract_submission_text(sample_dir / "669102_Zainab_Hassan.docx")
        pdf_content = extract_submission_text(sample_dir / "669205_David_Kimani.pdf")

        self.assertIn("Kamau et al. (2024)", txt_content)
        self.assertIn("Kamau et al. (2024)", docx_content)
        self.assertIn("Otieno", pdf_content)

        zip_path = DATA_DIR / "outputs" / "Blackboard_Bulk_Submissions_Sample.zip"
        rubric = get_rubric_by_id("standard_research_paper")
        zip_results = ingest_zip_bytes(zip_path.read_bytes(), rubric)
        self.assertEqual(len(zip_results), 3)

    def test_zero_drift_deterministic_consistency(self):
        sample_dir = DATA_DIR / "sample_submissions"
        text = extract_submission_text(sample_dir / "665421_Amina_Wanjiku.txt")
        rubric = get_rubric_by_id("standard_research_paper")
        run1 = evaluate_submission_deterministic("665421", "Amina Wanjiku", text, rubric)
        run2 = evaluate_submission_deterministic("665421", "Amina Wanjiku", text, rubric)
        self.assertEqual(run1["total_score"], run2["total_score"])
        self.assertEqual(run1["letter_grade"], "A")
        self.assertEqual(len(run1["criteria_breakdown"]), 4)

    def test_all_three_usiu_school_rubrics_load(self):
        rubrics = load_all_rubrics()
        self.assertIn("standard_research_paper", rubrics)
        self.assertIn("csb_business_case_study", rubrics)
        self.assertIn("shss_humanities_essay", rubrics)

    def test_lecturer_override_recalculation_and_sqlite_3nf(self):
        rubric = get_rubric_by_id("csb_business_case_study")
        res = evaluate_submission_deterministic(
            "667890", "Brian Otieno", "Short business market note in Kenya.", rubric
        )
        updated = recalculate_with_overrides(
            res,
            {
                "strategic_diagnosis": 24.0,
                "analytical_frameworks": 28.0,
                "financial_operational_evidence": 23.0,
                "action_plan": 18.0,
            },
            custom_feedback="Lecturer manually verified case study presentation.",
        )
        self.assertEqual(updated["total_score"], 93.0)
        self.assertEqual(updated["letter_grade"], "A")
        self.assertTrue(updated["overridden_by_lecturer"])

        # Test SQLite 3NF persistence
        temp_db_path = DATA_DIR / "outputs" / "test_store.sqlite3"
        if temp_db_path.exists():
            temp_db_path.unlink()
        db = USIUGradingDatabase(temp_db_path)
        db.upsert_assessment(updated)
        fetched = db.get_assessment("667890")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["total_score"], 93.0)
        self.assertEqual(len(fetched["criteria_breakdown"]), 4)
        csv_out = format_blackboard_csv_string([fetched])
        self.assertIn("667890", csv_out)
        self.assertIn("Brian Otieno", csv_out)
        temp_db_path.unlink(missing_ok=True)

    def test_custom_assignment_rubric_configuration(self):
        custom = save_custom_rubric({
            "id": "apt3040_midterm_custom",
            "title": "APT3040 Midterm Telemetry & Zero-Trust Rubric",
            "course_code": "APT3040",
            "assignment_prompt": "Analyze zero-trust telemetry in Kenyan banking.",
            "min_words": 150,
            "expected_citations": 2,
            "criteria": [
                {"name": "1. Telemetry Architecture", "weight": 40, "keywords": "telemetry, objective, hypothesis, architecture"},
                {"name": "2. Kenyan Empirical Citations", "weight": 30, "keywords": "kamau, study, data, 2024"},
                {"name": "3. Cybersecurity Trade-offs", "weight": 20, "keywords": "cybersecurity, however, methodology"},
                {"name": "4. APA Structure", "weight": 10, "keywords": "introduction, conclusion, references"},
            ]
        })
        self.assertEqual(custom["id"], "apt3040_midterm_custom")
        self.assertEqual(sum(c["weight"] for c in custom["criteria"]), 100.0)
        loaded = get_rubric_by_id("apt3040_midterm_custom")
        self.assertEqual(loaded["min_words"], 150)


if __name__ == "__main__":
    unittest.main(verbosity=2)
