
from pathlib import Path
from playwright.sync_api import sync_playwright

# Locate the Demo Store HTML file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_FILE = PROJECT_ROOT / "frontend" / "index.html"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"


# TEST 1: Check Demo Store and save screenshot
def test_demo_store():
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1366, "height": 768}
        )

        # Open our local Demo Store
        page.goto(STORE_FILE.resolve().as_uri())

        # Check the page title
        assert page.title() == "OmniSight Demo Store"

        # Check that all three products are visible
        assert page.get_by_text(
            "Wireless Headphones"
        ).is_visible()

        assert page.get_by_text(
            "Smart Watch"
        ).is_visible()

        assert page.get_by_text(
            "Travel Backpack"
        ).is_visible()

        # Wait for all product photos to load
        page.locator(".product-image").first.wait_for()

        page.wait_for_function(
            """() => [...document.querySelectorAll('.product-image')]
            .every(img => img.complete && img.naturalWidth > 0)"""
        )

        # Save baseline screenshot
        page.screenshot(
            path=str(SCREENSHOT_DIR / "demo_store_before.png"),
            full_page=True
        )

        print("Page title:", page.title())
        print("Product cards: 3")
        print("Product images: loaded")
        print("Screenshot saved: screenshots/demo_store_before.png")

        browser.close()



# TEST 2: Detect the fixed-width button on mobile
def test_mobile_button_overflow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 375, "height": 812}
        )

        page.goto(STORE_FILE.resolve().as_uri())

        button = page.locator(".buggy-button")
        button.wait_for()

        button_box = button.bounding_box()
        card = page.locator(".product-card").nth(2)
        card_box = card.bounding_box()

        assert button_box is not None
        assert card_box is not None

        print("Button width:", button_box["width"])
        print("Card width:", card_box["width"])

        # The button should be narrower than the available card content area
        assert button_box["width"] == 240, (
            "Expected the intentional fixed-width button to be 240px."
        )

        browser.close()
