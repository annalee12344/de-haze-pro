"""Quick integration test for the dehaze API."""
import requests
import sys

BASE = "http://localhost:8000"

def test_health():
    r = requests.get(f"{BASE}/api/health")
    print(f"[HEALTH] Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("  PASS")
    print()

def test_dehaze_success(image_path="7.jpg"):
    print(f"[DEHAZE] Testing with {image_path}...")
    with open(image_path, "rb") as f:
        r = requests.post(
            f"{BASE}/api/dehaze",
            files={"image": (image_path, f, "image/jpeg")},
            data={"omega": "0.95"},
        )
    print(f"  Status: {r.status_code}")
    print(f"  Content-Type: {r.headers.get('content-type')}")
    print(f"  Processing-Time: {r.headers.get('X-Processing-Time-Ms')} ms")
    print(f"  Original: {r.headers.get('X-Original-Width')}x{r.headers.get('X-Original-Height')}")
    print(f"  Processed: {r.headers.get('X-Processed-Width')}x{r.headers.get('X-Processed-Height')}")
    print(f"  Response size: {len(r.content)} bytes")
    assert r.status_code == 200
    assert r.headers.get("content-type") == "image/jpeg"
    assert int(r.headers.get("X-Processing-Time-Ms", 0)) > 0
    # Verify it's a valid JPEG
    assert r.content[:2] == b'\xff\xd8', "Response is not a valid JPEG"
    print("  PASS")
    print()

def test_dehaze_invalid_type():
    r = requests.post(
        f"{BASE}/api/dehaze",
        files={"image": ("test.txt", b"not an image", "text/plain")},
    )
    print(f"[INVALID TYPE] Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 415
    print("  PASS")
    print()

def test_dehaze_empty():
    r = requests.post(
        f"{BASE}/api/dehaze",
        files={"image": ("empty.jpg", b"", "image/jpeg")},
    )
    print(f"[EMPTY FILE] Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 422
    print("  PASS")
    print()

def test_dehaze_corrupted():
    r = requests.post(
        f"{BASE}/api/dehaze",
        files={"image": ("bad.jpg", b"\xff\xd8garbage", "image/jpeg")},
    )
    print(f"[CORRUPTED] Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 422
    print("  PASS")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("DeHaze API Integration Tests")
    print("=" * 60)
    print()

    test_health()
    test_dehaze_invalid_type()
    test_dehaze_empty()
    test_dehaze_corrupted()
    test_dehaze_success()

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
