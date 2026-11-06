/**
 * usiu_bb_browser_bridge.js — Live Logged-In Session Bridge for USIU Blackboard
 * Target Server: https://blackboard.usiu.ac.ke (Blackboard Learn v4001.4.0 rel.58+b22e012)
 *
 * WHY THIS WORKS WITHOUT IT ADMIN API KEYS:
 * When the lecturer is logged into `https://blackboard.usiu.ac.ke` in Chrome/Edge,
 * her browser holds an authenticated session cookie. This script runs directly
 * inside her logged-in tab (via Bookmarklet or Chrome Extension) to:
 *   1. List her active USIU courses (`/learn/api/public/v1/users/me/courses?expand=course`)
 *   2. List gradebook assignment columns (`/learn/api/public/v2/courses/{courseId}/gradebook/columns`)
 *   3. Pull student submission attempts (`/learn/api/public/v2/courses/{courseId}/gradebook/columns/{columnId}/attempts`)
 *   4. Post final grades & rubric feedback (`PATCH /learn/api/public/v2/courses/{courseId}/gradebook/columns/{columnId}/users/{userId}`)
 */

const USIUBlackboardSessionBridge = {
  baseUrl: "https://blackboard.usiu.ac.ke",

  /**
   * 1. Fetch all courses where the logged-in user is an Instructor / Grader
   */
  async getMyInstructorCourses() {
    const res = await fetch(`${this.baseUrl}/learn/api/public/v1/users/me/courses?expand=course`, {
      credentials: "include",
      headers: { "Accept": "application/json" }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Make sure you are logged into blackboard.usiu.ac.ke`);
    const data = await res.json();
    return (data.results || []).filter(
      (m) => m.courseRoleId === "Instructor" || m.courseRoleId === "TeachingAssistant" || m.courseRoleId === "Grader"
    );
  },

  /**
   * 2. Fetch all Gradebook Columns (Assignments/Exams) for a specific USIU Course
   */
  async getCourseGradebookColumns(courseId) {
    const res = await fetch(`${this.baseUrl}/learn/api/public/v2/courses/${courseId}/gradebook/columns`, {
      credentials: "include",
      headers: { "Accept": "application/json" }
    });
    if (!res.ok) throw new Error(`Failed to fetch gradebook columns: HTTP ${res.status}`);
    const data = await res.json();
    return data.results || [];
  },

  /**
   * 3. Fetch all Student Submission Attempts for a Gradebook Column
   */
  async getAssignmentAttempts(courseId, columnId) {
    const res = await fetch(
      `${this.baseUrl}/learn/api/public/v2/courses/${courseId}/gradebook/columns/${columnId}/attempts`,
      {
        credentials: "include",
        headers: { "Accept": "application/json" }
      }
    );
    if (!res.ok) throw new Error(`Failed to fetch attempts: HTTP ${res.status}`);
    const data = await res.json();
    return data.results || [];
  },

  /**
   * 4. Post a Student's Grade & Structured Rubric Feedback back to USIU Blackboard
   */
  async postStudentGrade(courseId, columnId, userId, score, feedbackText) {
    const res = await fetch(
      `${this.baseUrl}/learn/api/public/v2/courses/${courseId}/gradebook/columns/${columnId}/users/${userId}`,
      {
        method: "PATCH",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          score: Number(score),
          text: feedbackText,
          feedback: feedbackText
        })
      }
    );
    if (!res.ok) throw new Error(`Failed to post grade for user ${userId}: HTTP ${res.status}`);
    return await res.json();
  }
};

window.USIUBlackboardSessionBridge = USIUBlackboardSessionBridge;
console.log("[USIU BLACKBOARD BRIDGE] Ready on", USIUBlackboardSessionBridge.baseUrl);
