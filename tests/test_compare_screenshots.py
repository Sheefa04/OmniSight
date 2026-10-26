import os
import json
from pathlib import Path
from PIL import Image, ImageChops
import pytest
from fastapi.testclient import TestClient

from backend.main import app, SCREENSHOT_DIR

client = TestClient(app)

# Helper to create a PNG image
def create_png(path: Path, size=(10, 10), color=(255, 255, 255)):
    img = Image.new('RGB', size, color)
    img.save(path)

# Helper to write a corrupt "image"
def create_corrupt_file(path: Path):
    with open(path, 'w') as f:
        f.write('this is not an image')

@pytest.fixture(autouse=True)
def clean_screenshots():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    # Preserve built-in demo screenshots (before.png, after.png) while cleaning test artifacts
    for f in os.listdir(SCREENSHOT_DIR):
        if f in ('before.png', 'after.png'):
            continue
        os.remove(os.path.join(SCREENSHOT_DIR, f))
    yield
    for f in os.listdir(SCREENSHOT_DIR):
        if f in ('before.png', 'after.png'):
            continue
        os.remove(os.path.join(SCREENSHOT_DIR, f))

def test_identical_images(tmp_path: Path):
    orig = tmp_path / 'orig.png'
    repaired = tmp_path / 'repaired.png'
    create_png(orig)
    create_png(repaired)
    # copy to screenshot dir
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
    Path(SCREENSHOT_DIR, repaired.name).write_bytes(repaired.read_bytes())
    resp = client.post('/compare-screenshots', json={'original': orig.name, 'repaired': repaired.name})
    assert resp.status_code == 200
    data = resp.json()
    assert data['difference_percent'] == 0
    diff_path = Path(SCREENSHOT_DIR, Path(data['diff_url']).name)
    assert diff_path.exists()
    diff_img = Image.open(diff_path)
    orig_img = Image.open(Path(SCREENSHOT_DIR, orig.name))
    diff = ImageChops.difference(diff_img, orig_img)
    assert not diff.getbbox()

def test_one_pixel_change(tmp_path: Path):
    orig = tmp_path / 'orig.png'
    repaired = tmp_path / 'repaired.png'
    create_png(orig)
    create_png(repaired)
    # change a single pixel on repaired image
    img = Image.open(repaired)
    img.putpixel((0, 0), (0, 0, 0))
    img.save(repaired)
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
    Path(SCREENSHOT_DIR, repaired.name).write_bytes(repaired.read_bytes())
    resp = client.post('/compare-screenshots', json={'original': orig.name, 'repaired': repaired.name})
    assert resp.status_code == 200
    data = resp.json()
    # 10x10 = 100 pixels, 1 changed pixel => 1%
    assert data['difference_percent'] == 1
    diff_path = Path(SCREENSHOT_DIR, Path(data['diff_url']).name)
    assert diff_path.exists()
    diff_img = Image.open(diff_path)
    diff = ImageChops.difference(diff_img, Image.open(Path(SCREENSHOT_DIR, orig.name)))
    assert diff.getbbox() is not None

def test_missing_original(tmp_path: Path):
    repaired = tmp_path / 'repaired.png'
    create_png(repaired)
    Path(SCREENSHOT_DIR, repaired.name).write_bytes(repaired.read_bytes())
    resp = client.post('/compare-screenshots', json={'original': 'nonexistent.png', 'repaired': repaired.name})
    assert resp.status_code == 404

def test_missing_repaired(tmp_path: Path):
    orig = tmp_path / 'orig.png'
    create_png(orig)
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
    resp = client.post('/compare-screenshots', json={'original': orig.name, 'repaired': 'nonexistent.png'})
    assert resp.status_code == 404

def test_corrupt_image(tmp_path: Path):
    orig = tmp_path / 'orig.png'
    create_png(orig)
    corrupt = tmp_path / 'corrupt.png'
    create_corrupt_file(corrupt)
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
    Path(SCREENSHOT_DIR, corrupt.name).write_bytes(corrupt.read_bytes())
    resp = client.post('/compare-screenshots', json={'original': orig.name, 'repaired': corrupt.name})
    assert resp.status_code == 400
    assert 'detail' in resp.json()

def test_dimension_mismatch(tmp_path: Path):
    orig = tmp_path / 'orig.png'
    repaired = tmp_path / 'repaired.png'
    create_png(orig, size=(10, 10))
    create_png(repaired, size=(20, 20))
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
    Path(SCREENSHOT_DIR, repaired.name).write_bytes(repaired.read_bytes())
    resp = client.post('/compare-screenshots', json={'original': orig.name, 'repaired': repaired.name})
    assert resp.status_code == 400
    assert 'detail' in resp.json()

def test_invalid_identifier_path_traversal(tmp_path: Path):
    orig = tmp_path / 'orig.png'
    repaired = tmp_path / 'repaired.png'
    create_png(orig)
    create_png(repaired)
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
    Path(SCREENSHOT_DIR, repaired.name).write_bytes(repaired.read_bytes())
    resp = client.post('/compare-screenshots', json={'original': '../outside.png', 'repaired': repaired.name})
    assert resp.status_code == 400
    assert 'detail' in resp.json()

def test_visibly_different_images(tmp_path: Path):
    """Test 100% and 50% visually different images."""
    orig = tmp_path / 'orig_white.png'
    repaired_black = tmp_path / 'repaired_black.png'
    create_png(orig, size=(10, 10), color=(255, 255, 255))
    create_png(repaired_black, size=(10, 10), color=(0, 0, 0))
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())
    Path(SCREENSHOT_DIR, repaired_black.name).write_bytes(repaired_black.read_bytes())
    
    # 100% changed
    resp = client.post('/compare-screenshots', json={'original': orig.name, 'repaired': repaired_black.name})
    assert resp.status_code == 200
    data = resp.json()
    assert data['difference_percent'] == 100.0
    assert data['different_pixels'] == 100
    assert data['total_pixels'] == 100

    # 50% changed: top 5 rows white, bottom 5 rows black
    half_img = Image.new('RGB', (10, 10), (255, 255, 255))
    for y in range(5, 10):
        for x in range(10):
            half_img.putpixel((x, y), (0, 0, 0))
    repaired_half = tmp_path / 'repaired_half.png'
    half_img.save(repaired_half)
    Path(SCREENSHOT_DIR, repaired_half.name).write_bytes(repaired_half.read_bytes())

    resp_half = client.post('/compare-screenshots', json={'original': orig.name, 'repaired': repaired_half.name})
    assert resp_half.status_code == 200
    data_half = resp_half.json()
    assert data_half['difference_percent'] == 50.0
    assert data_half['different_pixels'] == 50

def test_missing_payload_fields(tmp_path: Path):
    """Test rejection when required payload fields are missing."""
    resp1 = client.post('/compare-screenshots', json={})
    assert resp1.status_code == 400
    assert "required" in resp1.json()['detail'].lower()

    resp2 = client.post('/compare-screenshots', json={'original': 'orig.png'})
    assert resp2.status_code == 400
    assert "required" in resp2.json()['detail'].lower()

def test_invalid_identifier_backslash_and_absolute(tmp_path: Path):
    """Test rejection of Windows backslash traversal and absolute paths."""
    orig = tmp_path / 'orig.png'
    create_png(orig)
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())

    # Backslash traversal
    resp_bs = client.post('/compare-screenshots', json={'original': '..\\outside.png', 'repaired': orig.name})
    assert resp_bs.status_code == 400
    assert "invalid screenshot identifier" in resp_bs.json()['detail'].lower()

    # Absolute path with root
    resp_abs = client.post('/compare-screenshots', json={'original': '/etc/passwd', 'repaired': orig.name})
    assert resp_abs.status_code == 400
    assert "invalid screenshot identifier" in resp_abs.json()['detail'].lower()

def test_invalid_identifier_non_string_types(tmp_path: Path):
    """Test rejection when filename identifier is not a string."""
    orig = tmp_path / 'orig.png'
    create_png(orig)
    Path(SCREENSHOT_DIR, orig.name).write_bytes(orig.read_bytes())

    resp = client.post('/compare-screenshots', json={'original': 12345, 'repaired': orig.name})
    assert resp.status_code == 400
    assert "invalid screenshot identifier" in resp.json()['detail'].lower()

