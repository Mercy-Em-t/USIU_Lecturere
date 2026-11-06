#!/usr/bin/env python3
"""
usiu_lecturer_server.py — Local HTTP/REST & SQLite Backend Server for USIU-Africa Accessible Grading Hub
Runs on http://127.0.0.1:8085 (Zero third-party cloud uploads — 100% Kenya Data Protection Act 2019 compliant).

Endpoints:
  • GET  /                      -> Serves the Low-Vision Accessible Web Hub (`index.html`)
  • GET  /api/health            -> Returns server status, Blackboard target version, and active rubric count
  • GET  /api/rubrics           -> Returns all locked USIU rubrics (`SST`, `CSB`, `SHSS`) & USIU grading scale
  • GET  /api/submissions       -> Returns all graded student submissions stored in SQLite/session
  • POST /api/ingest            -> Accepts JSON `{files: [{filename, content_base64, text}], rubric_id}` OR
                                   multipart/form-data file drops (`.pdf`, `.docx`, `.txt`, `.md`, `.zip`)
  • POST /api/override          -> Updates criterion scores & lecturer feedback for a student (`recalculate_with_overrides`)
  • POST /api/speak             -> Triggers offline Windows SAPI5 voice synthesis for low-vision accessibility
  • GET  /api/export/csv        -> Downloads RFC-4180 `USIU_Blackboard_GradeCenter_Upload.csv`
  • GET  /api/export/json       -> Downloads full audit report `USIU_Grading_Audit_Report.json`
  • POST /api/blackboard/sync   -> Stages or PATCHes approved grades to `https://blackboard.usiu.ac.ke`
"""

import argparse
import base64
import email.parser
import io
import json
import contextlib
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "outputs" / "usiu_grading_store.sqlite3"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from usiu_blackboard_grader import (
    USIU_GRADE_SCALE,
    USIUBlackboardClient,
    evaluate_submission_deterministic,
    extract_submission_bytes,
    extract_submission_text,
    format_blackboard_csv_string,
    get_rubric_by_id,
    ingest_zip_bytes,
    load_all_rubrics,
    parse_student_identity_from_filename,
    recalculate_with_overrides,
    speak_aloud_windows,
)


class USIUGradingDatabase:
    """
    3NF Relational SQLite Persistence Engine for USIU Student Assessments.
    Maintains audit trails across `assessments` and `assessment_criteria_scores`.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextlib.contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS assessments (
                    student_id TEXT PRIMARY KEY,
                    student_name TEXT NOT NULL,
                    source_filename TEXT,
                    rubric_id TEXT NOT NULL,
                    rubric_title TEXT,
                    word_count INTEGER DEFAULT 0,
                    citations_detected INTEGER DEFAULT 0,
                    total_score REAL NOT NULL,
                    letter_grade TEXT NOT NULL,
                    gpa_points REAL NOT NULL,
                    standing TEXT,
                    feedback_for_blackboard TEXT,
                    overridden_by_lecturer INTEGER DEFAULT 0,
                    blackboard_sync_json TEXT,
                    graded_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS assessment_criteria_scores (
                    student_id TEXT NOT NULL,
                    criterion_id TEXT NOT NULL,
                    criterion_name TEXT NOT NULL,
                    weight REAL NOT NULL,
                    earned REAL NOT NULL,
                    evidence_quote TEXT,
                    PRIMARY KEY (student_id, criterion_id),
                    FOREIGN KEY (student_id) REFERENCES assessments(student_id) ON DELETE CASCADE
                );
                """
            )

    def upsert_assessment(self, item: Dict[str, Any]):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assessments (
                    student_id, student_name, source_filename, rubric_id, rubric_title,
                    word_count, citations_detected, total_score, letter_grade, gpa_points,
                    standing, feedback_for_blackboard, overridden_by_lecturer,
                    blackboard_sync_json, graded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    student_name=excluded.student_name,
                    source_filename=excluded.source_filename,
                    rubric_id=excluded.rubric_id,
                    rubric_title=excluded.rubric_title,
                    word_count=excluded.word_count,
                    citations_detected=excluded.citations_detected,
                    total_score=excluded.total_score,
                    letter_grade=excluded.letter_grade,
                    gpa_points=excluded.gpa_points,
                    standing=excluded.standing,
                    feedback_for_blackboard=excluded.feedback_for_blackboard,
                    overridden_by_lecturer=excluded.overridden_by_lecturer,
                    blackboard_sync_json=excluded.blackboard_sync_json,
                    graded_at=excluded.graded_at
                """,
                (
                    item["student_id"],
                    item["student_name"],
                    item.get("source_filename", ""),
                    item.get("rubric_id", "standard_research_paper"),
                    item.get("rubric_title", "USIU Rubric"),
                    int(item.get("word_count", 0)),
                    int(item.get("citations_detected", 0)),
                    float(item["total_score"]),
                    item["letter_grade"],
                    float(item["gpa_points"]),
                    item.get("standing", ""),
                    item.get("feedback_for_blackboard", ""),
                    1 if item.get("overridden_by_lecturer") else 0,
                    json.dumps(item.get("blackboard_sync", {})),
                    item.get("graded_at", ""),
                ),
            )
            conn.execute("DELETE FROM assessment_criteria_scores WHERE student_id = ?", (item["student_id"],))
            for idx, c in enumerate(item.get("criteria_breakdown", [])):
                cid = c.get("id") or f"crit_{idx+1}"
                conn.execute(
                    """
                    INSERT INTO assessment_criteria_scores (
                        student_id, criterion_id, criterion_name, weight, earned, evidence_quote
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["student_id"],
                        cid,
                        c["criterion"],
                        float(c["weight"]),
                        float(c["earned"]),
                        c.get("evidence_quote", ""),
                    ),
                )

    def list_assessments(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM assessments ORDER BY student_id ASC").fetchall()
            results = []
            for r in rows:
                c_rows = conn.execute(
                    "SELECT * FROM assessment_criteria_scores WHERE student_id = ? ORDER BY rowid ASC",
                    (r["student_id"],),
                ).fetchall()
                criteria = [
                    {
                        "id": cr["criterion_id"],
                        "criterion": cr["criterion_name"],
                        "weight": cr["weight"],
                        "earned": cr["earned"],
                        "evidence_quote": cr["evidence_quote"],
                    }
                    for cr in c_rows
                ]
                results.append(
                    {
                        "student_id": r["student_id"],
                        "student_name": r["student_name"],
                        "source_filename": r["source_filename"],
                        "rubric_id": r["rubric_id"],
                        "rubric_title": r["rubric_title"],
                        "word_count": r["word_count"],
                        "citations_detected": r["citations_detected"],
                        "total_score": r["total_score"],
                        "letter_grade": r["letter_grade"],
                        "gpa_points": r["gpa_points"],
                        "standing": r["standing"],
                        "criteria_breakdown": criteria,
                        "feedback_for_blackboard": r["feedback_for_blackboard"],
                        "overridden_by_lecturer": bool(r["overridden_by_lecturer"]),
                        "blackboard_sync": json.loads(r["blackboard_sync_json"] or "{}"),
                        "graded_at": r["graded_at"],
                    }
                )
            return results

    def get_assessment(self, student_id: str) -> Dict[str, Any] | None:
        for item in self.list_assessments():
            if item["student_id"] == student_id:
                return item
        return None


def seed_initial_submissions(db: USIUGradingDatabase):
    """Seeds the database with the localized USIU sample submissions if empty."""
    if db.list_assessments():
        return
    sample_dir = DATA_DIR / "sample_submissions"
    if not sample_dir.exists():
        return
    rubric = get_rubric_by_id("standard_research_paper")
    bb_client = USIUBlackboardClient("https://blackboard.usiu.ac.ke")
    for f in sorted(sample_dir.glob("*")):
        if f.suffix.lower() in {".txt", ".md", ".docx", ".pdf"}:
            sid, sname = parse_student_identity_from_filename(f.name)
            text = extract_submission_text(f)
            res = evaluate_submission_deterministic(sid, sname, text, rubric, source_filename=f.name)
            res["blackboard_sync"] = bb_client.post_grade_to_blackboard(
                "_10482_1", "_58291_1", sid, res["total_score"], res["feedback_for_blackboard"]
            )
            db.upsert_assessment(res)


def parse_multipart_files(content_type: str, body: bytes) -> Tuple[Dict[str, str], List[Tuple[str, bytes]]]:
    """
    Pure-Python standard library multipart/form-data parser (Python 3.13 compatible, no `cgi` dependency).
    Returns (form_fields_dict, list_of_(filename, file_bytes)).
    """
    raw_Email = b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + body
    msg = email.parser.BytesParser().parsebytes(raw_Email)
    fields: Dict[str, str] = {}
    files: List[Tuple[str, bytes]] = []

    if msg.is_multipart():
        for part in msg.iter_parts():
            cd = part.get("Content-Disposition", "")
            fname = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            name_match = None
            for param in cd.split(";"):
                param = param.strip()
                if param.startswith("name="):
                    name_match = param.split("=", 1)[1].strip('"')
            if fname:
                files.append((fname, payload))
            elif name_match:
                fields[name_match] = payload.decode("utf-8", errors="ignore")
    return fields, files


class USIULecturerRequestHandler(BaseHTTPRequestHandler):
    db: USIUGradingDatabase = None  # Set at server init

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, payload: Any, status: int = 200):
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in {"/", "/index.html"}:
            index_file = ROOT_DIR / "index.html"
            raw = index_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/api/health":
            self._send_json({
                "status": "ONLINE",
                "engine": "Python 3 Local USIU Grading Server",
                "institution": "USIU-Africa",
                "target_lms": "https://blackboard.usiu.ac.ke (v4001.4.0)",
                "rubrics_available": list(load_all_rubrics().keys()),
                "submissions_count": len(self.db.list_assessments()),
            })
            return

        if path == "/api/rubrics":
            self._send_json({
                "rubrics": load_all_rubrics(),
                "grading_scale": [
                    {"min": t, "letter": l, "gpa": g, "standing": d}
                    for t, l, g, d in USIU_GRADE_SCALE
                ],
            })
            return

        if path == "/api/submissions":
            self._send_json({"submissions": self.db.list_assessments()})
            return

        if path == "/api/export/csv":
            csv_str = format_blackboard_csv_string(self.db.list_assessments())
            raw = csv_str.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="USIU_Blackboard_GradeCenter_Upload.csv"')
            self.send_header("Content-Length", str(len(raw)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/api/export/json":
            self._send_json(self.db.list_assessments())
            return

        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_len) if content_len > 0 else b""
        content_type = self.headers.get("Content-Type", "")

        if path == "/api/ingest":
            ingested: List[Dict[str, Any]] = []
            bb_client = USIUBlackboardClient("https://blackboard.usiu.ac.ke")

            if "multipart/form-data" in content_type:
                fields, files = parse_multipart_files(content_type, body)
                rubric = get_rubric_by_id(fields.get("rubric_id", "standard_research_paper"))
                for fname, fbytes in files:
                    if fname.lower().endswith(".zip"):
                        for res in ingest_zip_bytes(fbytes, rubric):
                            res["blackboard_sync"] = bb_client.post_grade_to_blackboard(
                                "_10482_1", "_58291_1", res["student_id"], res["total_score"], res["feedback_for_blackboard"]
                            )
                            self.db.upsert_assessment(res)
                            ingested.append(res)
                    else:
                        sid, sname = parse_student_identity_from_filename(fname)
                        text = extract_submission_bytes(fname, fbytes)
                        res = evaluate_submission_deterministic(sid, sname, text, rubric, source_filename=fname)
                        res["blackboard_sync"] = bb_client.post_grade_to_blackboard(
                            "_10482_1", "_58291_1", sid, res["total_score"], res["feedback_for_blackboard"]
                        )
                        self.db.upsert_assessment(res)
                        ingested.append(res)
            else:
                payload = json.loads(body.decode("utf-8") or "{}")
                rubric = get_rubric_by_id(payload.get("rubric_id", "standard_research_paper"))
                files_list = payload.get("files", [])
                for fitem in files_list:
                    fname = fitem.get("filename", "669001_Student_Submission.txt")
                    if "content_base64" in fitem and fitem["content_base64"]:
                        fbytes = base64.b64decode(fitem["content_base64"])
                    else:
                        fbytes = (fitem.get("text") or "").encode("utf-8")

                    if fname.lower().endswith(".zip"):
                        for res in ingest_zip_bytes(fbytes, rubric):
                            res["blackboard_sync"] = bb_client.post_grade_to_blackboard(
                                "_10482_1", "_58291_1", res["student_id"], res["total_score"], res["feedback_for_blackboard"]
                            )
                            self.db.upsert_assessment(res)
                            ingested.append(res)
                    else:
                        sid = fitem.get("student_id")
                        sname = fitem.get("student_name")
                        if not sid or not sname:
                            sid, sname = parse_student_identity_from_filename(fname)
                        text = extract_submission_bytes(fname, fbytes)
                        res = evaluate_submission_deterministic(sid, sname, text, rubric, source_filename=fname)
                        res["blackboard_sync"] = bb_client.post_grade_to_blackboard(
                            "_10482_1", "_58291_1", sid, res["total_score"], res["feedback_for_blackboard"]
                        )
                        self.db.upsert_assessment(res)
                        ingested.append(res)

            # Also update CSV and JSON files on disk automatically
            all_rows = self.db.list_assessments()
            (DATA_DIR / "outputs" / "USIU_Blackboard_GradeCenter_Upload.csv").write_text(
                format_blackboard_csv_string(all_rows), encoding="utf-8"
            )
            (DATA_DIR / "outputs" / "USIU_Grading_Audit_Report.json").write_text(
                json.dumps(all_rows, indent=2), encoding="utf-8"
            )

            self._send_json({
                "status": "INGESTED",
                "ingested_count": len(ingested),
                "ingested": ingested,
                "submissions": all_rows,
            })
            return

        if path == "/api/override":
            payload = json.loads(body.decode("utf-8") or "{}")
            student_id = payload.get("student_id", "")
            existing = self.db.get_assessment(student_id)
            if not existing:
                self._send_json({"error": f"Student ID {student_id} not found"}, status=404)
                return
            updated = recalculate_with_overrides(
                existing,
                payload.get("criterion_overrides", {}),
                payload.get("feedback_for_blackboard"),
            )
            self.db.upsert_assessment(updated)
            all_rows = self.db.list_assessments()
            (DATA_DIR / "outputs" / "USIU_Blackboard_GradeCenter_Upload.csv").write_text(
                format_blackboard_csv_string(all_rows), encoding="utf-8"
            )
            (DATA_DIR / "outputs" / "USIU_Grading_Audit_Report.json").write_text(
                json.dumps(all_rows, indent=2), encoding="utf-8"
            )
            self._send_json({"status": "UPDATED", "assessment": updated, "submissions": all_rows})
            return

        if path == "/api/speak":
            payload = json.loads(body.decode("utf-8") or "{}")
            text = payload.get("text", "")
            if text:
                speak_aloud_windows(text)
            self._send_json({"status": "SPOKEN", "text": text})
            return

        if path == "/api/blackboard/sync":
            payload = json.loads(body.decode("utf-8") or "{}")
            course_id = payload.get("course_id", "_10482_1")
            column_id = payload.get("column_id", "_58291_1")
            token = payload.get("access_token", "")
            bb = USIUBlackboardClient("https://blackboard.usiu.ac.ke", access_token=token)
            synced = []
            for item in self.db.list_assessments():
                res = bb.post_grade_to_blackboard(
                    course_id, column_id, item["student_id"], item["total_score"], item["feedback_for_blackboard"]
                )
                item["blackboard_sync"] = res
                self.db.upsert_assessment(item)
                synced.append(res)
            self._send_json({"status": "SYNC_COMPLETE", "count": len(synced), "results": synced})
            return

        self.send_error(404, "Endpoint not found")


def run_server(host: str = "127.0.0.1", port: int = 8085):
    db = USIUGradingDatabase()
    seed_initial_submissions(db)
    USIULecturerRequestHandler.db = db
    server = HTTPServer((host, port), USIULecturerRequestHandler)
    print("==========================================================================")
    print(f"🚀 USIU-AFRICA ACCESSIBLE GRADING SERVER RUNNING AT http://{host}:{port}")
    print("   • Drag-and-Drop Ingestion: .pdf, .docx, .txt, .md, and Blackboard .zip")
    print("   • SQLite 3NF Store:        data/outputs/usiu_grading_store.sqlite3")
    print("==========================================================================")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the USIU-Africa Accessible Grading Local HTTP Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8085, help="Port number (default 8085)")
    args = parser.parse_args()
    run_server(args.host, args.port)
