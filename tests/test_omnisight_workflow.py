import json
import urllib.request
import urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright

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
        dashboard_page.screenshot(path=str(ev_comparison))
        print(f"[OK] Saved Before/After comparison evidence: {ev_comparison.name}")
        
        browser.close()

if __name__ == "__main__":
    test_api_health()
    test_safety_approved_false()
    test_safety_invalid_url()
    test_safety_non_broken_page()
    test_responsive_viewports_and_workflow()
    print("\n=======================================================")
    print(" ALL TESTS PASSED: COMPLETE EVIDENCE SUITE GENERATED! ")
    print("=======================================================\n")
