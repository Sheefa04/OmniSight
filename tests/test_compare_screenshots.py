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
