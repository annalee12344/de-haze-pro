"""
Benchmark & verification: float64 (original) vs float32 (API) dehazing pipeline.

Runs the same image through DarkChannelPrior with both dtypes and compares:
  - Visual similarity (PSNR, max absolute difference)
  - Processing time
  - Peak memory usage

Usage:
    python api/verify_float32.py [image_path]

If no image path is given, uses 7.jpg in the project root.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

# Ensure project root is importable
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dehaze_torch import DarkChannelPrior


def run_dehaze(image_path: str, dtype: torch.dtype) -> tuple[np.ndarray, float, int]:
    """
    Run DarkChannelPrior on an image with the given dtype.

    Returns (result_uint8, elapsed_ms, peak_memory_bytes).
    """
    pil = Image.open(image_path).convert("RGB")
    arr = np.array(pil, dtype=np.float64 if dtype == torch.float64 else np.float32)

    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)  # (1,3,H,W)
    assert tensor.dtype == dtype, f"Expected {dtype}, got {tensor.dtype}"

    model = DarkChannelPrior(
        kernel_size=15,
        top_candidates_ratio=0.0001,
        omega=0.95,
        radius=40,
        eps=1e-3,
        open_threshold=True,
        depth_est=False,
    )
    model.eval()

    # Warm up (first run may include JIT overhead)
    with torch.no_grad():
        _ = model(tensor)

    # Timed run
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    t0 = time.perf_counter()
    with torch.no_grad():
        outputs = model(tensor)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    elapsed = (time.perf_counter() - t0) * 1000

    dehazed = outputs[0].squeeze(0).permute(1, 2, 0)  # (H,W,3)
    dehazed = dehazed.clamp(0, 255).to(torch.uint8).cpu().numpy()

    # Rough peak memory estimate (CPU — torch doesn't track CPU peak natively)
    # We'll report the tensor sizes instead
    peak_mem = tensor.nelement() * tensor.element_size()

    return dehazed, elapsed, peak_mem


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    """Compute PSNR between two uint8 images."""
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    if mse == 0:
        return float("inf")
    return 10 * np.log10(255.0 ** 2 / mse)


def main():
    # Find image
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = str(Path(_ROOT) / "7.jpg")

    if not Path(image_path).exists():
        print(f"Error: Image not found at {image_path}")
        sys.exit(1)

    pil = Image.open(image_path)
    w, h = pil.size
    print(f"Image: {image_path}")
    print(f"Size:  {w} × {h} ({w*h:,} pixels)")
    print(f"Mode:  {pil.mode}")
    print()

    # --- float64 (original pipeline) ---
    print("=" * 60)
    print("Running float64 (original pipeline)...")
    result_f64, time_f64, mem_f64 = run_dehaze(image_path, torch.float64)
    print(f"  Time:  {time_f64:.1f} ms")
    print(f"  Tensor element size: 8 bytes (float64)")
    print()

    # --- float32 (API pipeline) ---
    print("Running float32 (API pipeline)...")
    result_f32, time_f32, mem_f32 = run_dehaze(image_path, torch.float32)
    print(f"  Time:  {time_f32:.1f} ms")
    print(f"  Tensor element size: 4 bytes (float32)")
    print()

    # --- Comparison ---
    print("=" * 60)
    print("COMPARISON")
    print("-" * 60)

    max_diff = np.max(np.abs(result_f64.astype(int) - result_f32.astype(int)))
    mean_diff = np.mean(np.abs(result_f64.astype(float) - result_f32.astype(float)))
    p = psnr(result_f64, result_f32)

    print(f"  Max pixel difference:  {max_diff}")
    print(f"  Mean pixel difference: {mean_diff:.4f}")
    print(f"  PSNR:                  {p:.2f} dB")
    print(f"  Identical:             {'YES' if max_diff == 0 else 'NO'}")
    print()
    print(f"  float64 time: {time_f64:.1f} ms")
    print(f"  float32 time: {time_f32:.1f} ms")
    print(f"  Speedup:      {time_f64/time_f32:.2f}×")
    print(f"  Memory saved: ~50% (8->4 bytes per element)")
    print()

    if max_diff <= 2:
        print("✓ Results are visually identical (max diff ≤ 2/255).")
        print("  float32 is safe to use for production.")
    elif max_diff <= 5:
        print("⚠ Results have minor differences (max diff ≤ 5/255).")
        print("  float32 is acceptable for production.")
    else:
        print(f"✗ Results differ by up to {max_diff}/255.")
        print("  Review carefully before using float32.")

    # Save side-by-side comparison
    out_f64 = Image.fromarray(result_f64)
    out_f32 = Image.fromarray(result_f32)
    diff = np.abs(result_f64.astype(int) - result_f32.astype(int)).astype(np.uint8)
    # Amplify diff for visibility
    diff_vis = np.clip(diff * 20, 0, 255).astype(np.uint8)
    out_diff = Image.fromarray(diff_vis)

    comparison = Image.new("RGB", (w * 3, h))
    comparison.paste(out_f64, (0, 0))
    comparison.paste(out_f32, (w, 0))
    comparison.paste(out_diff, (w * 2, 0))

    out_path = str(Path(_ROOT) / "float_comparison.png")
    comparison.save(out_path)
    print(f"\nSaved comparison image: {out_path}")
    print(f"  Left: float64 | Center: float32 | Right: diff×20")


if __name__ == "__main__":
    main()
