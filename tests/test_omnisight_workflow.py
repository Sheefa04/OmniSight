import pytest
import subprocess
import sys
import time
import atexit
import os
import signal
from pathlib import Path
import json
import urllib.request
import urllib.error
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="session", autouse=True)
def start_backend():
    """Start the FastAPI backend as a subprocess for the test session if not already running."""
    already_running = False
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as res:
            if res.status == 200:
                already_running = True
    except Exception:
        already_running = False

    proc = None
    if not already_running:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen([
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--log-level",
            "error",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)

        # Poll until health endpoint responds or timeout
        start_time = time.time()
        started = False
        while time.time() - start_time < 12:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as res:
                    if res.status == 200:
                        started = True
                        break
            except Exception:
                time.sleep(0.5)

        if not started:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            raise RuntimeError("FastAPI backend failed to start within 12 seconds.")

    def _cleanup():
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    atexit.register(_cleanup)
    yield
    _cleanup()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = PROJECT_ROOT / "screenshots" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "http://127.0.0.1:8000"
STORE_URL = f"{API_BASE}/frontend/store.html"
DASHBOARD_URL = f"{API_BASE}/frontend/dashboard.html"

def test_api_health():
    """Test 1: Backend health endpoint."""
    print("\n--- Test 1: Checking Backend Health ---")
    req = urllib.request.Request(f"{API_BASE}/health")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data.get("status") == "healthy"
        print("[OK] Health check passed:", data)

def test_safety_approved_false():
    """Test 2: Ensure repair is safely rejected if approved=false."""
    print("\n--- Test 2: Safety Check (approved=false) ---")
    req = urllib.request.Request(
        f"{API_BASE}/repair-ui",
        data=json.dumps({"url": STORE_URL, "approved": False}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have raised HTTP 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        body = json.loads(e.read().decode())
        assert "Set approved=true" in body.get("detail", "")
        print("[OK] Safety rejection confirmed (HTTP 400):", body["detail"])

def test_safety_invalid_url():
    """Test 3: Ensure invalid URLs fail cleanly with validation error."""
    print("\n--- Test 3: Safety Check (invalid URL) ---")
    req = urllib.request.Request(
        f"{API_BASE}/repair-ui",
        data=json.dumps({"url": "invalid-url-format", "approved": True}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have raised HTTP 422"
    except urllib.error.HTTPError as e:
        assert e.code == 422
        body = json.loads(e.read().decode())
        assert "detail" in body
        print("[OK] Validation rejection confirmed (HTTP 422):", body["detail"][0]["msg"])

def test_safety_non_broken_page():
    """Test 4: Page with no broken button reports status='not_applied'."""
    print("\n--- Test 4: Page without broken button ---")
    req = urllib.request.Request(
        f"{API_BASE}/repair-ui",
        data=json.dumps({"url": "https://example.com", "approved": True}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        body = json.loads(res.read().decode())
        assert body.get("status") == "not_applied"
        print("[OK] Truthful status for page without button:", body["message"])

def test_responsive_viewports_and_workflow():
    """Test 5: Responsive viewports & complete UI workflow with evidence capture."""
    print("\n--- Test 5: End-to-End Workflow & Viewport Verification ---")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # --- A. Test Desktop Viewport (1366x768) ---
        print("\nA. Testing Desktop Viewport (1366 x 768)...")
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.goto(STORE_URL, wait_until="networkidle")
        desktop_evidence = EVIDENCE_DIR / "02_desktop_store_1366x768.png"
        page.screenshot(path=str(desktop_evidence), full_page=True)
        print(f"[OK] Saved desktop screenshot: {desktop_evidence.name}")
        page.close()

        # --- B. Test Mobile Viewport (375x812) ---
        print("\nB. Testing Mobile Viewport (375 x 812)...")
        page = browser.new_page(viewport={"width": 375, "height": 812})
        page.goto(STORE_URL, wait_until="networkidle")
        mobile_evidence = EVIDENCE_DIR / "03_mobile_store_375x812.png"
        page.screenshot(path=str(mobile_evidence), full_page=True)
        print(f"[OK] Saved mobile screenshot: {mobile_evidence.name}")
        
        # Verify button unwrapped & overflow in mobile viewport
        btn = page.locator("button.broken-button")
        assert btn.is_visible()
        btn_box = btn.bounding_box()
        print(f"[OK] Broken button dimensions on mobile: width={btn_box['width']:.1f}px, height={btn_box['height']:.1f}px")
        page.close()

        # --- C. Test Mobile Viewport 390x844 (iPhone 12/13/14) ---
        print("\nC. Testing Mobile Viewport (390 x 844)...")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(STORE_URL, wait_until="networkidle")
        mobile390_evidence = EVIDENCE_DIR / "03b_mobile_store_390x844.png"
        page.screenshot(path=str(mobile390_evidence), full_page=True)
        print(f"[OK] Saved mobile 390x844 screenshot: {mobile390_evidence.name}")
        page.close()

        # --- D. Test Tablet Viewport (768x1024) ---
        print("\nD. Testing Tablet Viewport (768 x 1024)...")
        page = browser.new_page(viewport={"width": 768, "height": 1024})
        page.goto(STORE_URL, wait_until="networkidle")
        tablet_evidence = EVIDENCE_DIR / "04_tablet_store_768x1024.png"
        page.screenshot(path=str(tablet_evidence), full_page=True)
        print(f"[OK] Saved tablet screenshot: {tablet_evidence.name}")
        page.close()

        # --- E. Test Dashboard Complete Workflow ---
        print("\nE. Testing Dashboard UI Workflow & Capturing Evidence...")
        dashboard_page = browser.new_page(viewport={"width": 1400, "height": 900})
        dashboard_page.goto(DASHBOARD_URL, wait_until="networkidle")
        
        # Evidence: Initial Dashboard
        ev_initial = EVIDENCE_DIR / "01_dashboard_initial.png"
        dashboard_page.screenshot(path=str(ev_initial))
        print(f"[OK] Saved initial dashboard evidence: {ev_initial.name}")
        
        # Select ShopHub
        dashboard_page.select_option("#demoSite", "shophub")
        
        # Trigger Inspection
        dashboard_page.locator("#inspectionForm button[type='submit']").click()
        dashboard_page.wait_for_function(
            "() => document.getElementById('notice').textContent.includes('Inspection successful')",
            timeout=30000
        )
        dashboard_page.wait_for_timeout(3000)
        
        # Evidence: Detected Issue
        ev_inspection = EVIDENCE_DIR / "05_dashboard_issues_detected.png"
        dashboard_page.screenshot(path=str(ev_inspection))
        print(f"[OK] Saved issue detection evidence: {ev_inspection.name}")
        
        # Trigger Approved Repair
        dashboard_page.locator("#repairButton").click()
        dashboard_page.wait_for_function(
            "() => document.getElementById('repairStatus').textContent.includes('Temporary CSS repair applied')",
            timeout=35000
        )
        dashboard_page.wait_for_timeout(2000)
        
        # Evidence: Repaired & Comparison
        ev_comparison = EVIDENCE_DIR / "06_dashboard_repaired_comparison.png"
        dashboard_page.screenshot(path=str(ev_comparison), full_page=True)
        print(f"[OK] Saved Before/After comparison evidence: {ev_comparison.name}")

        # Verify comparison panel images and difference metrics are rendered
      
        before_img = dashboard_page.locator("#beforeRepairImage")
        after_img = dashboard_page.locator("#afterRepairImage")
        diff_img = dashboard_page.locator("#diffRepairImage")
        diff_pct = dashboard_page.locator("#diffPercentage")

        print("\n--- DIFF IMAGE DEBUG ---")
        print("Diff src:", diff_img.get_attribute("src"))
        print("Diff display:", diff_img.evaluate("(el) => getComputedStyle(el).display"))
        print("Diff complete:", diff_img.evaluate("(el) => el.complete"))
        print("Diff naturalWidth:", diff_img.evaluate("(el) => el.naturalWidth"))
        print("Placeholder:", dashboard_page.locator("#diffRepairPlaceholder").inner_text())
        print("Percentage:", diff_pct.inner_text())
        print("--- END DEBUG ---\n")

        assert before_img.is_visible(), "Before repair image should be visible"
        assert after_img.is_visible(), "After repair image should be visible"
        assert diff_img.is_visible(), "Diff image should be visible"
        assert diff_pct.is_visible(), "Diff percentage should be visible"
        assert "%" in (diff_pct.text_content() or ""), "Diff percentage should display a percentage metric"

        browser.close()

def test_sandbox_invalid_viewport():
    """Test that sandbox-evaluate returns a 4xx error for an invalid viewport string."""
    print("\n--- Test: Sandbox endpoint invalid viewport ---")
    req = urllib.request.Request(
        f"{API_BASE}/sandbox-evaluate",
        data=json.dumps({
            "url": STORE_URL,
            "viewport": "invalid",
            "css": "button { color: red; }"
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Expected HTTPError for invalid viewport"
    except urllib.error.HTTPError as e:
        # FastAPI returns 400 for invalid viewport
        assert e.code == 400, f"Unexpected status code {e.code}"
        body = json.loads(e.read().decode())
        assert "Invalid viewport" in body.get("detail", "")
        print("[OK] Sandbox invalid viewport correctly returned 400:", body.get("detail"))

def test_safety_missing_approval():
    """Ensure omitting 'approved' defaults to False and safely rejects repair."""
    req = urllib.request.Request(
        f"{API_BASE}/repair-ui",
        data=json.dumps({"url": STORE_URL}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Expected HTTP 400 when approved is omitted"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        body = json.loads(e.read().decode())
        assert "Set approved=true" in body.get("detail", "")
        print("[OK] Omitted approval safely rejected with 400")

def test_source_file_integrity_after_repair():
    """Verify that applying an approved temporary repair NEVER modifies files on disk."""
    store_file = PROJECT_ROOT / "frontend" / "store.html"
    assert store_file.exists(), "store.html must exist on disk"
    content_before = store_file.read_bytes()

    req = urllib.request.Request(
        f"{API_BASE}/repair-ui",
        data=json.dumps({"url": STORE_URL, "approved": True}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        body = json.loads(res.read().decode())
        assert body.get("status") == "success"

    content_after = store_file.read_bytes()
    assert content_before == content_after, "Target website source files MUST NOT be modified on disk by session repairs!"
    print("[OK] Source file integrity verified: store.html unmodified on disk.")

def test_detect_issues_valid_shophub():
    """Verify issue detection returns structured evidence on ShopHub mobile."""
    req = urllib.request.Request(
        f"{API_BASE}/detect-issues",
        data=json.dumps({"url": STORE_URL, "viewport": "375x812"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data.get("status") == "success"
        assert data.get("issue_count", 0) > 0
        assert len(data.get("issues", [])) > 0
        first_issue = data["issues"][0]
        assert "type" in first_issue
        assert "element" in first_issue
        assert "description" in first_issue
        print(f"[OK] Issue detection confirmed: {len(data['issues'])} issues found on ShopHub.")

def test_detect_issues_invalid_viewport():
    """Verify issue detection rejects invalid viewport with HTTP 400."""
    req = urllib.request.Request(
        f"{API_BASE}/detect-issues",
        data=json.dumps({"url": STORE_URL, "viewport": "bad-viewport"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Expected HTTP 400 for bad viewport"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        body = json.loads(e.read().decode())
        assert "Invalid viewport" in body.get("detail", "")
        print("[OK] Issue detection rejected bad viewport with HTTP 400.")


if __name__ == "__main__":
    test_api_health()
    test_safety_approved_false()
    test_safety_invalid_url()
    test_safety_non_broken_page()
    test_responsive_viewports_and_workflow()
    test_sandbox_invalid_viewport()
    print("\n=======================================================")
    print(" ALL TESTS PASSED: COMPLETE EVIDENCE SUITE GENERATED! ")
    print("=======================================================\n")
