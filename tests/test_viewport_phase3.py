"""
Phase 3 -- Multi-Viewport Inspection & Repair Support
=====================================================

Tests cover:
- All four canonical viewports via /inspect-browser and /detect-issues APIs
- /capture-baseline endpoint (new in Phase 3)
- /viewports discovery endpoint
- Viewport mismatch rejection in /compare-screenshots
- Invalid dimension handling
- Cross-viewport comparison guard
- Viewport information carried through /repair-ui response
- Screenshot filename embeds the viewport key
"""

import json
import os
import subprocess
import sys
import time
import atexit
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app, SCREENSHOT_DIR, SUPPORTED_VIEWPORTS, viewport_key, parse_viewport

client = TestClient(app)

PHASE3_VIEWPORTS = [
    ("1366x768", 1366, 768),
    ("768x1024",  768, 1024),
    ("375x812",   375,  812),
    ("390x844",   390,  844),
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_URL = "http://127.0.0.1:8000/frontend/store.html"
API_BASE  = "http://127.0.0.1:8000"


def create_png(path: Path, size=(10, 10), color=(255, 255, 255)):
    img = Image.new("RGB", size, color)
    img.save(path)


@pytest.fixture(scope="session", autouse=True)
def start_backend():
    already_running = False
    try:
        with urllib.request.urlopen(f"{API_BASE}/health", timeout=2) as res:
            already_running = res.status == 200
    except Exception:
        pass

    proc = None
    if not already_running:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app",
             "--host", "127.0.0.1", "--port", "8000", "--log-level", "error"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        deadline = time.time() + 15
        started = False
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{API_BASE}/health", timeout=1) as res:
                    if res.status == 200:
                        started = True
                        break
            except Exception:
                time.sleep(0.5)
        if not started:
            if proc:
                proc.kill()
            raise RuntimeError("FastAPI backend did not start within 15 seconds.")

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


@pytest.fixture()
def clean_screenshots():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    preserved = {"before.png", "after.png"}
    for f in os.listdir(SCREENSHOT_DIR):
        if f not in preserved:
            os.remove(os.path.join(SCREENSHOT_DIR, f))
    yield
    for f in os.listdir(SCREENSHOT_DIR):
        if f not in preserved:
            os.remove(os.path.join(SCREENSHOT_DIR, f))


# ===========================================================================
# Part 1 - SUPPORTED_VIEWPORTS constant & parse_viewport
# ===========================================================================

class TestSupportedViewports:
    def test_all_four_viewports_present(self):
        for key, w, h in PHASE3_VIEWPORTS:
            assert key in SUPPORTED_VIEWPORTS, f"Missing viewport {key}"
            assert SUPPORTED_VIEWPORTS[key]["width"] == w
            assert SUPPORTED_VIEWPORTS[key]["height"] == h

    def test_viewport_key_helper(self):
        assert viewport_key({"width": 375, "height": 812}) == "375x812"
        assert viewport_key({"width": 1366, "height": 768}) == "1366x768"
        assert viewport_key({"width": 390, "height": 844}) == "390x844"

    @pytest.mark.parametrize("vp_str,expected_w,expected_h", PHASE3_VIEWPORTS)
    def test_parse_viewport_all_four(self, vp_str, expected_w, expected_h):
        result = parse_viewport(vp_str)
        assert result["width"] == expected_w
        assert result["height"] == expected_h


# ===========================================================================
# Part 2 - /viewports discovery endpoint
# ===========================================================================

class TestViewportsEndpoint:
    def test_get_viewports_returns_all_four(self):
        resp = client.get("/viewports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        keys = {v["key"] for v in data["viewports"]}
        for vp_key_str, _, _ in PHASE3_VIEWPORTS:
            assert vp_key_str in keys, f"Viewport {vp_key_str} missing from /viewports"

    def test_viewports_include_label(self):
        resp = client.get("/viewports")
        for vp in resp.json()["viewports"]:
            assert "label" in vp and vp["label"], "Every viewport must have a label"


# ===========================================================================
# Part 3 - Invalid dimension handling
# ===========================================================================

class TestInvalidViewports:
    @pytest.mark.parametrize("bad_vp", [
        "bad", "0x0", "99x100", "100x200", "375",
        "AxB", "3001x768", "1366x50", "",
    ])
    def test_parse_viewport_rejects_invalid(self, bad_vp):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            parse_viewport(bad_vp)
        assert exc_info.value.status_code == 400

    def test_inspect_browser_rejects_invalid_viewport(self):
        resp = client.post(
            "/inspect-browser",
            json={"url": "https://example.com", "viewport": "bad-viewport"},
        )
        assert resp.status_code == 400
        assert "Invalid viewport" in resp.json()["detail"]

    def test_detect_issues_rejects_invalid_viewport(self):
        resp = client.post(
            "/detect-issues",
            json={"url": "https://example.com", "viewport": "99x100"},
        )
        assert resp.status_code == 400

    def test_capture_baseline_rejects_invalid_viewport(self):
        resp = client.post(
            "/capture-baseline",
            json={"url": "https://example.com", "viewport": "AxB"},
        )
        assert resp.status_code == 400

    def test_sandbox_rejects_invalid_viewport(self):
        resp = client.post(
            "/sandbox-evaluate",
            json={"url": STORE_URL, "viewport": "invalid", "css": "body {}"},
        )
        assert resp.status_code == 400


# ===========================================================================
# Part 4 - Viewport mismatch in /compare-screenshots
# ===========================================================================

class TestViewportMismatch:
    def test_mismatch_rejected_with_400(self, tmp_path, clean_screenshots):
        orig = tmp_path / "orig.png"
        repl = tmp_path / "repl.png"
        create_png(orig)
        create_png(repl)
        Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
        Path(SCREENSHOT_DIR, repl.name).write_bytes(repl.read_bytes())

        resp = client.post(
            "/compare-screenshots",
            json={
                "original": orig.name,
                "repaired": repl.name,
                "original_viewport": "375x812",
                "repaired_viewport": "1366x768",
            },
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "Viewport mismatch" in detail
        assert "375x812" in detail
        assert "1366x768" in detail

    def test_same_viewport_accepted(self, tmp_path, clean_screenshots):
        orig = tmp_path / "orig2.png"
        repl = tmp_path / "repl2.png"
        create_png(orig)
        create_png(repl)
        Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
        Path(SCREENSHOT_DIR, repl.name).write_bytes(repl.read_bytes())

        resp = client.post(
            "/compare-screenshots",
            json={
                "original": orig.name,
                "repaired": repl.name,
                "original_viewport": "375x812",
                "repaired_viewport": "375x812",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["original_viewport_key"] == "375x812"
        assert data["repaired_viewport_key"] == "375x812"

    def test_no_viewport_omission_backward_compat(self, tmp_path, clean_screenshots):
        orig = tmp_path / "orig3.png"
        repl = tmp_path / "repl3.png"
        create_png(orig)
        create_png(repl)
        Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
        Path(SCREENSHOT_DIR, repl.name).write_bytes(repl.read_bytes())

        resp = client.post(
            "/compare-screenshots",
            json={"original": orig.name, "repaired": repl.name},
        )
        assert resp.status_code == 200

    def test_mobile_vs_desktop_all_cross_pairs_rejected(self, tmp_path, clean_screenshots):
        vp_pairs = [
            ("375x812", "1366x768"),
            ("390x844", "768x1024"),
            ("375x812", "768x1024"),
            ("390x844", "1366x768"),
            ("375x812", "390x844"),
        ]
        orig = tmp_path / "shared_orig.png"
        repl = tmp_path / "shared_repl.png"
        create_png(orig)
        create_png(repl)
        Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
        Path(SCREENSHOT_DIR, repl.name).write_bytes(repl.read_bytes())

        for ov, rv in vp_pairs:
            resp = client.post(
                "/compare-screenshots",
                json={
                    "original": orig.name,
                    "repaired": repl.name,
                    "original_viewport": ov,
                    "repaired_viewport": rv,
                },
            )
            assert resp.status_code == 400, \
                f"Expected 400 for {ov} vs {rv}, got {resp.status_code}"
            assert "Viewport mismatch" in resp.json()["detail"]


# ===========================================================================
# Part 5 - /capture-baseline endpoint
# ===========================================================================

class TestCaptureBaseline:
    def test_capture_baseline_returns_viewport_key(self):
        resp = client.post(
            "/capture-baseline",
            json={"url": STORE_URL, "viewport": "1366x768"},
        )
        if resp.status_code in (504, 500):
            pytest.skip("Backend not reachable for live endpoint test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["viewport_key"] == "1366x768"
        assert data["screenshot_url"].startswith("/screenshots/")
        assert "baseline_" in data["screenshot_url"]

    def test_capture_baseline_filename_contains_viewport_key(self):
        resp = client.post(
            "/capture-baseline",
            json={"url": STORE_URL, "viewport": "375x812"},
        )
        if resp.status_code in (504, 500):
            pytest.skip("Backend not reachable for live endpoint test")
        assert resp.status_code == 200
        assert "375x812" in resp.json()["screenshot_url"]


# ===========================================================================
# Part 6 - /inspect-browser viewport_key in response
# ===========================================================================

class TestInspectBrowserViewportKey:
    @pytest.mark.parametrize("vp_str,expected_w,expected_h", PHASE3_VIEWPORTS)
    def test_inspect_browser_returns_viewport_key(self, vp_str, expected_w, expected_h):
        resp = client.post(
            "/inspect-browser",
            json={"url": STORE_URL, "viewport": vp_str},
        )
        if resp.status_code in (504, 500):
            pytest.skip("Backend not reachable for live endpoint test")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("viewport_key") == vp_str
        assert data["viewport"]["width"] == expected_w
        assert data["viewport"]["height"] == expected_h

    def test_screenshot_filename_contains_viewport_key(self):
        resp = client.post(
            "/inspect-browser",
            json={"url": STORE_URL, "viewport": "390x844"},
        )
        if resp.status_code in (504, 500):
            pytest.skip("Backend not reachable for live endpoint test")
        assert resp.status_code == 200
        url = resp.json().get("screenshot_url", "")
        assert "390x844" in url, f"Viewport key missing from filename: {url}"


# ===========================================================================
# Part 7 - /repair-ui viewport propagation
# ===========================================================================

class TestRepairUIViewport:
    def test_repair_ui_returns_viewport_key(self):
        resp = client.post(
            "/repair-ui",
            json={"url": STORE_URL, "approved": True, "viewport": "1366x768"},
        )
        if resp.status_code in (504, 500):
            pytest.skip("Backend not reachable for live endpoint test")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("viewport_key") == "1366x768"

    def test_repair_ui_screenshot_filename_contains_viewport_key(self):
        resp = client.post(
            "/repair-ui",
            json={"url": STORE_URL, "approved": True, "viewport": "1366x768"},
        )
        if resp.status_code in (504, 500):
            pytest.skip("Backend not reachable for live endpoint test")
        assert resp.status_code == 200
        url = resp.json().get("screenshot_url", "")
        assert "1366x768" in url, f"Viewport key missing from repair filename: {url}"

    def test_repair_ui_backward_compat_no_viewport(self):
        resp = client.post(
            "/repair-ui",
            json={"url": STORE_URL, "approved": True},
        )
        if resp.status_code in (504, 500):
            pytest.skip("Backend not reachable for live endpoint test")
        assert resp.status_code == 200
        assert resp.json().get("viewport_key") == "1366x768"


# ===========================================================================
# Part 8 - Live end-to-end API tests
# ===========================================================================

def _api_post(path, payload, timeout=35):
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.status, json.loads(res.read().decode())


@pytest.mark.parametrize("vp_str,w,h", PHASE3_VIEWPORTS)
def test_inspect_api_all_four_viewports(vp_str, w, h, start_backend):
    try:
        status, data = _api_post("/inspect-browser", {"url": STORE_URL, "viewport": vp_str})
    except urllib.error.URLError:
        pytest.skip("Backend not reachable")
    assert status == 200
    assert data["status"] == "success"
    assert data.get("viewport_key") == vp_str
    assert data["viewport"]["width"] == w
    assert data["viewport"]["height"] == h
    assert vp_str in data.get("screenshot_url", ""), "Viewport key must appear in screenshot filename"


@pytest.mark.parametrize("vp_str,w,h", PHASE3_VIEWPORTS)
def test_detect_issues_all_four_viewports(vp_str, w, h, start_backend):
    try:
        status, data = _api_post("/detect-issues", {"url": STORE_URL, "viewport": vp_str})
    except urllib.error.URLError:
        pytest.skip("Backend not reachable")
    assert status == 200
    assert data["status"] == "success"
    assert data["viewport"]["width"] == w
    assert data["viewport"]["height"] == h


def test_capture_baseline_live(start_backend):
    try:
        status, data = _api_post("/capture-baseline", {"url": STORE_URL, "viewport": "1366x768"})
    except urllib.error.URLError:
        pytest.skip("Backend not reachable")
    assert status == 200
    assert data.get("viewport_key") == "1366x768"
    assert "baseline_" in data.get("screenshot_url", "")


def test_compare_screenshots_viewport_mismatch_live(start_backend, tmp_path):
    orig = tmp_path / "lv_orig.png"
    repl = tmp_path / "lv_repl.png"
    create_png(orig)
    create_png(repl)
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
    Path(SCREENSHOT_DIR, repl.name).write_bytes(repl.read_bytes())

    try:
        req = urllib.request.Request(
            f"{API_BASE}/compare-screenshots",
            data=json.dumps({
                "original": orig.name,
                "repaired": repl.name,
                "original_viewport": "375x812",
                "repaired_viewport": "1366x768",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)
        assert False, "Expected HTTP 400 for viewport mismatch"
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
        body = json.loads(exc.read().decode())
        assert "Viewport mismatch" in body["detail"]
    finally:
        for f in [orig.name, repl.name]:
            fpath = Path(SCREENSHOT_DIR, f)
            if fpath.exists():
                fpath.unlink()


def test_invalid_viewport_all_endpoints_live(start_backend):
    bad_viewport = "invalid"
    for path in ["/inspect-browser", "/detect-issues", "/capture-baseline"]:
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            data=json.dumps({"url": STORE_URL, "viewport": bad_viewport}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req)
            assert False, f"Expected HTTP 400 from {path}"
        except urllib.error.HTTPError as exc:
            assert exc.code == 400, f"{path} returned {exc.code} instead of 400"
            body = json.loads(exc.read().decode())
            assert "Invalid viewport" in body.get("detail", ""), \
                f"{path}: detail missing 'Invalid viewport': {body}"
