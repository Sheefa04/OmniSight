import sys
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
import logging
import re

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        import uvicorn.loops.asyncio
        uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.ProactorEventLoop
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from .repair_sandbox import evaluate_css_candidate


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR = BASE_DIR.parent / "frontend"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnisight")

app = FastAPI(
    title="OmniSight API",
    description="Website inspection, UI issue detection and approved UI repair.",
    version="1.0.0",
)

# Allow the local frontend served through Live Server, file origin, or any port.
app.add_middleware(
    CORSMiddleware,
    # Local prototype: allow Live Server on any localhost/127.0.0.1 port
    # and avoid failed preflight requests from the dashboard.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)

app.mount(
    "/screenshots",
    StaticFiles(directory=str(SCREENSHOT_DIR)),
    name="screenshots",
)

if FRONTEND_DIR.exists():
    app.mount(
        "/frontend",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
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

class SandboxRequest(BaseModel):
    """Payload for the What‑If Repair Sandbox."""
    url: HttpUrl                     # target page
    viewport: str = "375x812"        # same format as other endpoints
    css: str                         # raw CSS snippet to test


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
    """Convert a viewport such as 375x812 into dimensions."""
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
    """Launch Chromium and return the active browser resources."""
    playwright = await async_playwright().start()
    browser = None

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
        if browser is not None:
            await browser.close()
        await playwright.stop()
        raise


async def close_browser_resources(playwright, browser):
    """Close browser resources safely."""
    try:
        await browser.close()
    finally:
        await playwright.stop()


# --------------------------------------------------
# Basic endpoints
# --------------------------------------------------

@app.get("/")
async def root():
    return {
        "status": "success",
        "message": "OmniSight API is running.",
        "docs": "/docs",
        "dashboard": "/frontend/dashboard.html",
    }


@app.get("/dashboard")
async def dashboard_page():
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "dashboard.html").exists():
        return FileResponse(str(FRONTEND_DIR / "dashboard.html"))
    raise HTTPException(status_code=404, detail="Dashboard not found")


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
        playwright, browser, context, page, response = (
            await open_browser_page(url, viewport)
        )

        try:
            return {
                "status": "success",
                "message": "Website inspection completed.",
                "title": await page.title(),
                "url": page.url,
                "http_status": response.status if response else None,
                "viewport": viewport,
            }
        finally:
            await close_browser_resources(playwright, browser)

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

    screenshot_name = f"inspection_{uuid4().hex[:10]}.png"
    screenshot_path = SCREENSHOT_DIR / screenshot_name

    try:
        playwright, browser, context, page, response = (
            await open_browser_page(url, viewport)
        )

        try:
            await page.screenshot(
                path=str(screenshot_path),
                full_page=True,
                animations="disabled",
            )

            return {
                "status": "success",
                "message": "Website inspection completed.",
                "title": await page.title(),
                "url": page.url,
                "http_status": response.status if response else None,
                "viewport": viewport,
                "screenshot": str(screenshot_path),
                "screenshot_url": f"/screenshots/{screenshot_name}",
            }
        finally:
            await close_browser_resources(playwright, browser)

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
        playwright, browser, context, page, response = (
            await open_browser_page(url, viewport)
        )

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
                            description:
                                'Element extends beyond viewport width.'
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
                            description:
                                'Absolutely positioned element starts above the viewport.'
                        });
                    }
                    
                    const isBrokenButton = el.matches(
    'button.broken-button, button.buggy-button'
);

if (isBrokenButton) {
    found.push({
        type: 'oversized-button',
        element: el.tagName.toLowerCase(),
        text: (el.innerText || el.value || '')
            .trim()
            .slice(0, 100),
        description:
            'Known demo button has intentionally unwrapped text and oversized padding.',
        width: Math.round(rect.width),
        parent_width: el.parentElement
            ? Math.round(
                el.parentElement.getBoundingClientRect().width
            )
            : null
    });
}

                    if (found.length >= 50) {
                        break;
                    }
                }

                if (
                    document.documentElement.scrollWidth >
                    window.innerWidth
                ) {
                    found.unshift({
                        type: 'page-horizontal-overflow',
                        element: 'html',
                        text: '',
                        description: 'The page is wider than the viewport.'
                    });
                }

                return found.slice(0, 50);
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
            await close_browser_resources(playwright, browser)

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
# What‑If Repair Sandbox
# --------------------------------------------------
@app.post("/sandbox-evaluate")
async def sandbox_evaluate(request: SandboxRequest):
    """
    Evaluate one or more CSS repair candidates in an isolated
    Playwright context. Returns measurements and a screenshot for the
    caller to rank the candidate.
    """
    try:
        result = await evaluate_css_candidate(
            url=str(request.url),
            viewport_str=request.viewport,
            css_snippet=request.css,
        )
        return result
    except HTTPException:
        # Preserve original 4xx errors (e.g., invalid viewport)
        raise
    except Exception as exc:  # unexpected failures
        logger.exception("Sandbox evaluation failed")
        raise HTTPException(
            status_code=500,
            detail="Sandbox evaluation failed.",
        )


# --------------------------------------------------
# Approved UI repair
# --------------------------------------------------

@app.post("/repair-ui")
async def repair_ui(request: RepairRequest):
    if not request.approved:
        raise HTTPException(
            status_code=400,
            detail=(
                "Repair not applied. Set approved=true "
                "to authorize the demo repair."
            ),
        )

    url = validate_http_url(str(request.url))

    try:
        playwright, browser, context, page, response = (
            await open_browser_page(
                url,
                {"width": 1366, "height": 768},
            )
        )

        try:
            repair_result = await page.evaluate("""() => {
                const button = document.querySelector('button.buggy-button, button.broken-button');

                if (!button) {
                    return {
                        applied: false,
                        message: 'No button.buggy-button or button.broken-button element was found.'
                    };
                }

                const style = document.createElement('style');
                style.id = 'omnisight-demo-repair';
                style.textContent = `
                    button.buggy-button, button.broken-button {
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
                "status": (
                    "success" if repair_result["applied"] else "not_applied"
                ),
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
            await close_browser_resources(playwright, browser)

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


if __name__ == "__main__":
    import uvicorn
    # reload=False is required on Windows to preserve ProactorEventLoop for Playwright subprocesses
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

