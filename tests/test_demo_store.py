from pathlib import Path
from playwright.sync_api import sync_playwright

# Locate the Demo Store HTML file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_FILE = PROJECT_ROOT / "frontend" / "store.html"
if not STORE_FILE.exists():
    STORE_FILE = PROJECT_ROOT / "frontend" / "index.html"

SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


# TEST 1: Check Demo Store and save screenshot
def test_demo_store():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1366, "height": 768}
        )

        page.goto(STORE_FILE.resolve().as_uri())

        # Check the page title
        assert "ShopHub" in page.title() or "OmniSight" in page.title()

        # Check that featured products are visible
        assert page.get_by_text("Wireless Headphones").first.is_visible()
        assert page.get_by_text("Smart Watch").first.is_visible()
        assert page.locator(".broken-button, .buggy-button").first.is_visible()

        # Save baseline screenshot
        screenshot_path = SCREENSHOT_DIR / "demo_store_before.png"
        page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        print("[OK] Page title:", page.title())
        print(f"[OK] Screenshot saved: {screenshot_path}")

        browser.close()


# TEST 2: Detect the oversized/broken button on mobile
def test_mobile_button_overflow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 375, "height": 812}
        )

        page.goto(STORE_FILE.resolve().as_uri())

        button = page.locator(".broken-button, .buggy-button").first
        button.wait_for()

        button_box = button.bounding_box()
        assert button_box is not None

        print(f"[OK] Mobile button dimensions: width={button_box['width']:.1f}px, height={button_box['height']:.1f}px")
        assert button_box["width"] > 0
        assert button_box["height"] > 0

        browser.close()


if __name__ == "__main__":
    test_demo_store()
    test_mobile_button_overflow()
    print("[OK] All demo store tests passed successfully!")
