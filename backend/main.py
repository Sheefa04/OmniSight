
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
import logging
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl, Field
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnisight")

app = FastAPI(
    title="OmniSight API",
    description="Website inspection, UI issue detection and approved UI repair.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "null",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/screenshots",
    StaticFiles(directory=str(SCREENSHOT_DIR)),
    name="screenshots",
)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class InspectRequest(BaseModel):
    url: HttpUrl
    viewport: str = "375x812"


class RepairRequest(BaseModel):
    url: HttpUrl
    approved: bool = False


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def validate_http_url(url: str) -> str:
    """Allow only HTTP and HTTPS URLs."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid HTTP or HTTPS URL.",
        )

    return url


def parse_viewport(viewport: str) -> dict:
    """Convert a viewport string such as 375x812 into dimensions."""
    match = re.fullmatch(r"\s*(\d{2,4})\s*x\s*(\d{2,4})\s*", viewport)

    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid viewport. Use a format such as 375x812.",
        )

    width, height = map(int, match.groups())

    if not (200 <= width <= 3000 and 300 <= height <= 3000):
        raise HTTPException(
            status_code=400,
            detail="Viewport dimensions are outside the supported range.",
        )

    return {"width": width, "height": height}


async def open_browser_page(url: str, viewport: dict):
    """Launch Chromium and return an inspected page."""
    playwright = await async_playwright().start()

    try:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=viewport,
            ignore_https_errors=False,
        )
        page = await context.new_page()

        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        return playwright, browser, context, page, response

    except Exception:
        await playwright.stop()
        raise


# --------------------------------------------------
# Basic endpoints
# --------------------------------------------------

@app.get("/")
async def root():
    return {
        "status": "success",
        "message": "OmniSight API is running.",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "OmniSight API",
    }


# --------------------------------------------------
# Website inspection
# --------------------------------------------------

@app.post("/inspect")
async def inspect_website(request: InspectRequest):
    url = validate_http_url(str(request.url))
    viewport = parse_viewport(request.viewport)

    try:
        (
            playwright,
            browser,
            context,
            page,
            response,
        ) = await open_browser_page(url, viewport)

        try:
            title = await page.title()
            final_url = page.url

            return {
                "status": "success",
                "message": "Website inspection completed.",
                "title": title,
                "url": final_url,
                "http_status": response.status if response else None,
                "viewport": viewport,
            }

        finally:
            await browser.close()
            await playwright.stop()

    except PlaywrightTimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The website took too long to load.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Website inspection failed")
        raise HTTPException(
            status_code=500,
            detail="Website inspection failed. Check the backend terminal.",
        )


@app.post("/inspect-browser")
async def inspect_browser(request: InspectRequest):
    url = validate_http_url(str(request.url))
    viewport = parse_viewport(request.viewport)

    # Use a unique filename to avoid serving a stale screenshot.
    screenshot_name = f"inspection_{uuid4().hex[:10]}.png"
    screenshot_path = SCREENSHOT_DIR / screenshot_name

    try:
        (
            playwright,
            browser,
            context,
            page,
            response,
        ) = await open_browser_page(url, viewport)

        try:
            await page.screenshot(
                path=str(screenshot_path),
                full_page=True,
                animations="disabled",
            )

            title = await page.title()

            return {
                "status": "success",
                "message": "Website inspection completed.",
                "title": title,
                "url": page.url,
                "http_status": response.status if response else None,
                "viewport": viewport,
                "screenshot": str(screenshot_path),
                "screenshot_url": f"/screenshots/{screenshot_name}",
            }

        finally:
            await browser.close()
            await playwright.stop()

    except PlaywrightTimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The website took too long to load.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Browser inspection failed")
        raise HTTPException(
            status_code=500,
            detail="Browser inspection failed. Check the backend terminal.",
        )


# --------------------------------------------------
# Browser test
# --------------------------------------------------

@app.get("/test-browser")
async def test_browser():
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)

            try:
                page = await browser.new_page()
                await page.goto(
                    "https://example.com",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                return {
                    "status": "success",
                    "message": "Playwright browser test passed.",
                    "title": await page.title(),
                    "url": page.url,
                }

            finally:
                await browser.close()

    except Exception:
        logger.exception("Browser test failed")
        raise HTTPException(
            status_code=500,
            detail=(
                "Browser test failed. Check Playwright installation, "
                "Chromium availability and internet access."
            ),
        )


# --------------------------------------------------
# UI issue detection
# --------------------------------------------------

@app.post("/detect-issues")
async def detect_issues(request: InspectRequest):
    url = validate_http_url(str(request.url))
    viewport = parse_viewport(request.viewport)

    try:
        (
            playwright,
            browser,
            context,
            page,
            response,
        ) = await open_browser_page(url, viewport)

        try:
            issues = await page.evaluate("""() => {
                const found = [];
                const elements = Array.from(
                    document.querySelectorAll('body *')
                );

                for (const el of elements) {
                    const style = getComputedStyle(el);
                    const rect = el.getBoundingClientRect();

                    if (
                        rect.width === 0 ||
                        rect.height === 0 ||
                        style.display === 'none' ||
                        style.visibility === 'hidden'
                    ) {
                        continue;
                    }

                    if (
                        rect.right > window.innerWidth + 1 ||
                        rect.left < -1
                    ) {
                        found.push({
                            type: 'horizontal-overflow',
                            element: el.tagName.toLowerCase(),
                            text: (el.innerText || '').trim().slice(0, 100),
                            description: 'Element extends beyond viewport width.'
                        });
                    }

                    if (
                        style.position === 'absolute' &&
                        rect.top < 0
                    ) {
                        found.push({
                            type: 'positioning',
                            element: el.tagName.toLowerCase(),
                            text: (el.innerText || '').trim().slice(0, 100),
                            description: 'Absolutely positioned element starts above the viewport.'
                        });
                    }

                    if (found.length >= 50) {
                        break;
                    }
                }

                if (document.documentElement.scrollWidth > window.innerWidth) {
                    found.unshift({
                        type: 'page-horizontal-overflow',
                        element: 'html',
                        text: '',
                        description: 'The page is wider than the viewport.'
                    });
                }

                return found;
            }""")

            return {
                "status": "success",
                "message": "Basic DOM-based UI checks completed.",
                "url": page.url,
                "viewport": viewport,
                "http_status": response.status if response else None,
                "issue_count": len(issues),
                "issues": issues,
                "detection_method": "DOM and computed-style heuristics",
            }

        finally:
            await browser.close()
            await playwright.stop()

    except PlaywrightTimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The website took too long to load.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Issue detection failed")
        raise HTTPException(
            status_code=500,
            detail="Issue detection failed. Check the backend terminal.",
        )


# --------------------------------------------------
# Approved UI repair
# --------------------------------------------------

@app.post("/repair-ui")
async def repair_ui(request: RepairRequest):
    if not request.approved:
        raise HTTPException(
            status_code=400,
            detail="Repair not applied. Set approved=true to authorize the demo repair.",
        )

    url = validate_http_url(str(request.url))

    try:
        (
            playwright,
            browser,
            context,
            page,
            response,
        ) = await open_browser_page(
            url,
            {"width": 1366, "height": 768},
        )

        try:
            # This is a temporary demonstration repair in the browser.
            # It does not modify the target website's source files.
            repair_result = await page.evaluate("""() => {
                const button = document.querySelector('button.buggy-button');

                if (!button) {
                    return {
                        applied: false,
                        message: 'No button.buggy-button element was found.'
                    };
                }

                const style = document.createElement('style');
                style.id = 'omnisight-demo-repair';
                style.textContent = `
                    button.buggy-button {
                        position: relative !important;
                        max-width: 100% !important;
                        box-sizing: border-box !important;
                        white-space: normal !important;
                        overflow-wrap: anywhere !important;
                        z-index: 1 !important;
                    }
                `;

                document.head.appendChild(style);

                return {
                    applied: true,
                    message: 'Temporary CSS repair applied to the demo button.'
                };
            }""")

            screenshot_name = f"repair_{uuid4().hex[:10]}.png"
            screenshot_path = SCREENSHOT_DIR / screenshot_name

            await page.screenshot(
                path=str(screenshot_path),
                full_page=True,
                animations="disabled",
            )

            return {
                "status": "success" if repair_result["applied"] else "not_applied",
                "message": repair_result["message"],
                "url": page.url,
                "http_status": response.status if response else None,
                "screenshot_url": f"/screenshots/{screenshot_name}",
                "note": (
                    "The repair exists only in this browser session; "
                    "the original website files were not changed."
                ),
            }

        finally:
            await browser.close()
            await playwright.stop()

    except PlaywrightTimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The website took too long to load.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("UI repair failed")
        raise HTTPException(
            status_code=500,
            detail="UI repair failed. Check the backend terminal.",
        )
