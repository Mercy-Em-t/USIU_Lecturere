# Complete Algorithmic Pseudocode & System Documentation
## USIU-Africa Accessible Lecturer Assessment & Blackboard Grader Suite (`v2.0`)

This document provides complete, formal algorithmic pseudocode and architectural specifications for every program file in the repository.

---

## 1. [`src/usiu_blackboard_grader.py`](../src/usiu_blackboard_grader.py) — Multi-Format Ingestion & Deterministic Rubric Engine

### 1.1 Algorithm: `PARSE_STUDENT_IDENTITY_FROM_FILENAME(filename)`
```text
ALGORITHM PARSE_STUDENT_IDENTITY_FROM_FILENAME
INPUT: filename (String)
OUTPUT: (student_id, student_name) (Tuple of Strings)

BEGIN
    stem <- REMOVE_EXTENSION(filename)

    // Case 1: Official Blackboard Bulk Download Format
    // Example: "TermPaper_665421_attempt_2026-11-06-10-15-00_Amina_Wanjiku_Final"
    IF stem MATCHES REGEX "^.+?_([A-Za-z0-9\-]+)_attempt_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}_(.+)$" THEN
        student_id <- CAPTURE_GROUP(1)
        raw_name   <- REPLACE_UNDERSCORES_AND_HYPHENS(CAPTURE_GROUP(2), " ")
        clean_name <- STRIP_KEYWORDS(raw_name, ["final", "essay", "paper", "assignment", "submission", "draft"])
        RETURN (student_id, IF LENGTH(clean_name) >= 3 THEN clean_name ELSE "Student " + student_id)
    END IF

    // Case 2: Leading USIU Student ID Prefix
    // Example: "665421_Amina_Wanjiku"
    IF stem MATCHES REGEX "^(\d{5,8})[_\-\s]+(.+)$" THEN
        RETURN (CAPTURE_GROUP(1), REPLACE_UNDERSCORES_AND_HYPHENS(CAPTURE_GROUP(2), " "))
    END IF

    // Case 3: Fallback
    RETURN ("669999", REPLACE_UNDERSCORES(stem, " "))
END
```

### 1.2 Algorithm: `EXTRACT_SUBMISSION_BYTES(filename, raw_bytes)`
```text
ALGORITHM EXTRACT_SUBMISSION_BYTES
INPUT: filename (String), raw_bytes (ByteArray)
OUTPUT: extracted_text (UTF-8 String)

BEGIN
    ext <- LOWERCASE(GET_EXTENSION(filename))

    IF ext IN {".txt", ".md", ".csv", ".html"} THEN
        RETURN DECODE_UTF8(raw_bytes)

    ELSE IF ext == ".docx" THEN
        OPEN raw_bytes AS ZipArchive zf
        IF "word/document.xml" NOT IN zf THEN RETURN ""
        xml_tree <- PARSE_XML(zf.READ("word/document.xml"))
        paragraphs <- EMPTY_LIST
        FOR EACH node IN xml_tree WHERE node.tag ENDS_WITH "}p" DO
            p_text <- CONCATENATE(t.text FOR t IN node WHERE t.tag ENDS_WITH "}t")
            IF TRIM(p_text) IS NOT EMPTY THEN
                APPEND TRIM(p_text) TO paragraphs
            END IF
        END FOR
        RETURN JOIN(paragraphs, "\n")

    ELSE IF ext == ".pdf" THEN
        // Stage 1: Try pypdf / PyPDF2 if installed
        IF MODULE_AVAILABLE("pypdf") THEN
            text <- EXTRACT_VIA_PYPDF(raw_bytes)
            IF LENGTH(text) > 20 THEN RETURN text
        END IF

        // Stage 2: Pure-Python FlateDecode Zlib Stream + Literal String Extractor
        chunks <- EMPTY_LIST
        FOR EACH stream_block IN FIND_ALL_PDF_STREAMS(raw_bytes) DO
            TRY
                decompressed <- ZLIB_DECOMPRESS(stream_block)
                APPEND EXTRACT_PARENTHESIZED_STRINGS(decompressed) TO chunks
            CATCH ZlibError
                CONTINUE
            END TRY
        END FOR
        APPEND EXTRACT_PARENTHESIZED_STRINGS(raw_bytes) TO chunks
        RETURN JOIN(chunks, " ")
    END IF
END
```

### 1.3 Algorithm: `EVALUATE_SUBMISSION_DETERMINISTIC(student_id, student_name, text, rubric)`
```text
ALGORITHM EVALUATE_SUBMISSION_DETERMINISTIC
INPUT:
    student_id   (String)
    student_name (String)
    text         (String)
    rubric       (Dictionary with 4 Weighted Criteria summing to 100)
OUTPUT:
    assessment   (Structured Assessment Dictionary)

BEGIN
    words          <- TOKENIZE_LOWERCASE_WORDS(text)
    word_count     <- LENGTH(words)
    sentences      <- SPLIT_SENTENCES(text) WHERE LENGTH(sentence) > 25
    apa_citations  <- FIND_ALL_REGEX(text, "\([A-Za-z\s,&.\-]+,?\s*(?:19|20)\d{2}[a-z]?\)")
    citation_count <- LENGTH(apa_citations)

    total_score       <- 0.0
    criterion_results <- EMPTY_LIST

    FOR EACH crit IN rubric.criteria DO
        weight   <- crit.weight
        kw_hits  <- COUNT(kw IN crit.keywords WHERE kw IN words OR kw IN LOWERCASE(text))
        kw_ratio <- MIN(1.0, kw_hits / MAX(1.0, LENGTH(crit.keywords) * 0.45))

        length_factor <- MIN(1.0, word_count / 220.0)
        IF crit.id IN {"evidence_citations", "historical_empirical_sources", "financial_operational_evidence"} THEN
            cite_bonus <- MIN(0.15, citation_count * 0.05)
        ELSE
            cite_bonus <- 0.0
        END IF

        raw_ratio <- MIN(1.0, 0.45 + (0.45 * kw_ratio) + (0.10 * length_factor) + cite_bonus)
        IF word_count < 40 THEN
            raw_ratio <- raw_ratio * 0.55
        END IF

        earned      <- ROUND_TO_1_DECIMAL(weight * raw_ratio)
        total_score <- total_score + earned

        evidence_quote <- FIRST_SENTENCE_CONTAINING_ANY(sentences, crit.keywords)
                          OR FIRST_ELEMENT(sentences)
                          OR "No substantive sentence found."

        APPEND {
            id: crit.id,
            criterion: crit.name,
            weight: weight,
            earned: earned,
            evidence_quote: TRUNCATE(evidence_quote, 160)
        } TO criterion_results
    END FOR

    total_score <- ROUND_TO_1_DECIMAL(MIN(100.0, total_score))
    (letter_grade, gpa_points, standing) <- MAP_TO_USIU_SCALE(total_score)

    RETURN {
        student_id: student_id,
        student_name: student_name,
        word_count: word_count,
        citations_detected: citation_count,
        total_score: total_score,
        letter_grade: letter_grade,
        gpa_points: gpa_points,
        standing: standing,
        criteria_breakdown: criterion_results,
        feedback_for_blackboard: FORMAT_USIU_RECEIPT(student_name, student_id, total_score, letter_grade, gpa_points, standing)
    }
END
```

---

## 2. [`src/usiu_lecturer_server.py`](../src/usiu_lecturer_server.py) — Python 3 REST & SQLite 3NF Backend Server

```text
ALGORITHM USIU_PYTHON_REST_SERVER
INITIALIZATION:
    db <- INITIALIZE_SQLITE_3NF_SCHEMA("data/outputs/usiu_grading_store.sqlite3")
    IF db.assessments IS EMPTY THEN
        SEED_INITIAL_SUBMISSIONS("data/sample_submissions")
    END IF
    BIND HTTPServer ON ("127.0.0.1", 8085)

ON HTTP REQUEST (method, path, headers, body):
    IF method == "GET" AND path == "/" THEN
        SERVE_FILE("index.html")

    ELSE IF method == "GET" AND path == "/api/health" THEN
        RETURN JSON { status: "ONLINE", rubrics_available: KEYS(RUBRICS), submissions_count: COUNT(db) }

    ELSE IF method == "GET" AND path == "/api/submissions" THEN
        RETURN JSON { submissions: db.LIST_ASSESSMENTS() }

    ELSE IF method == "POST" AND path == "/api/ingest" THEN
        IF Content-Type CONTAINS "multipart/form-data" THEN
            (fields, files) <- PARSE_MULTIPART_FILES(headers, body)
        ELSE
            (fields, files) <- PARSE_JSON_BASE64_FILES(body)
        END IF

        rubric <- GET_RUBRIC_BY_ID(fields.rubric_id)
        FOR EACH (filename, file_bytes) IN files DO
            IF filename ENDS_WITH ".zip" THEN
                results <- INGEST_ZIP_BYTES(file_bytes, rubric)
                FOR EACH r IN results DO db.UPSERT_ASSESSMENT(r)
            ELSE
                (sid, sname) <- PARSE_STUDENT_IDENTITY_FROM_FILENAME(filename)
                text         <- EXTRACT_SUBMISSION_BYTES(filename, file_bytes)
                result       <- EVALUATE_SUBMISSION_DETERMINISTIC(sid, sname, text, rubric)
                db.UPSERT_ASSESSMENT(result)
            END IF
        END FOR
        WRITE_CSV_AND_JSON_EXPORTS(db.LIST_ASSESSMENTS())
        RETURN JSON { status: "INGESTED", submissions: db.LIST_ASSESSMENTS() }

    ELSE IF method == "POST" AND path == "/api/override" THEN
        payload  <- PARSE_JSON(body)
        existing <- db.GET_ASSESSMENT(payload.student_id)
        updated  <- RECALCULATE_WITH_OVERRIDES(existing, payload.criterion_overrides, payload.feedback_for_blackboard)
        db.UPSERT_ASSESSMENT(updated)
        WRITE_CSV_AND_JSON_EXPORTS(db.LIST_ASSESSMENTS())
        RETURN JSON { status: "UPDATED", assessment: updated }
    END IF
```

---

## 3. [`src/USIULecturerServer.java`](../src/USIULecturerServer.java) — Enterprise Java 21 Pure-JDK Server

```text
ALGORITHM USIU_JAVA21_ENTERPRISE_SERVER
BEGIN
    LOAD sample submissions from "data/sample_submissions"
    FOR EACH file IN sample_submissions DO
        (sid, sname) <- parseStudentIdentity(file.name)
        text         <- extractTextFromBytes(file.name, file.bytes)
        result       <- evaluateDeterministic(sid, sname, text, file.name)
        STORE.PUT(sid, result)
    END FOR

    IF "--cli-test" IN args THEN
        FOR EACH r IN STORE.VALUES() DO
            PRINT(r.studentName, r.studentId, r.totalScore, r.letterGrade, r.gpaPoints)
        END FOR
        EXIT(0)
    END IF

    START com.sun.net.httpserver.HttpServer ON 127.0.0.1:8086
    REGISTER "/api/health"      -> RETURN JSON health status
    REGISTER "/api/submissions" -> RETURN JSON array of STORE.VALUES()
END
```

---

## 4. [`index.html`](../index.html) & [`extension/content_script.js`](../extension/content_script.js) — Low-Vision UI & Chrome/Edge Extension

```text
ALGORITHM LOW_VISION_ACCESSIBLE_CLIENT_HUB
ON PAGE LOAD:
    RENDER high-contrast toolbar (100% / 135% / 175% zoom, Obsidian/Cream toggle, Read Aloud)
    PING http://127.0.0.1:8085/api/health
    IF ONLINE THEN
        FETCH cohort from /api/submissions
    ELSE
        USE built-in client-side rubric & JSZip ingestion engine
    END IF

ON DRAG_AND_DROP(fileList):
    IF backendOnline THEN
        POST multipart FormData(fileList) TO /api/ingest
    ELSE
        FOR EACH file IN fileList DO
            EXTRACT text via JSZip (.docx / .zip) or PDF stream decoder (.pdf) or UTF-8 (.txt)
            EVALUATE via evaluateSubmissionClientSide()
        END FOR
    END IF
    RENDER active student card & SPEAK grade aloud via window.speechSynthesis

ON KEYDOWN(event):
    SWITCH event.key:
        CASE "Space": SPEAK_CURRENT_STUDENT()
        CASE "N":     STEP_STUDENT(+1)
        CASE "P":     STEP_STUDENT(-1)
        CASE "1".."4": SPEAK_SINGLE_CRITERION(PARSE_INT(event.key) - 1)
        CASE "Alt+Z": CYCLE_ZOOM([20px, 25px, 30px])
        CASE "Alt+C": TOGGLE_HIGH_CONTRAST_THEME()
```
