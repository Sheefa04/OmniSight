# OmniSight: Mid-Review Presentation & Viva Guide

---

## Part 1: Mid-Review Presentation Slides (13 Slides)

### Slide 1: Title & Project Details
- **Project Title**: OmniSight: Multimodal UI Self-Healing & RPA Agent
- **Subtitle**: Automated Visual Inspection, Heuristic Issue Detection, and Approved Browser Remediation
- **Student**: Sheefa J Pathan
- **Branch**: B.E. Artificial Intelligence & Data Science
- **Project Type**: Solo Internship Project
- **Key Technologies**: Python 3.12, FastAPI, Playwright, Chromium, Modern Vanilla JS/CSS

---

### Slide 2: Problem Statement
- **The Visual QA Gap**: Traditional automated tests (like Selenium or Cypress) check DOM elements and status codes, but miss visual layout breaks, overflowing text, and viewport misalignments.
- **Responsive Fragility**: Elements that render perfectly on Desktop (1366×768) often break on Mobile screens (375×812) due to fixed widths and unwrapped whitespace.
- **Slow Feedback Loop**: Visual bugs require manual reporting, device testing, reproducing, and code patching.
- **Safety Risk of Auto-Healing**: Fully autonomous AI bots modifying code directly can break production sites. Human approval is critical.

---

### Slide 3: Motivation & Objectives
- **Motivation**: Create an intelligent quality agent that doesn't just log defects, but demonstrates an immediate visual solution with undeniable proof.
- **Core Objectives**:
  1. Inspect any web URL across desktop, tablet, and mobile breakpoints.
  2. Detect visual layout defects (oversized buttons, horizontal overflow) using DOM heuristics.
  3. Enforce a human-in-the-loop approval gate (`approved=true`).
  4. Apply temporary, non-destructive CSS repairs inside an active browser session.
  5. Provide dynamic Before/After visual comparison evidence.

---

### Slide 4: Proposed Solution: The OmniSight Loop
- **Closed-Loop Visual Engineering**:
  - **1. Ingest**: User provides website URL and chooses target viewport.
  - **2. Capture**: Headless Chromium navigates and captures a full-page baseline screenshot.
  - **3. Detect**: In-page heuristics analyze geometry, computed padding, and bounding boxes.
  - **4. Gate**: Dashboard displays the defect; remediation requires explicit user authorization.
  - **5. Repair**: Playwright injects safe scoped CSS rules into the browser session.
  - **6. Compare**: Post-repair screenshot is rendered side-by-side with the Before image.

---

### Slide 5: System Architecture
```text
[ User / Dashboard UI ] ──(REST API)──> [ FastAPI Backend ]
                                                │
                          ┌─────────────────────┴─────────────────────┐
                          ▼                                           ▼
                 [ Playwright Engine ]                      [ Static Screenshot ]
                          │                                 [ Storage (/screenshots) ]
              ┌───────────┴───────────┐
              ▼                       ▼
     [ Target Web Page ]      [ Scoped CSS Fix ]
     (ShopHub Demo Store)     (max-width, wrap)
```

---

### Slide 6: System Workflow
1. User enters `http://127.0.0.1:8000/frontend/store.html` and selects `Mobile (375 × 812)`.
2. Frontend calls `POST /inspect-browser`.
3. Backend runs Chromium, takes baseline screenshot, saves it to `backend/screenshots/inspection_*.png`.
4. Frontend calls `POST /detect-issues`.
5. DOM heuristics detect `oversized-button` with unwrapped text.
6. User reviews the issue and clicks **Approve & Repair UI**.
7. Frontend sends `POST /repair-ui` with `approved: true`.
8. Playwright injects scoped CSS rules, takes screenshot, and returns URL.
9. Dashboard displays side-by-side Before/After comparison.

---

### Slide 7: Technology Stack
- **Backend API**: FastAPI (Python 3.12) with asynchronous request handlers.
- **Event Loop**: Windows Proactor Event Loop for robust Playwright subprocess management.
- **Validation**: Pydantic v2 for strict URL and schema validation.
- **Browser Automation**: Playwright Python API (Headless Chromium).
- **Frontend**: Vanilla HTML5, Custom CSS Design System (Glassmorphic cards, CSS Grid), Vanilla ES6 JavaScript (Fetch API).
- **Test Automation**: Playwright Sync API & Python HTTP test suite.

---

### Slide 8: Current Implementation Status
- [x] FastAPI server running with health monitoring (`/health`).
- [x] Headless browser inspection with dynamic screenshot serving (`/inspect-browser`).
- [x] DOM-based UI issue detector (`/detect-issues`).
- [x] Built-in ShopHub responsive store (`frontend/store.html`) with intentional defect.
- [x] Approved repair flow requiring `approved=true` (`/repair-ui`).
- [x] Dynamic Before/After comparison with cache-busting timestamps (`?t=...`).
- [x] Clean error handling eliminating `[object Object]` crashes.
- [x] Responsive viewports tested: Desktop (1366×768), Tablet (768×1024), Mobile (375×812 & 390×844).

---

### Slide 9: Demo Screenshots & Visual Evidence
- **Initial Dashboard**: Clean workspace ready for URL and breakpoint input.
- **Mobile Inspection**: Displays the baseline ShopHub store on iPhone viewport (375×812).
- **Issue Detection Panel**: Flags 1 issue: `oversized-button` on `button.broken-button`.
- **Approved Repair State**: Green status indicator:
  > `✓ Temporary CSS repair applied to the demo button. (Note: Temporary session repair; target website files were not modified.)`
- **Before/After Comparison**: Side-by-side view showing the button before (unwrapped) and after (properly wrapped and constrained).

---

### Slide 10: Testing & Verification Results
- **Automated Test Suite**: `tests/test_omnisight_workflow.py`
  - Health check: **PASS** (HTTP 200, healthy)
  - Safety rejection: **PASS** (`approved=false` rejected with HTTP 400)
  - URL validation: **PASS** (Invalid URLs rejected with HTTP 422)
  - Non-broken page handling: **PASS** (`https://example.com` reports `not_applied` truthfully)
  - Multi-viewport tests: **PASS** (Desktop 1366×768, Tablet 768×1024, Mobile 375×812 & 390×844)
  - 7 evidence screenshots saved to `screenshots/evidence/`.

---

### Slide 11: Known Limitations & Current Challenges
- **Session-Level Repairs**: Repairs exist inside the active Playwright browser session for visual verification; original source files are intentionally not modified.
- **Heuristic Detection**: Visual detection is currently based on computed styles and DOM geometry rather than multimodal neural vision models.
- **Network Access**: Target websites must be reachable over standard HTTP/HTTPS protocols.

---

### Slide 12: Remaining Work & Project Timeline
- **Milestone 1 (Weeks 1–2 Post-Review)**: Integrate Vision-Language Model (Gemini Vision API) for semantic visual evaluation.
- **Milestone 2 (Weeks 3–4 Post-Review)**: Automated post-repair verification agent to confirm zero remaining layout errors.
- **Milestone 3 (Weeks 5–6 Post-Review)**: Automated Git patch / PR generator for exporting approved CSS fixes.
- **Milestone 4 (Week 7 Post-Review)**: Downloadable PDF/HTML audit report generation.
- **Milestone 5 (Week 8 Post-Review)**: Final project documentation, presentation video, and submission package.

---

### Slide 13: Conclusion
- OmniSight demonstrates that UI visual defects can be caught and temporarily self-healed in a controlled, safe environment.
- The human-in-the-loop design guarantees safety while eliminating manual device reproduction effort.
- The mid-review prototype is fully functional, rigorously tested, and backed by verifiable visual evidence.

---

## Part 2: 3–5 Minute Demonstration Script

### Timing Breakdown:
- **0:00 - 0:45**: Introduction & Problem Context
- **0:45 - 1:45**: Live Inspection & Issue Detection
- **1:45 - 2:45**: Human Review & Approved Repair Execution
- **2:45 - 3:30**: Dynamic Before/After Verification & Safety Explanation
- **3:30 - 4:00**: Q&A Wrap-Up

### Word-for-Word Script:

> **[0:00 - 0:45] Introduction**:
> "Good morning, respected evaluators. I am Sheefa Pathan, and I am presenting **OmniSight: Multimodal UI Self-Healing and RPA Agent**.
> In modern web engineering, responsive websites frequently suffer from visual layout regressions. For example, a button styled for desktop displays can extend past screen boundaries or fail to wrap text when viewed on a mobile device. Functional testing tools like Selenium often pass these tests because the button exists in the DOM, even though users see a broken layout.
> OmniSight provides an automated loop to inspect websites across viewports, detect visual flaws using computed style heuristics, and safely apply an approved, session-level repair."

> **[0:45 - 1:45] Inspection & Issue Detection**:
> *(Action: Open dashboard in browser `http://127.0.0.1:8000/frontend/dashboard.html`)*
> "Here is the OmniSight dashboard. You can see the backend status indicator in the top right confirms our FastAPI server is live and connected.
> Under 'Demo website', I will select our sample e-commerce site, **ShopHub**. Notice the URL automatically populates.
> Now I will select the **Mobile (375 × 812)** viewport and click **Start Inspection**.
> In the background, Playwright launches a headless Chromium instance, loads the page, and captures a full-page baseline screenshot.
> As you can see, the inspection screenshot immediately appears in our evidence card, and our issue detection engine has automatically detected **1 issue**: an `oversized-button` on `button.broken-button` caused by fixed width and unwrapped text."

> **[1:45 - 2:45] Approved Repair**:
> *(Action: Point to the UI Repair card)*
> "OmniSight follows a strict **human-in-the-loop** safety model. The system does not tamper with code autonomously. It requires explicit user approval.
> I will now click **Approve & Repair UI**.
> The backend receives an authorized request with `approved=true`. Playwright injects scoped, non-destructive CSS rules—applying `max-width: 100%` and `white-space: normal`—within the browser session, captures the repaired screen, and returns the result."

> **[2:45 - 3:30] Before / After Comparison & Safety**:
> *(Action: Scroll down to the Before / After Comparison card)*
> "Notice the status indicator has turned green:
> *'✓ Temporary CSS repair applied to the demo button.'*
> And here in the **Before / After Comparison** section, both images have dynamically updated:
> On the left, in the Before state, the button text is unwrapped and distorted.
> On the right, in the After state, the button fits neatly within the card, with text properly wrapped.
> Importantly, this repair exists inside the active browser session as proof—the original files on the server were not modified, guaranteeing safety."

> **[3:30 - 4:00] Conclusion**:
> "All endpoints, viewport configurations, and safety constraints have been automated and tested with 100% passing results.
> Thank you, and I am now ready for your questions."

---

## Part 3: Module-by-Module Technical Explanations

1. **FastAPI Backend (`backend/main.py`)**:
   - Manages asynchronous API routing.
   - Enforces Pydantic schema validation for incoming URLs and approval flags.
   - Serves generated screenshots statically via `/screenshots`.
   - Uses `WindowsProactorEventLoopPolicy` to ensure reliable Playwright subprocess handling on Windows.

2. **Browser Automation Engine (`Playwright Chromium`)**:
   - Controls headless Chromium sessions.
   - Configures exact viewport dimensions (e.g. 1366×768, 375×812).
   - Extracts page titles, HTTP response status codes, and captures full-page PNG screenshots.

3. **DOM & Style Heuristic Detector (`/detect-issues`)**:
   - Executes an in-page JavaScript evaluation analyzing all visible elements.
   - Compares bounding box client rects with `window.innerWidth`.
   - Compares document `scrollWidth` with `window.innerWidth` to catch horizontal page overflow.
   - Identifies known buggy button selectors with unwrapped text.

4. **Temporary CSS Injection Engine (`/repair-ui`)**:
   - Verifies the `approved=true` security check.
   - Injects a scoped `<style id="omnisight-demo-repair">` element into the DOM head.
   - Captures the repaired state without altering source files.

5. **Dashboard Frontend (`frontend/dashboard.html`)**:
   - Built with semantic HTML5 and vanilla CSS design tokens.
   - Features `formatApiError()` to parse FastAPI validation errors cleanly without `[object Object]` crashes.
   - Uses query-string cache-busters (`?t=timestamp`) to guarantee real-time screenshot refresh.

---

## Part 4: Top 15 Viva Questions & Beginner-Friendly Answers

### Q1: What is OmniSight in simple terms?
**Answer**: OmniSight is an automated website inspection and UI repair tool. It opens websites in a headless browser, spots layout bugs (like buttons overflowing on mobile screens), and lets the user review and approve a temporary CSS fix that is visually demonstrated side-by-side.

### Q2: Why did you use FastAPI instead of Flask or Django?
**Answer**: FastAPI natively supports Python `async/await` syntax, which is required to communicate seamlessly with Playwright's asynchronous browser API. It also provides automatic Swagger documentation and fast Pydantic data validation.

### Q3: Why did you choose Playwright over Selenium?
**Answer**: Playwright has built-in asynchronous support, automatically waits for network idle and DOM readiness, handles responsive viewports natively, and is significantly faster and more reliable than Selenium.

### Q4: Does the repair permanently change the website files?
**Answer**: No. The repair is applied as a scoped `<style>` injection inside the active Playwright browser session to capture visual evidence. It intentionally does not modify original website files to prevent unintended code regressions.

### Q5: What was the `Error: [object Object]` bug you fixed, and why did it happen?
**Answer**: When FastAPI returns a validation error (HTTP 422), it sends a JSON object containing a `detail` array. In JavaScript, passing an object or array to `new Error(...)` converts it via `toString()`, which produces `"[object Object]"`. We solved this by creating `formatApiError()` to unpack the array into clean, human-readable text.

### Q6: How does the system detect visual issues?
**Answer**: The backend runs an in-page script that checks element dimensions using `getBoundingClientRect()` and compares them against `window.innerWidth`. It also checks if `document.documentElement.scrollWidth > window.innerWidth` (horizontal page spill) and flags unwrapped elements.

### Q7: What viewports have you tested?
**Answer**: We tested:
- Desktop: 1366 × 768
- Tablet: 768 × 1024
- Mobile: 375 × 812 (iPhone standard) and 390 × 844 (modern iPhone)

### Q8: What prevents cached screenshots from showing in the dashboard?
**Answer**: We append a dynamic timestamp parameter to the image URL (`?t=` + `Date.now()`). This forces the browser to fetch the freshly generated image from the server instead of reading from local cache.

### Q9: Why is there an explicit `approved=true` requirement?
**Answer**: In robotic process automation and AI agents, safety is paramount. An agent should never apply visual modifications without human consent. Our API enforces this by rejecting any repair request with HTTP 400 if `approved` is not `true`.

### Q10: How do you handle Windows event loop issues with Playwright?
**Answer**: On Windows, default event loops can fail when managing subprocesses. We configured `asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())` at the top of `main.py` so Playwright subprocesses launch reliably.

### Q11: What is the ShopHub demo store?
**Answer**: ShopHub (`frontend/store.html`) is a built-in, local responsive e-commerce demo site containing an intentional layout defect: an unwrapped, fixed-padding "Add to Cart" button that overflows on mobile viewports.

### Q12: Can OmniSight inspect external websites?
**Answer**: Yes, as long as the URL starts with `http://` or `https://` and is accessible over the internet or localhost.

### Q13: How is this different from traditional visual regression tools like Percy?
**Answer**: Tools like Percy only tell you that pixels changed compared to a baseline, but they cannot tell you why or fix it. OmniSight detects the geometric cause and provides an approved repair with visual Before/After proof.

### Q14: What are your planned post-mid-review enhancements?
**Answer**: Integrating a Multimodal Vision-Language Model (like Gemini Vision API) for semantic visual balance analysis, automated post-repair retesting, and generating downloadable PDF audit reports.

### Q15: How did you verify your project?
**Answer**: We wrote an end-to-end automated test suite (`tests/test_omnisight_workflow.py`) that tests API health, safety rejection (HTTP 400), invalid URL handling (HTTP 422), responsive viewports, and captures 7 evidence screenshots. All tests passed 100%.

---

## Part 5: Implementation Status Summary

| Module | Status | Description |
| :--- | :---: | :--- |
| **Backend API (`main.py`)** | Complete | FastAPI endpoints for health, inspection, issue detection, and repair. |
| **Browser Engine** | Complete | Playwright Chromium automation with custom viewports. |
| **Demo Website (`store.html`)** | Complete | Responsive e-commerce store with intentional button defect. |
| **Dashboard UI (`dashboard.html`)** | Complete | Interactive controls, dynamic Before/After view, error formatting. |
| **Bug Fix (`[object Object]`)** | Complete | Resolved via `formatApiError()` and robust state handling. |
| **Automated Test Suite** | Complete | All tests passing (`test_omnisight_workflow.py`). |
| **Evidence Documentation** | Complete | 7 high-resolution screenshots saved to `screenshots/evidence/`. |
| **Vision-Language Model (VLM)** | Post Mid-Review | Semantic visual reasoning. |
| **Downloadable PDF Reports** | Post Mid-Review | Exportable audit summaries. |
