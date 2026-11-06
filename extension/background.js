/**
 * background.js — Manifest V3 Service Worker for USIU-Africa Accessible Grader Extension
 * Handles cross-origin messaging between the Blackboard content script and the local Python/Java grading server.
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("[USIU ACCESSIBLE GRADER] Manifest V3 Extension Installed.");
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "GRADE_SUBMISSION_LOCAL") {
    fetch("http://127.0.0.1:8085/api/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rubric_id: msg.rubric_id || "standard_research_paper",
        files: [
          {
            filename: msg.filename || `${msg.student_id || "665421"}_${msg.student_name || "Student"}.txt`,
            student_id: msg.student_id,
            student_name: msg.student_name,
            text: msg.text || ""
          }
        ]
      })
    })
      .then((r) => r.json())
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true; // Async response
  }
});
