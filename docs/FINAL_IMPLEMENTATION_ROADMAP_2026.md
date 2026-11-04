# OmniSight — Final Implementation Roadmap

**Project:** OmniSight: Multimodal UI Self-Healing & RPA Agent  
**Audit Date:** 4 November 2026  
**Implementation Period:** 5–8 November 2026  
**Project Type:** Solo Internship Project

## 1. Audit Summary — 4 November

The existing project workflow was reviewed before planning further enhancements.

### Existing capabilities identified
- Website inspection using Playwright.
- UI issue detection.
- Supported viewport selection:
  - Desktop: 1366 × 768
  - Tablet: 768 × 1024
  - Mobile: 375 × 812
  - Mobile: 390 × 844
- Human-approved temporary UI repair.
- Automatic post-repair verification.
- Before-and-after screenshot comparison.
- Inspection history displayed in the dashboard.
- HTML report export implementation in the separate frontend JavaScript file.

### Enhancement gaps identified
- Persistent repair history was not found in the inspected frontend/backend files.
- The dashboard history currently records inspections, not repair outcomes.
- The dashboard does not yet have the identified persistent audit trail.
- The inspected dashboard uses one selected viewport per inspection.
- An aggregated Responsive Health Score was not found.
- Explicit Repair Risk Score and Smart Issue Prioritization implementations were not found.
- A dashboard-compatible comprehensive QA report is planned.

These findings are based on the code sections and search patterns inspected during the audit.

## 2. Final Uniqueness Feature Roadmap

### Core features
1. Repair History & Audit Trail
2. Smart Issue Prioritization
3. Repair Risk Score
4. Responsive Health Score
5. Test Coverage Indicator
6. Enhanced HTML QA Report

### Advanced differentiators
7. Visual Regression Intelligence
8. Explainable Repair Recommendations
9. One-Click Repair Rollback — subject to technical feasibility
10. Human-in-the-Loop Safety Dashboard

### Optional enhancement
11. Accessibility Quick Audit:
    - Missing image alternative text
    - Missing form labels
    - Unnamed buttons
    - Basic color contrast checks

## 3. Implementation Schedule

### 5 November — History, Issue Intelligence and Safety
- Implement persistent inspection and repair history.
- Record successful, not-applied and failed repair outcomes.
- Include timestamps, target URLs, viewport details and verification results.
- Introduce explainable issue severity classification.
- Preserve mandatory human approval before repair execution.
- Test history persistence and failure handling.

### 6 November — Scoring and Responsive Intelligence
- Implement a transparent, rule-based Repair Risk Score.
- Develop combined responsive assessment using actual results from supported viewports.
- Introduce Responsive Health Score with an understandable breakdown.
- Display passed, failed and untested checks.
- Validate scoring logic with test cases.

### 7 November — Reporting and Advanced Enhancements
- Enhance dashboard-compatible HTML QA report.
- Include inspection, issue, repair, verification and screenshot-comparison evidence.
- Include available score and coverage results.
- Improve visual regression explanations.
- Add explainable repair recommendations.
- Assess safe rollback feasibility.
- Attempt accessibility checks only if core features are stable.
- Update README, screenshots and final documentation.

### 8 November — Final Validation and Submission
- Run the complete regression test suite.
- Verify all implemented features end-to-end.
- Validate history, scoring and report accuracy.
- Check screenshot and demo evidence.
- Verify GitHub repository and documentation.
- Review final project report and presentation.
- Prepare viva questions and demo rehearsal.
- Organize and back up the final submission package.

## 4. Final Testing Checklist

- [ ] Valid website inspection works.
- [ ] Invalid URLs are safely rejected.
- [ ] All supported viewport sizes can be inspected.
- [ ] Issue severity classification is explainable.
- [ ] Repair cannot execute without approval.
- [ ] Successful repairs are recorded.
- [ ] Not-applied repairs are recorded.
- [ ] Failed repair attempts are handled appropriately.
- [ ] History remains available after dashboard reload.
- [ ] Post-repair verification is displayed correctly.
- [ ] Screenshot comparison works.
- [ ] Risk score matches its test cases.
- [ ] Responsive score uses actual viewport results.
- [ ] Untested viewports are not counted as passed.
- [ ] QA report downloads and contains accurate results.
- [ ] Existing functionality passes regression testing.
- [ ] GitHub repository is clean and synchronized.

## 5. Commit Strategy

Target meaningful commits after implementation and testing:

1. Add persistent repair history and audit trail.
2. Introduce explainable issue prioritization.
3. Add repair risk assessment.
4. Implement responsive health scoring.
5. Enhance visual regression and QA reporting.
6. Finalize project documentation and evidence.

Only completed and tested changes should be committed.

## 6. Engineering and Reporting Principles

- Preserve existing working functionality.
- Do not claim a feature is complete before successful testing.
- Use transparent, explainable scoring formulas.
- Do not describe rule-based scores as AI predictions.
- Keep human approval mandatory for repairs.
- Preserve temporary, session-scoped repair behavior.
- Report external AI provider availability errors honestly.
- Treat rollback and accessibility as optional if they threaten core completion.
- Prefer tested functionality over feature count.

## 7. Final Project Goal

Deliver a working, tested and documented OmniSight prototype demonstrating:

**Website Inspection → Issue Detection → Prioritization → Risk Assessment → Human Approval → Temporary Repair → Post-Repair Verification → Visual Comparison → Audit Trail → QA Report**

The final objective is to demonstrate intelligence, explainability, safety and measurable UI quality improvements.
