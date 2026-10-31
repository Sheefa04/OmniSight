# OmniSight — Gemini Vision Audit Integration

**Feature completed:** 31 October 2026  
**Environment:** Python 3.12 (`backend\.venv312`), Gemini API (`gemini-3.8-flash`)

---

## Overview

OmniSight now includes a **Gemini Vision Audit** panel on the dashboard. After running a website inspection, the user can click **Run Vision Audit** to submit the captured screenshot to the Gemini Vision API. Gemini analyzes the visible screenshot and returns a structured report of detected UI issues. No repair is applied automatically.

---

## How It Works

```
User clicks "Run Vision Audit"
         │
         ▼
Frontend extracts screenshot filename from <img src>
         │
         ▼
POST /vision-audit  {screenshot_filename: "inspection_...png"}
         │
         ▼
Backend: validates filename (path-traversal check)
         │
         ▼
Backend: loads screenshot from backend/screenshots/ with Pillow
         │
         ▼
Backend: sends image + prompt to Gemini Vision API (gemini-3.8-flash)
         │
         ▼
Backend: validates JSON response structure (summary + issues[])
         │
         ▼
Response: {status, audit: {summary, issues[]}, model, repair_applied: false}
         │
         ▼
Frontend: renders summary + per-issue cards (title, severity, location,
          description, suggested improvement)
```

---

## API Endpoint

### `POST /vision-audit`

**Request body:**
```json
{
  "screenshot_filename": "inspection_375x812_183eb0ff2c.png"
}
```

**Successful response (HTTP 200):**
```json
{
  "status": "success",
  "screenshot": "inspection_375x812_183eb0ff2c.png",
  "audit": {
    "summary": "The store UI has visible text clipping on a product action button and inconsistent vertical alignment of CTA buttons within product cards.",
    "issues": [
      {
        "title": "Truncated button label in Everyday Backpack card",
        "location": "Featured products grid, second row, left card ('Everyday Backpack')",
        "description": "The button label is clipped abruptly as 'Add to Cart …' due to insufficient width or fixed container bounds without text overflow handling.",
        "severity": "medium",
        "suggestion": "Allow the button text to wrap cleanly or adjust button sizing, padding, and font size so that the full label is visible."
      },
      {
        "title": "Inconsistent vertical alignment of card action buttons",
        "location": "Featured products grid (e.g., 'Smart Watch', 'Running Shoes', 'Everyday Handbag')",
        "description": "Buttons are placed immediately following the price rather than being anchored to the bottom of each card, resulting in misaligned button rows.",
        "severity": "low",
        "suggestion": "Apply flexbox layout to each card content container ('display: flex; flex-direction: column;') and set the button's margin-top to 'auto'."
      }
    ]
  },
  "model": "gemini-3.8-flash",
  "detection_method": "Gemini Vision screenshot analysis",
  "repair_applied": false
}
```

**Error responses:**
| Condition | HTTP Status | Detail |
|---|---|---|
| Missing / unconfigured API key | 503 | `Gemini API key is not configured.` |
| Path traversal attempt | 400 | `Invalid screenshot identifier.` |
| Subdirectory in filename | 400 | `Invalid screenshot identifier.` |
| Screenshot file not found | 404 | `Screenshot not found.` |
| Gemini returns malformed JSON | 502 | `Gemini returned an invalid audit response.` |
| Gemini returns wrong structure | 502 | `Gemini returned an unexpected audit structure.` |
| Any other exception | 502 | `Vision audit failed. Check the backend terminal.` |

---

## Security Validation

The `_ensure_within_screenshot_dir()` function in `backend/main.py` applies three layers of validation before reading any file:

1. **Non-empty check** — rejects empty strings.
2. **Basename check** — `Path(filename).name != filename` rejects any path containing `/` or `\`.
3. **Resolved-path check** — after resolving the full path, verifies `path.parent == SCREENSHOT_DIR.resolve()` to prevent any symlink-based traversal.

---

## Frontend Integration

The Gemini Vision Audit panel is embedded inside `frontend/dashboard.html`. The panel HTML exists at lines 651–665. The JavaScript function `runVisionAudit()` and its click event listener are added to the **inline `<script>` block** at the bottom of the file (lines 1392–1512).

### Why `app.js` was not modified

`app.js` is not loaded by `dashboard.html` (no `<script src="app.js">` tag exists in the file). The dashboard runs entirely from an inline script. The `runVisionAudit` function and event listener were therefore added directly to the inline script to match the dashboard's actual script architecture.

### Screenshot visibility check

The guard uses `getComputedStyle(screenshotImg).display !== 'none'` rather than `.hidden`, because the image element uses `style="display:none"` (a CSS property), not the `hidden` HTML attribute. This ensures the guard correctly detects whether a screenshot has been loaded and is currently visible.

### Safe DOM rendering

All Gemini-generated text is inserted using `textContent`. No AI-generated content is inserted via `innerHTML`, preventing XSS from untrusted model output.

---

## Actual Test Results — 31 October 2026

### Backend validation tests (manual, run against live backend)

| Test | Result |
|---|---|
| `/health` returns `{status: healthy}` | ✅ PASS |
| Path traversal `../backend/.env` rejected (HTTP 400) | ✅ PASS |
| Non-existent file rejected (HTTP 404) | ✅ PASS |
| Subdirectory path `subdir/file.png` rejected (HTTP 400) | ✅ PASS |
| Live Gemini audit with real inspection screenshot | ✅ PASS |
| `repair_applied: false` in response | ✅ PASS |

### Automated test suite

```
tests/test_omnisight_workflow.py  — 10 passed
tests/test_demo_store.py          —  2 passed
tests/test_compare_screenshots.py — 11 passed
test_viewport_phase3.py           — (skipped — needs running server, run via workflow tests)

Total: 23 passed, 0 failed
```

---

## Actual Gemini Vision Finding (31 October 2026)

Screenshot used: `inspection_375x812_183eb0ff2c.png` (ShopHub mobile, 375×812)

**Gemini summary:**
> The store UI has visible text clipping on a product action button and inconsistent vertical alignment of CTA buttons within product cards.

**Issue 1 (medium):** Truncated button label in Everyday Backpack card  
- Location: Featured products grid, second row, left card  
- Description: Button label clipped as "Add to Cart 🛒 Sp…" due to insufficient width  
- Suggestion: Allow button text to wrap or resize the button

**Issue 2 (low):** Inconsistent vertical alignment of card action buttons  
- Location: Product cards throughout the grid  
- Description: Buttons follow price directly instead of anchoring to card bottom  
- Suggestion: Use `display:flex; flex-direction:column` + `margin-top:auto` on button

---

## Human Approval Gate

**No suggested repair is applied automatically.** The `repair_applied: false` field is always present in the response. Gemini findings are displayed as read-only informational cards. The user must explicitly click **Approve & Repair UI** (a separate workflow) and that repair operates only in a browser session — the original website source files are never modified.

---

## Known Limitations

- The Gemini Vision model (`gemini-3.8-flash`) analyzes the screenshot as a static image. It cannot detect issues that only appear through interaction or animation.
- Gemini may occasionally interpret rendering artifacts or image compression as visual defects. All findings require human review.
- The Gemini API requires network access. If the API is unavailable or returns an error, a descriptive error message is shown on the dashboard and no result is cached or fabricated.
- The model name `gemini-3.8-flash` is fixed in `backend/main.py`. Update `GEMINI_MODEL` if a newer model is preferred.
