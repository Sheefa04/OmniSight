# OmniSight — Safety and Approval Workflow

## 1. Purpose

OmniSight is designed to inspect web interfaces and propose or apply scoped UI repairs. A human approval step helps prevent unintended changes from being applied automatically.

## 2. Repair Workflow

1. The user provides a target URL.
2. OmniSight inspects the page using browser automation.
3. The system identifies potential UI issues using DOM and computed-style heuristics.
4. The system prepares a repair proposal for review.
5. A repair is permitted only when explicit approval is supplied.
6. The page is checked again to evaluate the result.

The exact outcome depends on the target page, browser state, and repair proposal. Detection alone does not prove that a repair is necessary or successful.

## 3. Approval Gate

The repair workflow uses an explicit approval condition. The automated test suite includes a safety test for `approved=false`.

The intended safety behavior is that a repair must not be applied when approval has not been granted. The approval-false test should be kept in the regression suite.

## 4. Scope of Changes

The repair approach applies scoped CSS within the active browser session rather than editing the target website's original source files.

This limits the repair's scope and supports before-and-after inspection. Session-scoped changes should not be described as permanent production fixes unless a separate implementation process explicitly creates and verifies a permanent change.

## 5. Evidence and Verification

For a reliable review:

- Record the original page state before repair.
- Capture the viewport dimensions used for inspection.
- Keep screenshots of detected issues.
- Record whether approval was granted.
- Capture the post-repair state.
- Re-test the same viewport and inspect whether the original issue remains.
- Report unsuccessful or inconclusive outcomes honestly.

A screenshot comparison highlights visual differences; it does not by itself prove that the repair is correct.

## 6. Current Detection Scope

The currently documented detection approach uses DOM and computed-style heuristics. These heuristics can identify likely UI problems but may produce false positives or miss some visual defects.

Gemini Vision/VLM integration, automated post-repair verification, Git patch export, and downloadable report export are planned enhancements unless separately implemented and tested.

## 7. Limitations

- Results depend on the target page and browser environment.
- A detected issue requires review before a repair is approved.
- A visual difference is not equivalent to a successful repair.
- Session-scoped CSS does not permanently modify the target website.
- Automated test success does not replace manual visual validation.

## 8. Safety Summary

OmniSight combines browser-based inspection, explicit repair approval, scoped session changes, and post-repair evaluation. Final claims should be based on recorded test output and verified visual evidence.
