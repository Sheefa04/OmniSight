"""
OmniSight – What‑If Repair Sandbox

This module isolates the evaluation of CSS‑based repair candidates.
It provides utilities to:
* launch a fresh Playwright page (identical to the main inspection flow)
* inject a candidate stylesheet into the page
* capture measurements (bounding box, overflow, etc.) and a screenshot
* return a structured result that can be ranked later.

The sandbox is deliberately stateless – each call creates its own browser
context so that candidates never interfere with one another or with the
live inspection/reparation sessions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4
from typing import Dict, Any

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

# NOTE: Lazy imports are performed inside evaluate_css_candidate to avoid a circular import with backend.main
# The required utilities (validate_http_url, parse_viewport, open_browser_page,
# close_browser_resources, SCREENSHOT_DIR) will be imported when the function runs.


logger = logging.getLogger("omnisight.sandbox")

# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------


async def evaluate_css_candidate(
    url: str,
    viewport_str: str,
    css_snippet: str,
    *,
    screenshot_prefix: str = "candidate",
) -> Dict[str, Any]:
    """
    Evaluate a single CSS repair candidate in an isolated browser context.

    Parameters
    ----------
    url: str
        The target page URL (must be a valid HTTP/HTTPS URL).
    viewport_str: str
        Viewport specification, e.g. ``"375x812"`` – the same format used by
        the existing ``/inspect`` endpoint.
    css_snippet: str
        Raw CSS that will be injected into the page via a temporary ``<style>`` tag.
    screenshot_prefix: str, optional
        Prefix for the generated screenshot filename (default ``"candidate"``).

    Returns
    -------
    dict
        A JSON‑serialisable mapping containing:

        * ``status`` – ``"success"`` or ``"error"``.
        * ``message`` – human‑readable description or error detail.
        * ``measurements`` – dictionary with keys like ``bounding_box``,
          ``horizontal_overflow``, ``vertical_overflow`` (populated from the
          page after injection).
        * ``screenshot_path`` – absolute path of the captured screenshot.
        * ``screenshot_url`` – ``/screenshots/<filename>`` for API consumers.
    """
    # Import required utilities from main module
    from backend.main import validate_http_url, parse_viewport, open_browser_page, close_browser_resources, SCREENSHOT_DIR
    # ---- Input validation ------------------------------------------------
    validated_url = validate_http_url(url)
    viewport = parse_viewport(viewport_str)

    # ---- Browser setup ---------------------------------------------------
    try:
        playwright, browser, context, page, response = await open_browser_page(
            validated_url, viewport
        )
    except PlaywrightTimeoutError as exc:
        logger.exception("Page load timeout while evaluating candidate")
        return {
            "status": "error",
            "message": "Page load timed out.",
            "error": str(exc),
        }
    except Exception as exc:
        logger.exception("Failed to launch browser for sandbox")
        return {"status": "error", "message": "Browser launch failed.", "error": str(exc)}

    try:
        # ---- Inject candidate CSS -----------------------------------------
        await page.evaluate(
            """(css) => {
                const style = document.createElement('style');
                style.id = 'omnisight-sandbox-candidate';
                style.textContent = css;
                document.head.appendChild(style);
            }""",
            css_snippet,
        )

        # ---- Gather measurements -------------------------------------------
        measurements = await _collect_measurements(page)

        # ---- Screenshot ----------------------------------------------------
        screenshot_name = f"{screenshot_prefix}_{uuid4().hex[:10]}.png"
        screenshot_path: Path = SCREENSHOT_DIR / screenshot_name
        await page.screenshot(path=str(screenshot_path), full_page=True, animations="disabled")

        return {
            "status": "success",
            "message": "Candidate evaluated.",
            "measurements": measurements,
            "screenshot_path": str(screenshot_path),
            "screenshot_url": f"/screenshots/{screenshot_name}",
        }

    finally:
        # Always clean up the browser resources, even on unexpected failures.
        await close_browser_resources(playwright, browser)


# ----------------------------------------------------------------------
# Internal helper
# ----------------------------------------------------------------------
async def _collect_measurements(page: Page) -> Dict[str, Any]:
    """
    Run a small script in the page to extract the metrics we care about
    after the candidate CSS has been applied.

    Returns a dict with:
    * ``bounding_box`` – ``{x, y, width, height}`` of the first element that
      triggered an issue (or ``null`` if none found).
    * ``horizontal_overflow`` – ``bool`` indicating if any element exceeds
      ``window.innerWidth``.
    * ``vertical_overflow`` – ``bool`` indicating if any element exceeds
      ``window.innerHeight``.
    """
    return await page.evaluate(
        """() => {
            const rects = Array.from(document.querySelectorAll('body *'))
                .map(el => el.getBoundingClientRect());

            const overflowX = rects.some(r => r.right > window.innerWidth || r.left < 0);
            const overflowY = rects.some(r => r.bottom > window.innerHeight || r.top < 0);

            // Find the first element that overflows horizontally (as an example)
            const offending = rects.find(r => r.right > window.innerWidth);
            const bounding_box = offending
                ? {x: offending.x, y: offending.y, width: offending.width, height: offending.height}
                : null;

            return {
                horizontal_overflow: overflowX,
                vertical_overflow: overflowY,
                bounding_box: bounding_box,
            };
        }"""
    )
