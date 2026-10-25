import sys
import asyncio
import logging
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        import uvicorn.loops.asyncio

        uvicorn.loops.asyncio.asyncio_loop_factory = (
            lambda use_subprocess=False: asyncio.ProactorEventLoop
        )
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from PIL import Image, ImageChops

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

app.add_middleware(
    CORSMiddleware,
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
    viewport: str = "1366x768"


class SandboxRequest(BaseModel):
    url: HttpUrl
    viewport: str = "375x812"
    css: str


class CompareScreenshotsRequest(BaseModel):
    # object permits invalid JSON types to reach our validation,
    # so we can return HTTP 400 instead of automatic HTTP 422.
    original: object = None
    repaired: object = None
    original_viewport: str | None = None
    repaired_viewport: str | None = None


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def validate_http_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid HTTP or HTTPS URL.",
        )

    return url


SUPPORTED_VIEWPORTS = {
    "1366x768": {
        "width": 1366,
        "height": 768,
        "label": "Desktop",
    },
    "768x1024": {
        "width": 768,
        "height": 1024,
        "label": "Tablet",
    },
    "375x812": {
        "width": 375,
        "height": 812,
        "label": "Mobile",
    },
    "390x844": {
        "width": 390,
        "height": 844,
        "label": "Mobile",
    },
}


def viewport_key(viewport: dict) -> str:
    return f"{viewport['width']}x{viewport['height']}"


def parse_viewport(viewport: str) -> dict:
    match = re.fullmatch(
        r"\s*(\d{2,4})\s*x\s*(\d{2,4})\s*",
        viewport,
    )

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


def _ensure_within_screenshot_dir(filename: str) -> Path:
    """Allow only filenames belonging to the screenshot directory."""

    if (
        not filename
        or Path(filename).name != filename
        or "/" in filename
        or "\\" in filename
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid screenshot identifier.",
        )

    path = (SCREENSHOT_DIR / filename).resolve()

    if path.parent != SCREENSHOT_DIR.resolve():
        raise HTTPException(
            status_code=400,
            detail="Invalid screenshot identifier.",
        )

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Screenshot not found.",
        )

    return path


async def open_browser_page(url: str, viewport: dict):
    """Launch Chromium and return active browser resources."""

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
    try:
        await browser.close()
    finally:
        await playwright.stop()


async def capture_full_page_screenshot(page, screenshot_path: Path):
    try:
        await page.evaluate("document.fonts.ready")
    except Exception:
        logger.debug("Could not wait for document fonts.")

    await page.screenshot(
        path=str(screenshot_path),
        full_page=True,
        animations="disabled",
    )


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
    dashboard_file = FRONTEND_DIR / "dashboard.html"

    if dashboard_file.exists():
        return FileResponse(str(dashboard_file))

    raise HTTPException(
        status_code=404,
        detail="Dashboard not found.",
    )


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "OmniSight API",
    }


@app.get("/viewports")
async def get_viewports():
    return {
        "status": "success",
        "viewports": [
            {"key": key, **details}
            for key, details in SUPPORTED_VIEWPORTS.items()
        ],
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
                "viewport_key": viewport_key(viewport),
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
    current_viewport_key = viewport_key(viewport)

    screenshot_name = (
        f"inspection_{current_viewport_key}_{uuid4().hex[:10]}.png"
    )
    screenshot_path = SCREENSHOT_DIR / screenshot_name

    try:
        playwright, browser, context, page, response = (
            await open_browser_page(url, viewport)
        )

        try:
            await capture_full_page_screenshot(page, screenshot_path)

            return {
                "status": "success",
                "message": "Website inspection completed.",
                "title": await page.title(),
                "url": page.url,
                "http_status": response.status if response else None,
                "viewport": viewport,
                "viewport_key": current_viewport_key,
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
# Baseline screenshot
# --------------------------------------------------

@app.post("/capture-baseline")
async def capture_baseline(request: InspectRequest):
    url = validate_http_url(str(request.url))
    viewport = parse_viewport(request.viewport)
    current_viewport_key = viewport_key(viewport)

    screenshot_name = (
        f"baseline_{current_viewport_key}_{uuid4().hex[:10]}.png"
    )
    screenshot_path = SCREENSHOT_DIR / screenshot_name

    try:
        playwright, browser, context, page, response = (
            await open_browser_page(url, viewport)
        )

        try:
            await capture_full_page_screenshot(page, screenshot_path)

            return {
                "status": "success",
                "message": "Baseline screenshot captured successfully.",
                "url": page.url,
                "viewport": viewport,
                "viewport_key": current_viewport_key,
                "http_status": response.status if response else None,
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
        logger.exception("Baseline screenshot capture failed")
        raise HTTPException(
            status_code=500,
            detail="Baseline capture failed. Check the backend terminal.",
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
                            text: (el.innerText || '')
                                .trim().slice(0, 100),
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
                            text: (el.innerText || '')
                                .trim().slice(0, 100),
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
                                .trim().slice(0, 100),
                            description:
                                'Known demo button has intentionally unwrapped text and oversized padding.',
                            width: Math.round(rect.width),
                            parent_width: el.parentElement
                                ? Math.round(
                                    el.parentElement
                                        .getBoundingClientRect().width
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
                        description:
                            'The page is wider than the viewport.'
                    });
                }

                return found.slice(0, 50);
            }""")

            return {
                "status": "success",
                "message": "Basic DOM-based UI checks completed.",
                "url": page.url,
                "viewport": viewport,
                "viewport_key": viewport_key(viewport),
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
# What-If Repair Sandbox
# --------------------------------------------------

@app.post("/sandbox-evaluate")
async def sandbox_evaluate(request: SandboxRequest):
    try:
        url = validate_http_url(str(request.url))
        parse_viewport(request.viewport)

        return await evaluate_css_candidate(
            url=url,
            viewport_str=request.viewport,
            css_snippet=request.css,
        )

    except HTTPException:
        raise
    except Exception:
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
    viewport = parse_viewport(request.viewport)
    current_viewport_key = viewport_key(viewport)

    try:
        playwright, browser, context, page, response = (
            await open_browser_page(url, viewport)
        )

        try:
            repair_result = await page.evaluate("""() => {
                const button = document.querySelector(
                    'button.buggy-button, button.broken-button'
                );

                if (!button) {
                    return {
                        applied: false,
                        message:
                            'No button.buggy-button or button.broken-button element was found.'
                    };
                }

                const style = document.createElement('style');
                style.id = 'omnisight-demo-repair';
                style.textContent = `
                    button.buggy-button,
                    button.broken-button {
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
                    message:
                        'Temporary CSS repair applied to the demo button.'
                };
            }""")

            screenshot_name = (
                f"repair_{current_viewport_key}_{uuid4().hex[:10]}.png"
            )
            screenshot_path = SCREENSHOT_DIR / screenshot_name

            await capture_full_page_screenshot(page, screenshot_path)

            return {
                "status": (
                    "success" if repair_result["applied"] else "not_applied"
                ),
                "message": repair_result["message"],
                "url": page.url,
                "viewport": viewport,
                "viewport_key": current_viewport_key,
                "http_status": response.status if response else None,
                "screenshot": str(screenshot_path),
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


# --------------------------------------------------
# Screenshot comparison
# --------------------------------------------------

def compare_images(
    original_path: Path,
    repaired_path: Path,
    *,
    original_viewport_key: str | None = None,
    repaired_viewport_key: str | None = None,
) -> dict:
    """Compare screenshots without stretching or hiding width mismatches."""

    if (
        original_viewport_key
        and repaired_viewport_key
        and original_viewport_key != repaired_viewport_key
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Viewport mismatch: cannot compare screenshots captured "
                f"at different viewports: {original_viewport_key} "
                f"vs {repaired_viewport_key}."
            ),
        )

    try:
        with Image.open(original_path) as original_image:
            orig = original_image.convert("RGB")

        with Image.open(repaired_path) as repaired_image:
            repl = repaired_image.convert("RGB")

    except Exception:
        logger.exception("Failed to open screenshots for comparison")
        raise HTTPException(
            status_code=400,
            detail="Failed to open images.",
        )

    if orig.width != repl.width:
        raise HTTPException(
            status_code=400,
            detail=(
                "Images have different widths: "
                f"{orig.width}px vs {repl.width}px. "
                "Capture both screenshots at the same viewport width."
            ),
        )

    common_height = max(orig.height, repl.height)

    if orig.height != repl.height:
        aligned_orig = Image.new(
            "RGB",
            (orig.width, common_height),
            (255, 255, 255),
        )
        aligned_repl = Image.new(
            "RGB",
            (repl.width, common_height),
            (255, 255, 255),
        )

        aligned_orig.paste(orig, (0, 0))
        aligned_repl.paste(repl, (0, 0))

        orig = aligned_orig
        repl = aligned_repl

    diff = ImageChops.difference(orig, repl)
    diff_data = diff.getdata()
    total_pixels = orig.width * orig.height

    diff_pixels = sum(
        1
        for pixel in diff_data
        if any(channel != 0 for channel in pixel)
    )

    diff_percent = (
        (diff_pixels / total_pixels) * 100
        if total_pixels
        else 0
    )

    diff_name = f"diff_{uuid4().hex[:10]}.png"
    diff_path = SCREENSHOT_DIR / diff_name

    # When screenshots are identical, save the original as the
    # difference image so the zero-difference case is handled correctly.
    if diff_pixels == 0:
        orig.save(diff_path)
    else:
        diff.save(diff_path)

    return {
        "status": "success",
        "original_url": f"/screenshots/{original_path.name}",
        "repaired_url": f"/screenshots/{repaired_path.name}",
        "diff_url": f"/screenshots/{diff_name}",
        "difference_percent": round(diff_percent, 2),
        "total_pixels": total_pixels,
        "different_pixels": diff_pixels,
        "original_viewport_key": original_viewport_key,
        "repaired_viewport_key": repaired_viewport_key,
        "dimensions": {
            "width": orig.width,
            "height": orig.height,
        },
    }


@app.post("/compare-screenshots")
async def compare_screenshots(payload: CompareScreenshotsRequest):
    if not isinstance(payload.original, str) or not payload.original:
        raise HTTPException(
            status_code=400,
            detail="Missing or invalid screenshot identifier.",
        )

    if not isinstance(payload.repaired, str) or not payload.repaired:
        raise HTTPException(
            status_code=400,
            detail="Missing or invalid screenshot identifier.",
        )

    original_path = _ensure_within_screenshot_dir(payload.original)
    repaired_path = _ensure_within_screenshot_dir(payload.repaired)

    return compare_images(
        original_path,
        repaired_path,
        original_viewport_key=payload.original_viewport,
        repaired_viewport_key=payload.repaired_viewport,
    )


# --------------------------------------------------
# Run directly
# --------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )