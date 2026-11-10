# OmniSight — Automated Test Results

**Project:** OmniSight: Multimodal UI Self-Healing & RPA Agent
**Latest verified complete test date:** 10 November 2026
**Environment:** Python 3.12 virtual environment (`backend\.venv312`)
**Test framework:** pytest

## 1. Test command

Run from the repository root:

```powershell
.\backend\.venv312\Scripts\python.exe -m pytest tests -q
```

## 2. Latest verified complete test run — 10 November 2026

The complete automated test suite was executed using the Python 3.12 virtual environment.

| Result | Value |
|---|---:|
| Tests passed | **74** |
| Tests failed | **0** |
| Warnings | **6** |
| Execution time | **65.50 seconds** |
| Overall result | **PASS** |

The six warnings were non-fatal Pillow deprecation warnings associated with `Image.Image.getdata()` in `backend/main.py` at line 1113. They did not cause test failures. Review this usage before upgrading to a Pillow release that removes the deprecated API.

Passing automated tests validate the tested workflows in this local environment. They do not, by themselves, prove that every possible target website, browser configuration, or visual repair has been manually validated.

## 3. Historical complete test run — 5 November 2026

| Result | Value |
|---|---:|
| Tests passed | 74 |
| Tests failed | 0 |
| Warnings | 6 |
| Execution time | 60.58 seconds |
| Overall result | PASS |

The six warnings were non-fatal Pillow deprecation warnings associated with screenshot processing. The latest observed warning location in that run was `backend/main.py:1113`.

## 4. Historical complete test run — 29 October 2026

| Result | Value |
|---|---:|
| Tests passed | 69 |
| Tests failed | 0 |
| Warnings | 6 |
| Execution time | 64.73 seconds |
| Overall result | PASS |

This is a historical result and is not the latest test count.

## 5. Historical focused workflow tests — 31 October 2026

The following focused tests were recorded after Gemini Vision frontend integration:

- `test_omnisight_workflow.py`: 10 passed
- `test_demo_store.py`: 2 passed
- `test_compare_screenshots.py`: 11 passed (4 non-fatal Pillow deprecation warnings)
- **Total: 23 passed, 0 failed**

Additional endpoint validation was recorded for invalid paths and missing files. A live Gemini Vision request on 31 October 2026 was recorded as successful and identified two UI issues. This is historical evidence only; it does not establish current provider availability.

## 6. Interpretation and limitations

- The latest complete automated run is the 10 November 2026 result: **74 passed, 0 failed, 6 warnings, 65.50 seconds**.
- Historical test results are retained for traceability and must not be labelled as the latest result.
- Automated tests do not replace manual browser demonstration or visual review.
- Gemini Vision is an optional external integration. Recent live API attempts on 10 November 2026 returned provider errors (HTTP 503/502), so current live availability is unconfirmed. Do not claim a successful current live Gemini analysis without a fresh successful run.
- The Pillow warnings are non-fatal but should be addressed in a future maintenance change.

---

**Record status:** Updated to reflect the latest verified complete test output supplied for 10 November 2026.
