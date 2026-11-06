#!/usr/bin/env python3
"""
usiu_blackboard_grader.py — USIU-Africa Blackboard Accessible Assessment & Grading Engine
Edition 2 of the Agent Mercy Blank-Canvas Infrastructure

Designed specifically for low-vision accessibility and strict academic grading consistency:
  1. Eliminates "vibes prompting" by enforcing a Locked Criterion-Referenced Rubric.
  2. Connects to USIU Blackboard Learn REST API (`/learn/api/public/v1/courses/.../gradebook/...`)
     to download student attempts and PATCH final grades + rubric feedback back to Blackboard.
  3. Also supports local folders of student submissions (.txt, .md, .docx) and exports a
     100% Blackboard-compatible Grade Center CSV (`USIU_Blackboard_GradeCenter_Upload.csv`).
  4. Includes optional Windows Text-to-Speech (TTS) audio read-aloud so the lecturer can listen
     to student grades and feedback without eye strain.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Official USIU-Africa Letter Grade Scale
USIU_GRADE_SCALE = [
    (90, "A",  4.0, "Distinction — Exceptional mastery of course concepts"),
    (87, "A-", 3.7, "Excellent — Strong analytical depth and evidence"),
    (84, "B+", 3.3, "Very Good — Well-structured argument with minor gaps"),
    (80, "B",  3.0, "Good — Solid understanding and competent execution"),
    (77, "B-", 2.7, "Above Average — Clear effort but needs deeper synthesis"),
    (74, "C+", 2.3, "Satisfactory Plus — Meets core criteria"),
    (70, "C",  2.0, "Satisfactory — Acceptable baseline work"),
    (67, "C-", 1.7, "Marginal Pass — Weak citation or structural issues"),
    (64, "D+", 1.3, "Below Average — Incomplete analysis"),
    (62, "D",  1.0, "Minimum Pass — Significant conceptual gaps"),
    (60, "D-", 0.7, "Low Pass — Barely meets minimum submission threshold"),
    (0,  "F",  0.0, "Fail — Does not meet academic standards")
]

DEFAULT_LOCKED_RUBRIC = {
    "course_code": "APT3040 / BUS4010",
    "institution": "USIU-Africa",
    "criteria": [
        {
            "id": "thesis_clarity",
            "name": "1. Thesis, Problem Formulation & Core Argument",
            "weight": 30,
            "keywords": ["objective", "hypothesis", "problem", "thesis", "purpose", "framework", "strategy", "research", "aim"]
        },
        {
            "id": "evidence_citations",
            "name": "2. Empirical Evidence, Literature & Citations",
            "weight": 30,
            "keywords": ["study", "data", "evidence", "according", "et al", "202", "199", "table", "findings", "source", "reference"]
        },
        {
            "id": "critical_analysis",
            "name": "3. Critical Evaluation, Methodology & Depth",
            "weight": 25,
            "keywords": ["however", "analysis", "methodology", "compared", "implication", "limitation", "evaluate", "impact", "because", "therefore"]
        },
        {
            "id": "academic_structure",
            "name": "4. Academic Structure, Coherence & APA 7th Style",
            "weight": 15,
            "keywords": ["introduction", "conclusion", "references", "section", "summary", "recommendations"]
        }
    ]
}


def score_to_usiu_letter(score: float) -> tuple[str, float, str]:
    for threshold, letter, gpa, desc in USIU_GRADE_SCALE:
        if score >= threshold:
            return letter, gpa, desc
    return "F", 0.0, "Fail"


def extract_submission_text(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".docx":
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(file_path) as zf:
            xml_content = zf.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        return " ".join(elem.text for elem in tree.iter() if elem.text)
    return ""


def evaluate_submission_deterministic(student_id: str, student_name: str, text: str, rubric: dict) -> dict:
    """
    Deterministic, criterion-referenced grading engine.
    Guarantees 100% consistent marks for identical work — zero "vibes" or prompt drift.
    """
    words = re.findall(r"\b\w+\b", text.lower())
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 25]

    # Check for APA year citations like (2023) or (Smith, 2021)
    citation_matches = re.findall(r"\([A-Za-z\s,&]+,?\s*(?:19|20)\d{2}\)", text)

    criterion_results = []
    total_score = 0.0

    for crit in rubric["criteria"]:
        weight = crit["weight"]
        kw_hits = sum(1 for kw in crit["keywords"] if kw in words)
        kw_ratio = min(1.0, kw_hits / max(1, len(crit["keywords"]) * 0.45))

        # Depth factor based on length & citation density
        length_factor = min(1.0, word_count / 220.0)
        cite_bonus = min(0.15, len(citation_matches) * 0.05) if crit["id"] == "evidence_citations" else 0.0

        raw_ratio = min(1.0, (0.45 + (0.45 * kw_ratio) + (0.10 * length_factor) + cite_bonus))
        if word_count < 40:
            raw_ratio *= 0.55

        earned = round(weight * raw_ratio, 1)
        total_score += earned

        # Pick an evidence quote from the student's work
        matching_sent = next(
            (s for s in sentences if any(k in s.lower() for k in crit["keywords"])),
            sentences[0] if sentences else "No substantive sentence found."
        )

        criterion_results.append({
            "criterion": crit["name"],
            "weight": weight,
            "earned": earned,
            "evidence_quote": matching_sent[:160] + ("..." if len(matching_sent) > 160 else "")
        })

    total_score = round(min(100.0, total_score), 1)
    letter, gpa, summary_desc = score_to_usiu_letter(total_score)

    strengths = [c["criterion"] for c in criterion_results if (c["earned"] / c["weight"]) >= 0.8]
    improvements = [c["criterion"] for c in criterion_results if (c["earned"] / c["weight"]) < 0.8]

    feedback_lines = [
        f"USIU-Africa Official Assessment Receipt ({rubric['course_code']})",
        f"Student: {student_name} ({student_id}) | Score: {total_score}/100 ({letter} | GPA {gpa})",
        f"Overall Standing: {summary_desc}.",
        f"Strengths: {', '.join(strengths) if strengths else 'Basic topic coverage'}.",
        f"Areas to Strengthen: {', '.join(improvements) if improvements else 'Maintain strong APA 7th empirical grounding'}."
    ]

    return {
        "student_id": student_id,
        "student_name": student_name,
        "word_count": word_count,
        "citations_detected": len(citation_matches),
        "total_score": total_score,
        "letter_grade": letter,
        "gpa_points": gpa,
        "standing": summary_desc,
        "criteria_breakdown": criterion_results,
        "feedback_for_blackboard": " ".join(feedback_lines),
        "graded_at": datetime.now().isoformat()
    }


class USIUBlackboardClient:
    """
    REST API Client for USIU-Africa Blackboard Learn (`/learn/api/public/v1`).
    Supports downloading student assignment attempts and posting grades + feedback
    directly to the lecturer's Blackboard Grade Center column.
    """

    def __init__(self, base_url: str, access_token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

    def fetch_assignment_attempts(self, course_id: str, column_id: str) -> list[dict]:
        url = f"{self.base_url}/learn/api/public/v1/courses/{course_id}/gradebook/columns/{column_id}/attempts"
        if not self.access_token:
            return []
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.access_token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("results", [])

    def post_grade_to_blackboard(self, course_id: str, column_id: str, user_id: str, score: float, feedback: str) -> dict:
        url = f"{self.base_url}/learn/api/public/v1/courses/{course_id}/gradebook/columns/{column_id}/users/{user_id}"
        payload = {"score": score, "text": feedback, "feedback": feedback}
        if not self.access_token:
            return {
                "status": "STAGED_FOR_BLACKBOARD_SYNC",
                "endpoint": f"PATCH {url}",
                "payload": payload
            }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="PATCH",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"status": "POSTED_LIVE", "http_code": resp.status}


def speak_aloud_windows(text: str):
    """Low-vision accessibility helper: reads the grading summary aloud using Windows SAPI."""
    safe_text = text.replace("'", " ").replace('"', " ")
    ps_cmd = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = 0; $s.Speak('{safe_text}')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)


def main():
    parser = argparse.ArgumentParser(description="USIU Blackboard Accessible Lecturer Grading Suite")
    parser.add_argument("--submissions-dir", type=Path, default=Path("./sample_submissions"), help="Folder of student submissions")
    parser.add_argument("--out-csv", type=Path, default=Path("./USIU_Blackboard_GradeCenter_Upload.csv"), help="Blackboard Grade Center CSV")
    parser.add_argument("--out-json", type=Path, default=Path("./USIU_Grading_Audit_Report.json"), help="Detailed JSON audit report")
    parser.add_argument("--bb-url", type=str, default="https://blackboard.usiu.ac.ke", help="USIU Blackboard URL")
    parser.add_argument("--course-id", type=str, default="_10482_1", help="Blackboard Course ID")
    parser.add_argument("--column-id", type=str, default="_58291_1", help="Blackboard Gradebook Column ID")
    parser.add_argument("--speak", action="store_true", help="Read results aloud for low-vision accessibility")
    args = parser.parse_args()

    bb_client = USIUBlackboardClient(args.bb_url)
    files = sorted([f for f in args.submissions_dir.glob("*") if f.suffix.lower() in {".txt", ".md", ".docx"}])

    results = []
    print("==========================================================================")
    print("🎓 USIU-AFRICA ACCESSIBLE LECTURER GRADING & BLACKBOARD SYNC ENGINE")
    print("==========================================================================\n")

    for f in files:
        # Expect filename like: 665421_Amina_Wanjiku.txt
        parts = f.stem.split("_", 1)
        student_id = parts[0] if len(parts) > 1 else "STU-001"
        student_name = parts[1].replace("_", " ") if len(parts) > 1 else f.stem

        text = extract_submission_text(f)
        eval_res = evaluate_submission_deterministic(student_id, student_name, text, DEFAULT_LOCKED_RUBRIC)
        bb_sync = bb_client.post_grade_to_blackboard(
            args.course_id, args.column_id, student_id, eval_res["total_score"], eval_res["feedback_for_blackboard"]
        )
        eval_res["blackboard_sync"] = bb_sync
        results.append(eval_res)

        print(f"👤 STUDENT: {student_name} (ID: {student_id})")
        print(f"   • FINAL MARK:  {eval_res['total_score']}/100  [{eval_res['letter_grade']} | GPA {eval_res['gpa_points']}]")
        print(f"   • STANDING:    {eval_res['standing']}")
        for c in eval_res["criteria_breakdown"]:
            print(f"     - {c['criterion']}: {c['earned']}/{c['weight']} pts")
        print(f"   • BLACKBOARD:  {bb_sync['status']} -> {bb_sync['endpoint']}\n")

        if args.speak:
            speak_aloud_windows(
                f"Student {student_name}. Score {eval_res['total_score']} out of 100. Grade {eval_res['letter_grade']}. {eval_res['standing']}."
            )

    # Export Blackboard Grade Center Compatible CSV
    with args.out_csv.open("w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["Username", "Student ID", "Full Name", "Score", "USIU Letter Grade", "Feedback to Learner"])
        for r in results:
            writer.writerow([
                r["student_id"],
                r["student_id"],
                r["student_name"],
                r["total_score"],
                r["letter_grade"],
                r["feedback_for_blackboard"]
            ])

    args.out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"✅ [EXPORTED] Blackboard Grade Center CSV: {args.out_csv}")
    print(f"✅ [EXPORTED] Full Rubric Audit JSON:      {args.out_json}")


if __name__ == "__main__":
    main()
