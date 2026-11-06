#!/usr/bin/env python3
"""
usiu_blackboard_grader.py — USIU-Africa Blackboard Accessible Assessment & Grading Engine
Edition 2.0 — Multi-Format Ingestion (.pdf, .docx, .txt, .md, Blackboard .zip) & Hybrid Rubric Engine

Designed specifically for low-vision accessibility and strict academic grading consistency:
  1. Eliminates "vibes prompting" by enforcing Locked Criterion-Referenced Rubrics from `data/usiu_locked_rubrics.json`.
  2. Ingests individual files (.txt, .md, .docx, .pdf) OR entire Blackboard Grade Center bulk .zip downloads,
     automatically parsing Blackboard's `Assignment_StudentID_attempt_Timestamp_Filename` convention.
  3. Connects to USIU Blackboard Learn REST API (`/learn/api/public/v2/courses/.../gradebook/...`)
     and exports a 100% Blackboard-compatible Grade Center CSV (`USIU_Blackboard_GradeCenter_Upload.csv`).
  4. Includes optional Windows SAPI5 Text-to-Speech (TTS) audio read-aloud (`--speak`).
"""

import argparse
import csv
import io
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
import zlib
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RUBRICS_PATH = DATA_DIR / "usiu_locked_rubrics.json"
KNOWLEDGE_BASE_PATH = DATA_DIR / "usiu_course_knowledge_base.json"

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "have", "has", "had", "not", "but", "what", "all", "when", "can", "more",
    "into", "than", "other", "its", "their", "which", "would", "about", "there",
    "only", "also", "such", "some", "these", "those", "between", "through"
}

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
    "id": "standard_research_paper",
    "title": "USIU-Africa Standardized Research & Term Paper Rubric (SST / General)",
    "school": "School of Science & Technology (SST)",
    "course_code": "APT3040 / BUS4010",
    "institution": "USIU-Africa",
    "criteria": [
        {
            "id": "thesis_clarity",
            "name": "1. Thesis, Problem Formulation & Core Argument",
            "weight": 30,
            "keywords": ["objective", "hypothesis", "problem", "thesis", "purpose", "framework", "strategy", "research", "aim", "architecture", "telemetry"]
        },
        {
            "id": "evidence_citations",
            "name": "2. Empirical Evidence, Literature & APA 7th Citations",
            "weight": 30,
            "keywords": ["study", "data", "evidence", "according", "et al", "202", "199", "table", "findings", "source", "reference", "literature"]
        },
        {
            "id": "critical_analysis",
            "name": "3. Critical Evaluation, Methodology & Depth",
            "weight": 25,
            "keywords": ["however", "analysis", "methodology", "compared", "implication", "limitation", "evaluate", "impact", "because", "therefore", "trade-off"]
        },
        {
            "id": "academic_structure",
            "name": "4. Academic Structure, Coherence & APA 7th Style",
            "weight": 15,
            "keywords": ["introduction", "conclusion", "references", "section", "summary", "recommendations", "abstract"]
        }
    ]
}


def load_all_rubrics() -> Dict[str, Any]:
    """Loads all locked USIU rubrics from data/usiu_locked_rubrics.json with fallback."""
    if RUBRICS_PATH.exists():
        try:
            data = json.loads(RUBRICS_PATH.read_text(encoding="utf-8"))
            if "rubrics" in data:
                return data["rubrics"]
        except Exception:
            pass
    return {"standard_research_paper": DEFAULT_LOCKED_RUBRIC}


def save_custom_rubric(rubric_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and persists a lecturer-configured custom rubric / marking scheme
    into `data/usiu_locked_rubrics.json` so it can be reused across sessions and courses.
    Enforces 100-point normalization across criteria weights.
    """
    rubric_id = re.sub(r"[^a-zA-Z0-9_]", "_", (rubric_obj.get("id") or rubric_obj.get("title", "custom_rubric")).lower()).strip("_")
    if not rubric_id:
        rubric_id = "custom_usiu_rubric"

    raw_criteria = rubric_obj.get("criteria", [])
    if not raw_criteria:
        raise ValueError("Custom rubric must define at least one marking criterion.")

    total_w = sum(float(c.get("weight", 25)) for c in raw_criteria) or 100.0
    normalized_criteria = []
    running_sum = 0.0
    for idx, c in enumerate(raw_criteria):
        cid = re.sub(r"[^a-zA-Z0-9_]", "_", (c.get("id") or c.get("name", f"crit_{idx+1}")).lower()).strip("_")
        if idx == len(raw_criteria) - 1:
            weight = round(100.0 - running_sum, 1)
        else:
            weight = round((float(c.get("weight", 25)) / total_w) * 100.0, 1)
            running_sum += weight

        kws = c.get("keywords", [])
        if isinstance(kws, str):
            kws = [k.strip().lower() for k in kws.split(",") if k.strip()]
        else:
            kws = [str(k).strip().lower() for k in kws if str(k).strip()]

        normalized_criteria.append({
            "id": cid or f"crit_{idx+1}",
            "name": c.get("name") or f"{idx+1}. Criterion {idx+1}",
            "weight": weight,
            "keywords": kws or ["analysis", "evidence", "study", "objective"]
        })

    clean_rubric = {
        "id": rubric_id,
        "title": rubric_obj.get("title") or f"USIU Custom Rubric ({rubric_id})",
        "school": rubric_obj.get("school") or "USIU-Africa Faculty Custom",
        "course_code": rubric_obj.get("course_code") or "USIU Course",
        "assignment_prompt": rubric_obj.get("assignment_prompt") or "",
        "min_words": int(rubric_obj.get("min_words", 220)),
        "expected_citations": int(rubric_obj.get("expected_citations", 3)),
        "total_points": 100,
        "criteria": normalized_criteria
    }

    full_doc = {"institution": "United States International University - Africa (USIU-Africa)", "version": "2.1.0", "rubrics": load_all_rubrics()}
    full_doc["rubrics"][rubric_id] = clean_rubric
    RUBRICS_PATH.write_text(json.dumps(full_doc, indent=2), encoding="utf-8")
    return clean_rubric


def get_rubric_by_id(rubric_id: str) -> Dict[str, Any]:
    rubrics = load_all_rubrics()
    rub = rubrics.get(rubric_id) or rubrics.get("standard_research_paper") or DEFAULT_LOCKED_RUBRIC
    if "course_code" not in rub:
        courses = rub.get("courses", ["APT3040", "BUS4010"])
        rub["course_code"] = " / ".join(courses[:2])
    return rub


def score_to_usiu_letter(score: float) -> Tuple[str, float, str]:
    for threshold, letter, gpa, desc in USIU_GRADE_SCALE:
        if score >= threshold:
            return letter, gpa, desc
    return "F", 0.0, "Fail — Does not meet academic standards"


def parse_student_identity_from_filename(filename: str) -> Tuple[str, str]:
    """
    Parses student ID and full name from either:
      1. Blackboard Bulk Download pattern:
         `CaseStudy1_665421_attempt_2026-11-06-10-30-00_Amina_Wanjiku_Essay.docx`
      2. Standard USIU ID prefix pattern:
         `665421_Amina_Wanjiku.txt` or `665421-Amina-Wanjiku.pdf`
      3. Arbitrary filename fallback.
    """
    stem = Path(filename).stem

    # Pattern 1: Blackboard bulk download `Assignment_Username_attempt_YYYY-MM-DD-HH-MM-SS_OriginalName`
    bb_match = re.match(
        r"^.+?_([A-Za-z0-9\-]+)_attempt_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}_(.+)$",
        stem,
        re.IGNORECASE
    )
    if bb_match:
        student_id = bb_match.group(1)
        raw_name = bb_match.group(2).replace("_", " ").replace("-", " ").strip()
        # Clean trailing document words like "Final Paper" if name is present
        cleaned_name = re.sub(r"\b(final|essay|paper|assignment|submission|draft)\b", "", raw_name, flags=re.IGNORECASE).strip()
        return student_id, (cleaned_name if len(cleaned_name) >= 3 else f"Student {student_id}")

    # Pattern 2: Leading 6-digit USIU ID `665421_Amina_Wanjiku`
    id_match = re.match(r"^(\d{5,8})[_\-\s]+(.+)$", stem)
    if id_match:
        student_id = id_match.group(1)
        student_name = id_match.group(2).replace("_", " ").replace("-", " ").strip()
        return student_id, student_name

    # Pattern 3: Embedded 6-digit USIU ID anywhere in stem
    any_id = re.search(r"\b(6\d{5})\b", stem)
    if any_id:
        student_id = any_id.group(1)
        remainder = stem.replace(student_id, "").replace("_", " ").replace("-", " ").strip()
        return student_id, (remainder if remainder else f"USIU Student {student_id}")

    # Fallback
    parts = stem.split("_", 1)
    if len(parts) > 1 and parts[0].isalnum():
        return parts[0], parts[1].replace("_", " ")
    return "669999", stem.replace("_", " ").replace("-", " ").strip() or "Anonymous Student"


def extract_text_from_docx_bytes(raw_bytes: bytes) -> str:
    """Extracts UTF-8 plain text from a .docx Word XML archive in memory."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            if "word/document.xml" not in zf.namelist():
                return ""
            xml_content = zf.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        paragraphs = []
        for elem in tree.iter():
            if elem.tag.endswith("}p"):
                p_text = "".join(t.text for t in elem.iter() if t.tag.endswith("}t") and t.text)
                if p_text.strip():
                    paragraphs.append(p_text.strip())
        if paragraphs:
            return "\n".join(paragraphs)
        return " ".join(elem.text for elem in tree.iter() if elem.text)
    except Exception:
        return ""


def extract_text_from_pdf_bytes(raw_bytes: bytes) -> str:
    """
    Multi-stage PDF text extractor:
      Stage 1: Uses `pypdf` / `PyPDF2` if installed in the environment.
      Stage 2: Pure-Python FlateDecode stream & PDF literal string `( ... )` / `TJ` parser
               so `.pdf` ingestion works with zero external pip dependencies.
    """
    # Stage 1: Try pypdf / PyPDF2 if available
    for mod_name in ("pypdf", "PyPDF2"):
        try:
            pdf_mod = __import__(mod_name)
            reader = pdf_mod.PdfReader(io.BytesIO(raw_bytes))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            joined = "\n".join(pages_text).strip()
            if len(joined) > 20:
                return joined
        except Exception:
            pass

    # Stage 2: Pure-Python PDF stream & literal string parser
    extracted_chunks: List[str] = []

    def _extract_pdf_strings(content_str: str):
        # Extract strings inside parentheses (...) and array blocks [...] TJ
        for match in re.finditer(r"\(([^()\\]*(?:\\.[^()\\]*)*)\)", content_str):
            token = match.group(1)
            token = (
                token.replace(r"\(", "(")
                .replace(r"\)", ")")
                .replace(r"\n", " ")
                .replace(r"\r", " ")
                .replace(r"\t", " ")
            )
            # Filter out binary/font metadata noise
            if re.search(r"[A-Za-z]{2,}", token):
                extracted_chunks.append(token)

    # Scan decompressed FlateDecode streams first
    for stream_match in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, re.DOTALL):
        stream_data = stream_match.group(1)
        for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
            try:
                decompressed = zlib.decompress(stream_data, wbits)
                _extract_pdf_strings(decompressed.decode("latin-1", errors="ignore"))
                break
            except Exception:
                continue

    # Also scan uncompressed PDF body text
    _extract_pdf_strings(raw_bytes.decode("latin-1", errors="ignore"))
    return " ".join(extracted_chunks).strip()


def extract_submission_bytes(filename: str, raw_bytes: bytes) -> str:
    """Extracts text from .txt, .md, .docx, or .pdf byte streams."""
    ext = Path(filename).suffix.lower()
    if ext in {".txt", ".md", ".csv", ".html"}:
        return raw_bytes.decode("utf-8", errors="ignore")
    if ext == ".docx":
        return extract_text_from_docx_bytes(raw_bytes)
    if ext == ".pdf":
        return extract_text_from_pdf_bytes(raw_bytes)
    return raw_bytes.decode("utf-8", errors="ignore")


def extract_submission_text(file_path: Path) -> str:
    """Extracts text from a local file path (.txt, .md, .docx, .pdf)."""
    return extract_submission_bytes(file_path.name, file_path.read_bytes())


def ingest_zip_bytes(zip_bytes: bytes, rubric: dict) -> List[Dict[str, Any]]:
    """
    Unpacks a Blackboard Grade Center bulk download `.zip` archive in memory,
    ignoring Blackboard's auto-generated `.txt` receipt headers if a corresponding
    student `.docx` / `.pdf` / `.txt` essay exists, and grades every submission.
    """
    results: List[Dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        entries = [
            info for info in zf.infolist()
            if not info.is_dir()
            and not Path(info.filename).name.startswith(".")
            and not info.filename.startswith("__MACOSX")
            and Path(info.filename).suffix.lower() in {".txt", ".md", ".docx", ".pdf"}
        ]
        for info in entries:
            fname = Path(info.filename).name
            raw_bytes = zf.read(info.filename)
            text = extract_submission_bytes(fname, raw_bytes)
            if not text or len(text.strip()) < 10:
                continue
            student_id, student_name = parse_student_identity_from_filename(fname)
            eval_res = evaluate_submission_deterministic(
                student_id, student_name, text, rubric, source_filename=fname
            )
            results.append(eval_res)
    return results


def load_course_knowledge_base() -> Dict[str, Any]:
    """Loads the Course Material Knowledge Base & Synonym Clusters from data/usiu_course_knowledge_base.json."""
    if KNOWLEDGE_BASE_PATH.exists():
        try:
            return json.loads(KNOWLEDGE_BASE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"synonym_clusters": {}, "course_materials": []}


def extract_salient_domain_concepts(text: str, top_k: int = 24) -> List[str]:
    """
    Extracts salient academic domain concepts, theories, and technical terms from uploaded
    lecture notes, syllabus documents, or marking guides.
    """
    tokens = [
        t for t in re.findall(r"\b[a-zA-Z][a-zA-Z0-9\-]{3,}\b", text.lower())
        if t not in STOPWORDS
    ]
    counts = Counter(tokens)
    return [term for term, _ in counts.most_common(top_k)]


def ingest_course_material_document(
    title: str,
    course_code: str,
    text: str,
    material_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ingests a lecturer's course material document (Lecture Notes, Syllabus, Case Study Brief,
    or Model Answer) into `data/usiu_course_knowledge_base.json` so student submissions are
    evaluated against the lecturer's actual taught domain concepts and semantic context.
    """
    kb = load_course_knowledge_base()
    mid = material_id or re.sub(r"[^a-zA-Z0-9_]", "_", f"{course_code}_{title}".lower()).strip("_")[:48]
    extracted_concepts = extract_salient_domain_concepts(text, top_k=24)

    new_entry = {
        "id": mid,
        "course_code": course_code,
        "title": title,
        "content": text.strip()[:12000],
        "extracted_concepts": extracted_concepts,
        "ingested_at": datetime.now().isoformat()
    }

    materials = [m for m in kb.get("course_materials", []) if m.get("id") != mid]
    materials.append(new_entry)
    kb["course_materials"] = materials
    KNOWLEDGE_BASE_PATH.write_text(json.dumps(kb, indent=2), encoding="utf-8")
    return new_entry


def stem_academic_token(word: str) -> str:
    """Lightweight morphological stemmer so 'analyzing', 'analytical', and 'analysis' match."""
    w = word.lower().strip()
    if len(w) <= 5:
        return w
    for suffix in ("ization", "ational", "fulness", "ousness", "iveness", "ologies", "ology", "ments", "ment", "ating", "ition", "ation", "ities", "ally", "ical", "ance", "ence", "ings", "ing", "edly", "ies", "ers", "ion", "ive", "ous", "ful", "est", "ed", "es", "ly", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[:-len(suffix)]
    return w


def compute_semantic_course_similarity(student_text: str, course_materials_text: str) -> float:
    """
    Computes a hybrid Word-Stem TF + Character 4-gram Cosine Similarity in [0.0, 1.0]
    between a student's submission and the lecturer's uploaded course materials.
    Rewards students who discuss the course's core subject matter even when paraphrasing!
    """
    if not student_text.strip() or not course_materials_text.strip():
        return 0.0

    stu_stems = Counter(
        stem_academic_token(w) for w in re.findall(r"\b[a-zA-Z]{4,}\b", student_text.lower())
        if w.lower() not in STOPWORDS
    )
    mat_stems = Counter(
        stem_academic_token(w) for w in re.findall(r"\b[a-zA-Z]{4,}\b", course_materials_text.lower())
        if w.lower() not in STOPWORDS
    )
    if not stu_stems or not mat_stems:
        return 0.0

    shared = set(stu_stems.keys()) & set(mat_stems.keys())
    dot = sum(stu_stems[k] * mat_stems[k] for k in shared)
    norm_a = math.sqrt(sum(v * v for v in stu_stems.values()))
    norm_b = math.sqrt(sum(v * v for v in mat_stems.values()))
    cosine = (dot / (norm_a * norm_b)) if (norm_a > 0 and norm_b > 0) else 0.0

    # Normalize typical academic cosine overlap (0.25+ is strong topical alignment) into [0.0, 1.0]
    return round(min(1.0, cosine / 0.28), 3)


ADVERSARIAL_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rubrics|rules)",
    r"disregard\s+(?:the\s+)?(?:rubric|instructions|grading)",
    r"system\s*prompt",
    r"you\s+are\s+(?:now\s+)?a\s+helpful\s+grading",
    r"(?:award|give|assign)\s+(?:me\s+|this\s+paper\s+)?(?:100|full\s+marks|grade\s+a)",
    r"override\s+(?:score|grade|rubric)",
    r"[\u200b\u200c\u200d\ufeff]{3,}"  # Hidden zero-width Unicode injection
]


def inspect_submission_security_and_anomalies(text: str, all_rubric_keywords: List[str]) -> Dict[str, Any]:
    """
    Zero-Trust Security & Anti-Gaming Scanner (v2.3):
      1. Detects adversarial prompt-injection / grade-tampering instructions hidden in student essays.
      2. Detects keyword-stuffing / low-entropy lists where students dump rubric keywords without prose.
    """
    lower = text.lower()
    words = re.findall(r"\b\w+\b", lower)
    word_count = len(words)
    unique_words = len(set(words))
    lexical_diversity = round(unique_words / max(1, word_count), 3)

    injection_hits = []
    for pat in ADVERSARIAL_INJECTION_PATTERNS:
        m = re.search(pat, lower)
        if m:
            injection_hits.append(m.group(0))

    # Check for keyword stuffing: high concentration of rubric keywords in a short/repetitive block
    kw_set = {k.lower() for k in all_rubric_keywords}
    total_kw_occurrences = sum(1 for w in words if w in kw_set)
    kw_density = round(total_kw_occurrences / max(1, word_count), 3)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 20]

    keyword_stuffing_detected = (
        (word_count >= 25 and lexical_diversity < 0.32)
        or (kw_density > 0.35 and len(sentences) <= 2)
    )

    quarantined_from_learning = bool(injection_hits or keyword_stuffing_detected)
    alerts = []
    if injection_hits:
        alerts.append({
            "severity": "CRITICAL",
            "type": "ADVERSARIAL_INJECTION_ATTEMPT",
            "message": f"Detected adversarial prompt/grade manipulation phrase: '{injection_hits[0]}'. Quarantined from cohort learning and flagged for Lecturer Intervention."
        })
    if keyword_stuffing_detected:
        alerts.append({
            "severity": "HIGH",
            "type": "KEYWORD_STUFFING_ANOMALY",
            "message": f"Low lexical diversity ({int(lexical_diversity*100)}%) or abnormal keyword density ({int(kw_density*100)}%). Blocked from cohort learning and capped."
        })

    return {
        "prompt_injection_detected": bool(injection_hits),
        "injection_matches": injection_hits,
        "keyword_stuffing_detected": keyword_stuffing_detected,
        "lexical_diversity": lexical_diversity,
        "keyword_density": kw_density,
        "quarantined_from_learning": quarantined_from_learning,
        "security_alerts": alerts
    }


def evaluate_submission_deterministic(
    student_id: str,
    student_name: str,
    text: str,
    rubric: dict,
    source_filename: str = ""
) -> dict:
    """
    Fairness-Guarded, Course-Material-Grounded Deterministic Assessment Engine (v2.2).
    Combines 3 signals so students are NEVER unfairly penalized for paraphrasing:
      1. Synonym Cluster & Morphological Stem Matching (recognizes academic synonyms & word stems)
      2. Course Material Semantic Alignment (cosine similarity against uploaded Lecture Notes / Syllabus)
      3. Academic Discourse & Argumentation Coherence (Claim -> Evidence -> Nuance -> Synthesis)
    """
    kb = load_course_knowledge_base()
    synonym_clusters = kb.get("synonym_clusters", {})
    course_materials = kb.get("course_materials", [])
    combined_course_notes = " ".join(m.get("content", "") for m in course_materials)
    course_concepts = set()
    for m in course_materials:
        for c in m.get("extracted_concepts", []):
            course_concepts.add(c.lower())

    lower_text = text.lower()
    words = re.findall(r"\b\w+\b", lower_text)
    word_set = set(words)
    stem_set = {stem_academic_token(w) for w in words if len(w) >= 4}
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 25]

    # Check for APA year citations like (2023) or (Smith, 2021) or [2024]
    citation_matches = re.findall(r"[\(\[][A-Za-z\s,&.\-]*?(?:19|20)\d{2}[a-z]?[\)\]]", text)

    # Compute overall semantic alignment with uploaded USIU Course Materials
    semantic_similarity = compute_semantic_course_similarity(text, combined_course_notes)
    matched_course_concepts = [c for c in course_concepts if c in lower_text or stem_academic_token(c) in stem_set]

    # Run Zero-Trust Security & Anti-Gaming Scanner
    all_rubric_kws = [kw for c in rubric["criteria"] for kw in c.get("keywords", [])]
    security_scan = inspect_submission_security_and_anomalies(text, all_rubric_kws)

    criterion_results = []
    total_score = 0.0
    fairness_boost_applied = False

    min_words = max(50.0, float(rubric.get("min_words", 220)))
    expected_cites = max(1, int(rubric.get("expected_citations", 3)))
    length_factor = min(1.0, word_count / min_words)

    for crit in rubric["criteria"]:
        weight = crit["weight"]
        exact_hits = 0
        synonym_or_stem_hits = 0

        for kw in crit["keywords"]:
            kw_low = kw.lower()
            kw_stem = stem_academic_token(kw_low)
            cluster = synonym_clusters.get(kw_low, [kw_low])

            if kw_low in word_set or kw_low in lower_text:
                exact_hits += 1
                synonym_or_stem_hits += 1
            elif kw_stem in stem_set or any(syn in lower_text for syn in cluster):
                synonym_or_stem_hits += 1

        # Use the expanded synonym + stem hit count so paraphrasing is fairly rewarded
        kw_ratio = min(1.0, synonym_or_stem_hits / max(1.0, len(crit["keywords"]) * 0.45))

        # Fairness Guard: If student's semantic alignment with course lecture notes + sentence depth
        # is higher than their exact keyword ratio, blend in the semantic course material alignment!
        discourse_coherence = min(1.0, (len(sentences) / 6.0) * 0.6 + (semantic_similarity * 0.4))
        if semantic_similarity >= 0.55 and word_count >= 90 and kw_ratio < 0.78:
            boosted_ratio = max(kw_ratio, round((kw_ratio * 0.55) + (semantic_similarity * 0.30) + (discourse_coherence * 0.15), 3))
            if boosted_ratio > kw_ratio + 0.05:
                fairness_boost_applied = True
            kw_ratio = boosted_ratio

        cite_bonus = (
            min(0.15, (len(citation_matches) / expected_cites) * 0.15)
            if crit["id"] in {"evidence_citations", "historical_empirical_sources", "financial_operational_evidence"}
            or "citation" in crit["name"].lower() or "evidence" in crit["name"].lower()
            else 0.0
        )

        raw_ratio = min(1.0, (0.45 + (0.45 * kw_ratio) + (0.10 * length_factor) + cite_bonus))
        if word_count < 40:
            raw_ratio *= 0.55
        if security_scan["keyword_stuffing_detected"] or security_scan["prompt_injection_detected"]:
            # Prevent gaming: cap raw ratio if keyword stuffing or prompt injection is present
            raw_ratio = min(raw_ratio, 0.50)

        earned = round(weight * raw_ratio, 1)
        total_score += earned

        # Pick an evidence quote from the student's work (checking keywords AND synonyms)
        expanded_terms = []
        for kw in crit["keywords"]:
            expanded_terms.extend(synonym_clusters.get(kw.lower(), [kw.lower()]))
        matching_sent = next(
            (s for s in sentences if any(k in s.lower() for k in expanded_terms)),
            sentences[0] if sentences else "No substantive sentence found."
        )

        criterion_results.append({
            "id": crit["id"],
            "criterion": crit["name"],
            "weight": weight,
            "earned": earned,
            "exact_hits": exact_hits,
            "synonym_or_stem_hits": synonym_or_stem_hits,
            "evidence_quote": matching_sent[:160] + ("..." if len(matching_sent) > 160 else "")
        })

    total_score = round(min(100.0, total_score), 1)
    letter, gpa, summary_desc = score_to_usiu_letter(total_score)

    strengths = [c["criterion"] for c in criterion_results if (c["earned"] / c["weight"]) >= 0.8]
    improvements = [c["criterion"] for c in criterion_results if (c["earned"] / c["weight"]) < 0.8]

    course_label = rubric.get("course_code") or rubric.get("title", "USIU Course")
    feedback_lines = [
        f"USIU-Africa Official Assessment Receipt ({course_label})",
        f"Student: {student_name} ({student_id}) | Score: {total_score}/100 ({letter} | GPA {gpa})",
        f"Overall Standing: {summary_desc}.",
        f"Course Material Alignment: {int(semantic_similarity * 100)}% ({len(matched_course_concepts)} lecture concepts matched).",
        f"Strengths: {', '.join(strengths) if strengths else 'Basic topic coverage'}.",
        f"Areas to Strengthen: {', '.join(improvements) if improvements else 'Maintain strong APA 7th empirical grounding'}."
    ]

    return {
        "student_id": student_id,
        "student_name": student_name,
        "source_filename": source_filename,
        "rubric_id": rubric.get("id", "standard_research_paper"),
        "rubric_title": rubric.get("title", "USIU-Africa Standardized Rubric"),
        "word_count": word_count,
        "citations_detected": len(citation_matches),
        "course_material_alignment_pct": int(round(semantic_similarity * 100)),
        "matched_course_concepts": matched_course_concepts[:10],
        "fairness_guard_triggered": fairness_boost_applied,
        "security_scan": security_scan,
        "needs_lecturer_intervention": bool(
            security_scan["quarantined_from_learning"]
            or total_score < 70.0
            or len(citation_matches) == 0
        ),
        "total_score": total_score,
        "letter_grade": letter,
        "gpa_points": gpa,
        "standing": summary_desc,
        "criteria_breakdown": criterion_results,
        "feedback_for_blackboard": " ".join(feedback_lines),
        "graded_at": datetime.now().isoformat()
    }


def extract_verified_student_cohort_concepts(
    assessments_with_texts: List[Tuple[Dict[str, Any], str]]
) -> List[Dict[str, Any]]:
    """
    Smart, Anti-Poisoning Student Cohort Learning Engine (v2.3):
    Extracts candidate emergent domain concepts ONLY from student submissions that pass ALL 4 gates:
      Gate 1: Zero prompt-injection or grade-tampering patterns (`not quarantined_from_learning`)
      Gate 2: Healthy lexical diversity (`TTR >= 0.35`)
      Gate 3: High academic performance (`total_score >= 85.0`, A or A- standing) AND
              strong alignment (`>= 55%`) with the Lecturer's official Course Materials
      Gate 4: Staged as `PENDING_LECTURER_APPROVAL` — never modifies the locked rubric blindly!
    """
    kb = load_course_knowledge_base()
    existing_concepts = set()
    for m in kb.get("course_materials", []):
        for c in m.get("extracted_concepts", []):
            existing_concepts.add(c.lower())
    for syn_list in kb.get("synonym_clusters", {}).values():
        for s in syn_list:
            existing_concepts.add(s.lower())

    approved_Set = {c.lower() for c in kb.get("lecturer_approved_student_concepts", [])}
    existing_concepts |= approved_Set

    candidate_counter: Counter = Counter()
    supporting_students: Dict[str, List[str]] = {}

    for eval_res, raw_text in assessments_with_texts:
        sec = eval_res.get("security_scan", {})
        if sec.get("quarantined_from_learning"):
            continue
        if float(eval_res.get("total_score", 0)) < 85.0:
            continue
        if int(eval_res.get("course_material_alignment_pct", 0)) < 55:
            continue

        tokens = [
            t for t in re.findall(r"\b[a-zA-Z][a-zA-Z0-9\-]{4,}\b", raw_text.lower())
            if t not in STOPWORDS and t not in existing_concepts
        ]
        unique_paper_terms = set(tokens)
        for term in unique_paper_terms:
            candidate_counter[term] += 1
            supporting_students.setdefault(term, []).append(
                f"{eval_res['student_name']} ({eval_res['student_id']})"
            )

    staged_candidates = []
    for term, freq in candidate_counter.most_common(12):
        staged_candidates.append({
            "concept": term,
            "peer_frequency": freq,
            "supporting_high_performers": supporting_students.get(term, [])[:4],
            "status": "PENDING_LECTURER_APPROVAL",
            "safety_verification": "Passed Anti-Injection, Entropy & Course-Alignment Gates (A/A- Cohort)"
        })

    kb["staged_student_concepts"] = staged_candidates
    KNOWLEDGE_BASE_PATH.write_text(json.dumps(kb, indent=2), encoding="utf-8")
    return staged_candidates


def approve_staged_student_concept(concept: str) -> Dict[str, Any]:
    """
    Promotes a staged student-derived concept into the active Course Knowledge Base
    ONLY after explicit Lecturer approval.
    """
    kb = load_course_knowledge_base()
    clean_c = concept.strip().lower()
    approved = kb.get("lecturer_approved_student_concepts", [])
    if clean_c and clean_c not in approved:
        approved.append(clean_c)
    kb["lecturer_approved_student_concepts"] = approved
    # Also append to first course material's extracted_concepts so semantic alignment uses it
    if kb.get("course_materials"):
        ec = kb["course_materials"][0].get("extracted_concepts", [])
        if clean_c not in ec:
            ec.append(clean_c)
    kb["staged_student_concepts"] = [
        item for item in kb.get("staged_student_concepts", [])
        if item.get("concept", "").lower() != clean_c
    ]
    KNOWLEDGE_BASE_PATH.write_text(json.dumps(kb, indent=2), encoding="utf-8")
    return kb


def generate_cohort_intervention_report(assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executive Intervention, Anomaly & Pedagogical Recommendation Suite (v2.3):
    Analyzes all graded submissions to surface:
      1. Priority Lecturer Intervention Alerts (Security/Injection attempts, Failing/At-Risk students <70%, Missing APA citations, Paraphrase Fairness reviews)
      2. Pillar-by-Pillar Cohort Performance Diagnostics
      3. Actionable Teaching & Curriculum Recommendations for the Lecturer
      4. Smart Cohort-Derived Candidate Concepts awaiting Lecturer Approval
    """
    if not assessments:
        return {
            "cohort_size": 0,
            "mean_score": 0.0,
            "intervention_alerts": [],
            "pillar_diagnostics": [],
            "pedagogical_recommendations": [],
            "staged_student_concepts": []
        }

    n = len(assessments)
    mean_score = round(sum(float(a["total_score"]) for a in assessments) / n, 1)
    pass_count = sum(1 for a in assessments if float(a["total_score"]) >= 70.0)
    distinction_count = sum(1 for a in assessments if float(a["total_score"]) >= 90.0)

    intervention_alerts = []
    for a in assessments:
        sid = a["student_id"]
        sname = a["student_name"]
        score = float(a["total_score"])
        letter = a["letter_grade"]
        cites = int(a.get("citations_detected", 0))
        sec = a.get("security_scan", {})

        # 1. Critical Security / Injection / Keyword Stuffing Alerts
        for alert in sec.get("security_alerts", []):
            intervention_alerts.append({
                "priority": "CRITICAL",
                "category": alert["type"],
                "student_id": sid,
                "student_name": sname,
                "score": score,
                "letter_grade": letter,
                "trigger": alert["message"],
                "recommended_action": "Inspect raw submission text immediately; quarantine from cohort learning and conduct academic integrity review."
            })

        # 2. Academic At-Risk / Remediation Alert (< 70% C threshold)
        if score < 70.0:
            weak_pillars = [
                c["criterion"] for c in a.get("criteria_breakdown", [])
                if (float(c["earned"]) / max(1.0, float(c["weight"]))) < 0.72
            ]
            intervention_alerts.append({
                "priority": "HIGH",
                "category": "AT_RISK_ACADEMIC_PERFORMANCE",
                "student_id": sid,
                "student_name": sname,
                "score": score,
                "letter_grade": letter,
                "trigger": f"Scored {score}/100 ({letter}), below USIU 70% Satisfactory C benchmark. Weakest pillars: {', '.join(weak_pillars) or 'General depth'}.",
                "recommended_action": "Schedule 10-minute office hours consultation and share USIU Writing Center APA 7th guide."
            })
        elif cites == 0:
            intervention_alerts.append({
                "priority": "MEDIUM",
                "category": "MISSING_APA_CITATIONS",
                "student_id": sid,
                "student_name": sname,
                "score": score,
                "letter_grade": letter,
                "trigger": "Zero in-text APA (Author, Year) empirical citations detected in submission.",
                "recommended_action": "Remind student to ground claims in peer-reviewed regional literature."
            })

        # 3. Paraphrase Fairness Guard Review Notification
        if a.get("fairness_guard_triggered"):
            intervention_alerts.append({
                "priority": "INFO",
                "category": "FAIRNESS_GUARD_PARAPHRASE_BOOST",
                "student_id": sid,
                "student_name": sname,
                "score": score,
                "letter_grade": letter,
                "trigger": f"Student paraphrased concepts with {a.get('course_material_alignment_pct', 0)}% lecture-note alignment; Fairness Guard prevented unfair keyword penalty.",
                "recommended_action": "Press 1–4 to hear verbatim quote and confirm agreement with Fairness Guard adjustment."
            })

    # Pillar-by-Pillar Cohort Diagnostics
    pillar_map: Dict[str, List[float]] = {}
    pillar_weights: Dict[str, float] = {}
    for a in assessments:
        for c in a.get("criteria_breakdown", []):
            cname = c["criterion"]
            w = float(c["weight"])
            pct = (float(c["earned"]) / max(1.0, w)) * 100.0
            pillar_map.setdefault(cname, []).append(pct)
            pillar_weights[cname] = w

    pillar_diagnostics = []
    pedagogical_recommendations = []

    for cname, pct_list in pillar_map.items():
        avg_pct = round(sum(pct_list) / len(pct_list), 1)
        status = "STRONG" if avg_pct >= 85.0 else ("MODERATE" if avg_pct >= 75.0 else "NEEDS_ATTENTION")
        pillar_diagnostics.append({
            "criterion": cname,
            "weight": pillar_weights[cname],
            "cohort_average_pct": avg_pct,
            "status": status
        })
        if avg_pct < 82.0:
            pedagogical_recommendations.append({
                "target_pillar": cname,
                "cohort_average_pct": avg_pct,
                "recommendation": f"Cohort averaged {avg_pct}% on '{cname}'. Dedicate 15 minutes in the next lecture to walk through a concrete A-grade exemplar and clarify rubric expectations."
            })

    if not pedagogical_recommendations:
        pedagogical_recommendations.append({
            "target_pillar": "Overall Cohort Mastery",
            "cohort_average_pct": mean_score,
            "recommendation": f"Cohort demonstrated strong mastery ({mean_score}% average). Consider introducing advanced comparative East African case study counter-arguments in the next module."
        })

    kb = load_course_knowledge_base()
    return {
        "generated_at": datetime.now().isoformat(),
        "cohort_size": n,
        "mean_score": mean_score,
        "satisfactory_pass_rate_pct": round((pass_count / n) * 100.0, 1),
        "distinction_rate_pct": round((distinction_count / n) * 100.0, 1),
        "intervention_alerts_count": len(intervention_alerts),
        "intervention_alerts": intervention_alerts,
        "pillar_diagnostics": pillar_diagnostics,
        "pedagogical_recommendations": pedagogical_recommendations,
        "staged_student_concepts": kb.get("staged_student_concepts", []),
        "approved_student_concepts": kb.get("lecturer_approved_student_concepts", [])
    }


def format_intervention_report_markdown(report: Dict[str, Any]) -> str:
    """Renders an executive-ready Markdown Intervention & Pedagogical Briefing for the Lecturer."""
    lines = [
        "# 🚨 USIU-Africa Executive Lecturer Intervention & Pedagogical Report",
        f"- **Generated At:** `{report.get('generated_at', '')}`",
        f"- **Cohort Size:** `{report.get('cohort_size', 0)}` students",
        f"- **Class Mean Score:** `{report.get('mean_score', 0.0)} / 100`",
        f"- **Satisfactory Pass Rate (>= 70% C):** `{report.get('satisfactory_pass_rate_pct', 0.0)}%`",
        f"- **Distinction Rate (>= 90% A):** `{report.get('distinction_rate_pct', 0.0)}%`",
        "",
        "---",
        "",
        "## 1. Priority Attention & Lecturer Intervention Queue",
        ""
    ]
    alerts = report.get("intervention_alerts", [])
    if not alerts:
        lines.append("✅ No critical anomalies or at-risk submissions detected.")
    else:
        lines.append("| Priority | Category | Student | Mark | Trigger | Recommended Lecturer Action |")
        lines.append("|:---|:---|:---|:---:|:---|:---|")
        for al in alerts:
            lines.append(
                f"| **{al['priority']}** | `{al['category']}` | **{al['student_name']}** (`{al['student_id']}`) | "
                f"**{al['score']}% ({al['letter_grade']})** | {al['trigger']} | {al['recommended_action']} |"
            )

    lines.extend([
        "",
        "---",
        "",
        "## 2. Pillar-by-Pillar Cohort Diagnostics",
        "",
        "| Rubric Pillar | Weight | Cohort Mastery (%) | Status |",
        "|:---|:---:|:---:|:---:|"
    ])
    for p in report.get("pillar_diagnostics", []):
        lines.append(f"| {p['criterion']} | {p['weight']} pts | **{p['cohort_average_pct']}%** | `{p['status']}` |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Pedagogical Recommendations & Teaching Suggestions",
        ""
    ])
    for rec in report.get("pedagogical_recommendations", []):
        lines.append(f"- **{rec['target_pillar']} ({rec['cohort_average_pct']}%):** {rec['recommendation']}")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Smart Cohort-Derived Concepts (Zero-Trust Anti-Poisoning Gate)",
        ""
    ])
    for sc in report.get("staged_student_concepts", []):
        lines.append(
            f"- **`{sc['concept']}`** (Found in {sc['peer_frequency']} A/A- paper(s): {', '.join(sc['supporting_high_performers'])}) — *{sc['safety_verification']}*"
        )

    return "\n".join(lines)


def recalculate_with_overrides(
    assessment: Dict[str, Any],
    criterion_overrides: Dict[str, float],
    custom_feedback: Optional[str] = None
) -> Dict[str, Any]:
    """
    Applies Lecturer human-in-the-loop score overrides to individual rubric criteria
    and recalculates the total score, USIU Letter Grade, GPA quality points, and receipt.
    """
    total_score = 0.0
    for crit in assessment.get("criteria_breakdown", []):
        cid = crit.get("id") or crit.get("criterion")
        if cid in criterion_overrides:
            new_val = max(0.0, min(float(crit["weight"]), float(criterion_overrides[cid])))
            crit["earned"] = round(new_val, 1)
        elif crit.get("criterion") in criterion_overrides:
            new_val = max(0.0, min(float(crit["weight"]), float(criterion_overrides[crit["criterion"]])))
            crit["earned"] = round(new_val, 1)
        total_score += float(crit["earned"])

    total_score = round(min(100.0, total_score), 1)
    letter, gpa, summary_desc = score_to_usiu_letter(total_score)

    assessment["total_score"] = total_score
    assessment["letter_grade"] = letter
    assessment["gpa_points"] = gpa
    assessment["standing"] = summary_desc
    assessment["overridden_by_lecturer"] = True

    if custom_feedback is not None and custom_feedback.strip():
        assessment["feedback_for_blackboard"] = custom_feedback.strip()
    else:
        strengths = [c["criterion"] for c in assessment["criteria_breakdown"] if (c["earned"] / c["weight"]) >= 0.8]
        improvements = [c["criterion"] for c in assessment["criteria_breakdown"] if (c["earned"] / c["weight"]) < 0.8]
        assessment["feedback_for_blackboard"] = (
            f"USIU-Africa Official Assessment Receipt | "
            f"Student: {assessment['student_name']} ({assessment['student_id']}) | "
            f"Score: {total_score}/100 ({letter} | GPA {gpa}) | "
            f"Overall Standing: {summary_desc}. "
            f"Strengths: {', '.join(strengths) if strengths else 'Basic topic coverage'}. "
            f"Areas to Strengthen: {', '.join(improvements) if improvements else 'Maintain strong APA 7th empirical grounding'}."
        )
    return assessment


def format_blackboard_csv_string(results: List[Dict[str, Any]]) -> str:
    """Generates an RFC-4180 compliant Blackboard Grade Center offline upload CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
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
    return buf.getvalue()


class USIUBlackboardClient:
    """
    REST API Client for USIU-Africa Blackboard Learn (`/learn/api/public/v2`).
    Supports downloading student assignment attempts and posting grades + feedback
    directly to the lecturer's Blackboard Grade Center column.
    """

    def __init__(self, base_url: str = "https://blackboard.usiu.ac.ke", access_token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

    def fetch_assignment_attempts(self, course_id: str, column_id: str) -> list[dict]:
        url = f"{self.base_url}/learn/api/public/v2/courses/{course_id}/gradebook/columns/{column_id}/attempts"
        if not self.access_token:
            return []
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.access_token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("results", [])

    def post_grade_to_blackboard(self, course_id: str, column_id: str, user_id: str, score: float, feedback: str) -> dict:
        url = f"{self.base_url}/learn/api/public/v2/courses/{course_id}/gradebook/columns/{column_id}/users/{user_id}"
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
            return {"status": "POSTED_LIVE", "http_code": resp.status, "endpoint": f"PATCH {url}"}


def speak_aloud_windows(text: str):
    """Low-vision accessibility helper: reads the grading summary aloud using Windows SAPI."""
    safe_text = re.sub(r"['\"`\r\n]+", " ", text)
    ps_cmd = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.Rate = 0; "
        f"$s.Speak('{safe_text}')"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)


def main():
    parser = argparse.ArgumentParser(description="USIU Blackboard Accessible Lecturer Grading Suite")
    parser.add_argument("--submissions-dir", type=Path, default=DATA_DIR / "sample_submissions", help="Folder of student submissions")
    parser.add_argument("--rubric-id", type=str, default="standard_research_paper", help="Rubric ID from usiu_locked_rubrics.json")
    parser.add_argument("--out-csv", type=Path, default=DATA_DIR / "outputs" / "USIU_Blackboard_GradeCenter_Upload.csv", help="Blackboard Grade Center CSV")
    parser.add_argument("--out-json", type=Path, default=DATA_DIR / "outputs" / "USIU_Grading_Audit_Report.json", help="Detailed JSON audit report")
    parser.add_argument("--bb-url", type=str, default="https://blackboard.usiu.ac.ke", help="USIU Blackboard URL")
    parser.add_argument("--course-id", type=str, default="_10482_1", help="Blackboard Course ID")
    parser.add_argument("--column-id", type=str, default="_58291_1", help="Blackboard Gradebook Column ID")
    parser.add_argument("--speak", action="store_true", help="Read results aloud for low-vision accessibility")
    args = parser.parse_args()

    rubric = get_rubric_by_id(args.rubric_id)
    bb_client = USIUBlackboardClient(args.bb_url)
    files = sorted([
        f for f in args.submissions_dir.glob("*")
        if f.suffix.lower() in {".txt", ".md", ".docx", ".pdf", ".zip"}
    ])

    results = []
    assessments_with_texts = []
    print("==========================================================================")
    print("🎓 USIU-AFRICA ACCESSIBLE LECTURER GRADING & BLACKBOARD SYNC ENGINE v2.3")
    print(f"📋 ACTIVE LOCKED RUBRIC: {rubric.get('title')}")
    print("==========================================================================\n")

    for f in files:
        if f.suffix.lower() == ".zip":
            zip_results = ingest_zip_bytes(f.read_bytes(), rubric)
            for eval_res in zip_results:
                bb_sync = bb_client.post_grade_to_blackboard(
                    args.course_id, args.column_id, eval_res["student_id"], eval_res["total_score"], eval_res["feedback_for_blackboard"]
                )
                eval_res["blackboard_sync"] = bb_sync
                results.append(eval_res)
            continue

        student_id, student_name = parse_student_identity_from_filename(f.name)
        text = extract_submission_text(f)
        eval_res = evaluate_submission_deterministic(student_id, student_name, text, rubric, source_filename=f.name)
        bb_sync = bb_client.post_grade_to_blackboard(
            args.course_id, args.column_id, student_id, eval_res["total_score"], eval_res["feedback_for_blackboard"]
        )
        eval_res["blackboard_sync"] = bb_sync
        results.append(eval_res)
        assessments_with_texts.append((eval_res, text))

        print(f"👤 STUDENT: {student_name} (ID: {student_id}) [{f.name}]")
        print(f"   • FINAL MARK:  {eval_res['total_score']}/100  [{eval_res['letter_grade']} | GPA {eval_res['gpa_points']}]")
        print(f"   • STANDING:    {eval_res['standing']}")
        for c in eval_res["criteria_breakdown"]:
            print(f"     - {c['criterion']}: {c['earned']}/{c['weight']} pts")
        print(f"   • BLACKBOARD:  {bb_sync['status']} -> {bb_sync['endpoint']}\n")

        if args.speak:
            speak_aloud_windows(
                f"Student {student_name}. Score {eval_res['total_score']} out of 100. Grade {eval_res['letter_grade']}. {eval_res['standing']}."
            )

    # Smart anti-poisoning student cohort concept learning + Executive Intervention Report
    extract_verified_student_cohort_concepts(assessments_with_texts)
    intervention_report = generate_cohort_intervention_report(results)
    report_md = format_intervention_report_markdown(intervention_report)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)

    report_md_path = args.out_json.parent / "USIU_Intervention_And_Recommendations_Report.md"
    report_json_path = args.out_json.parent / "USIU_Intervention_Report.json"

    args.out_csv.write_text(format_blackboard_csv_string(results), encoding="utf-8")
    args.out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    report_md_path.write_text(report_md, encoding="utf-8")
    report_json_path.write_text(json.dumps(intervention_report, indent=2), encoding="utf-8")

    print(f"✅ [EXPORTED] Blackboard Grade Center CSV: {args.out_csv}")
    print(f"✅ [EXPORTED] Full Rubric Audit JSON:      {args.out_json}")
    print(f"🚨 [EXPORTED] Lecturer Intervention MD:    {report_md_path} ({intervention_report['intervention_alerts_count']} alerts)")


if __name__ == "__main__":
    main()
