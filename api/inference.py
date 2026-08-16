"""
Reusable inference wrapper around DarkChannelPrior.

Provides a clean PIL Image → PIL Image interface, handling all tensor
conversion, dtype management, and memory cleanup internally.

The DarkChannelPrior model instance is created once and reused across
requests via the module-level `get_model()` function.
"""

from __future__ import annotations

import ctypes
import gc
import os
import sys
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

import numpy as np
import torch
from PIL import Image

# ---------------------------------------------------------------------------
# Ensure the project root is importable so `from dehaze_torch import ...`
# and `from GuideFilter.* import ...` work regardless of cwd.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dehaze_torch import DarkChannelPrior  # noqa: E402


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_KERNEL_SIZE = 15
DEFAULT_TOP_RATIO = 0.0001
DEFAULT_OMEGA = 0.95
DEFAULT_RADIUS = 40
DEFAULT_EPS = 1e-3
DEFAULT_OPEN_THRESHOLD = True

# Maximum dimension (longest edge) before the image is resized.
#
# Measured on the OPTIMIZED pipeline (guided_filter.py + dehaze_torch.py
# rewritten to avoid stack/einsum and to `del` intermediates, plus dynamic
# guided-filter subsampling above ~1MP/~3MP): steady-state peak RSS scales
# at roughly 105-130 MB per additional megapixel of *processed* resolution,
# on top of whatever the base process (Python + torch + numpy/PIL import)
# costs before any request is served. 1536px longest edge (~1.3-1.7MP for
# typical photo aspect ratios) targets a processing-attributable memory
# budget of ~150-220MB, which is intended to leave headroom for a lean
# CPU-only torch import (~150-250MB) under a 512MB limit. This is a
# starting point, not a guarantee for every container/torch build — verify
# and tune it for your actual deployment using the `docker stats` procedure
# (see project notes), then adjust via the env var below if needed.
MAX_DIMENSION = int(os.environ.get("DEHAZE_MAX_DIMENSION", "1536"))

# Minimum dimension — below this top_candidates_nums can become 0.
MIN_DIMENSION = 64


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------
class DehazeResult(NamedTuple):
    """Result bundle returned by `dehaze()`."""
    image: Image.Image           # dehazed RGB image
    processing_time_ms: float    # wall-clock processing time in milliseconds
    original_size: tuple[int, int]   # (width, height) of the input
    processed_size: tuple[int, int]  # (width, height) after optional resize


# ---------------------------------------------------------------------------
# Singleton model holder
# ---------------------------------------------------------------------------
_model: DarkChannelPrior | None = None


def get_model(
    kernel_size: int = DEFAULT_KERNEL_SIZE,
    top_candidates_ratio: float = DEFAULT_TOP_RATIO,
    omega: float = DEFAULT_OMEGA,
    radius: int = DEFAULT_RADIUS,
    eps: float = DEFAULT_EPS,
    open_threshold: bool = DEFAULT_OPEN_THRESHOLD,
) -> DarkChannelPrior:
    """Return the cached DarkChannelPrior instance, creating it on first call."""
    global _model
    if _model is None:
        _model = DarkChannelPrior(
            kernel_size=kernel_size,
            top_candidates_ratio=top_candidates_ratio,
            omega=omega,
            radius=radius,
            eps=eps,
            open_threshold=open_threshold,
            depth_est=False,
        )
        _model.eval()
    return _model


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
class ImageValidationError(Exception):
    """Raised when the uploaded image fails validation."""
    pass


class ServiceBusyError(Exception):
    """Raised when a dehaze request arrives while another is already being
    processed. The deployment target has 512MB RAM and running two
    inferences at once would roughly double peak memory, so requests are
    serialized and a second concurrent request is rejected immediately
    (rather than silently queued) so the caller can retry instead of
    piling up behind a slow request."""
    pass


def validate_image(image: Image.Image) -> Image.Image:
    """
    Validate and normalise an uploaded PIL Image.

    - Ensures the image is decodable.
    - Converts to RGB (strips alpha, handles grayscale, handles palette).
    - Checks minimum dimensions.

    Returns the validated RGB image.
    Raises ImageValidationError on failure.
    """
    try:
        image.load()  # force full decode
    except Exception as exc:
        raise ImageValidationError(f"Cannot decode image: {exc}") from exc

    if image.mode != "RGB":
        try:
            image = image.convert("RGB")
        except Exception as exc:
            raise ImageValidationError(
                f"Cannot convert image mode '{image.mode}' to RGB: {exc}"
            ) from exc

    w, h = image.size
    if w < MIN_DIMENSION or h < MIN_DIMENSION:
        raise ImageValidationError(
            f"Image too small ({w}×{h}). Minimum is {MIN_DIMENSION}×{MIN_DIMENSION}."
        )
    return image


def maybe_resize(image: Image.Image, max_dim: int = MAX_DIMENSION) -> Image.Image:
    """
    Resize the image so its longest edge is at most `max_dim`, preserving
    aspect ratio.  Uses LANCZOS resampling.  Returns the image unchanged
    if it is already within limits.
    """
    w, h = image.size
    longest = max(w, h)
    if longest <= max_dim:
        return image
    scale = max_dim / longest
    new_w = int(w * scale)
    new_h = int(h * scale)
    return image.resize((new_w, new_h), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Concurrency guard — one dehaze inference at a time.
# ---------------------------------------------------------------------------
_inference_lock = threading.Lock()

# Cached libc handle for malloc_trim (Linux only). If unavailable (e.g. when
# developing on macOS/Windows), memory release below becomes a no-op instead
# of crashing.
try:
    _libc = ctypes.CDLL("libc.so.6")
except OSError:
    _libc = None


def _release_free_memory() -> None:
    """
    Ask the allocator to hand freed memory back to the OS.

    Python's refcounting already frees each tensor's memory back to
    PyTorch's/glibc's allocator the moment its last reference goes away
    (the `del` statements throughout dehaze_torch.py / guided_filter.py
    take care of that). But by default glibc malloc keeps freed arenas
    around for reuse rather than returning them to the OS, so a
    long-running process's RSS tends to creep up to (and stay at) its
    all-time peak rather than shrinking back down between requests.
    Calling gc.collect() (to break any reference cycles, mostly a no-op
    for tensors) followed by malloc_trim(0) measurably reduced steady-state
    RSS in testing (~10% peak reduction after repeated requests). Cheap
    enough to run after every request.
    """
    gc.collect()
    if _libc is not None:
        try:
            _libc.malloc_trim(0)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Core inference
# ---------------------------------------------------------------------------
def dispatch_dehaze(
    image: Image.Image,
    algorithm: str,
    *,
    omega: float | None = None,
    max_dim: int = MAX_DIMENSION,
) -> DehazeResult:
    """
    Dispatcher to route the request to the specified dehazing algorithm.
    """
    if algorithm == "dark_channel_prior":
        return _run_dark_channel_prior(image, omega=omega, max_dim=max_dim)
    else:
        raise ImageValidationError(f"Unknown algorithm: '{algorithm}'")


def _run_dark_channel_prior(
    image: Image.Image,
    *,
    omega: float | None = None,
    max_dim: int = MAX_DIMENSION,
) -> DehazeResult:
    """
    Dehaze a PIL Image using the Dark Channel Prior algorithm.

    Parameters
    ----------
    image : PIL.Image.Image
        Input hazy image (any mode — will be converted to RGB).
    omega : float, optional
        Haze removal strength ∈ [0.5, 1.0]. Default uses model default (0.95).
    max_dim : int
        Maximum pixel dimension (longest edge). Images exceeding this are
        resized before processing.

    Returns
    -------
    DehazeResult
        Named tuple with (image, processing_time_ms, original_size, processed_size).

    Raises
    ------
    ServiceBusyError
        If another dehaze request is already being processed.
    """
    if not _inference_lock.acquire(blocking=False):
        raise ServiceBusyError(
            "Another dehaze request is currently being processed. "
            "Please retry shortly."
        )

    try:
        # ---- validate ---------------------------------------------------
        image = validate_image(image)
        original_size = image.size  # (w, h)

        # ---- resize if needed ---------------------------------------------------
        image = maybe_resize(image, max_dim)
        processed_size = image.size

        # ---- PIL → float32 tensor [0-255] shape (1, 3, H, W) -------------------
        arr = np.array(image, dtype=np.float32)          # (H, W, 3)
        tensor = torch.from_numpy(arr).permute(2, 0, 1)  # (3, H, W)
        tensor = tensor.unsqueeze(0)                      # (1, 3, H, W)

        # ---- run inference ------------------------------------------------------
        model = get_model()

        # If omega is overridden, temporarily adjust the model parameter.
        original_omega = model.omega
        if omega is not None:
            model.omega = omega

        t0 = time.perf_counter()
        try:
            # inference_mode is stricter and lighter-weight than no_grad:
            # it skips autograd's version-counter bookkeeping entirely,
            # which no_grad still pays for on every tensor.
            with torch.inference_mode():
                # DarkChannelPrior.forward returns:
                #   (dehaze_images, dc_vis, airlight, raw_t, refined_transmission)
                outputs = model(tensor)
                dehazed_tensor = outputs[0]  # (1, 3, H, W), float, range ~ [0, 255]
                del outputs
        finally:
            # Restore original omega
            model.omega = original_omega

        elapsed_ms = (time.perf_counter() - t0) * 1000

        # ---- tensor → PIL -------------------------------------------------------
        result_arr = dehazed_tensor.squeeze(0).permute(1, 2, 0)  # (H, W, 3)
        result_arr = result_arr.clamp(0, 255).to(torch.uint8).cpu().numpy()
        result_image = Image.fromarray(result_arr, mode="RGB")

        # ---- cleanup ------------------------------------------------------------
        del tensor, dehazed_tensor, arr
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return DehazeResult(
            image=result_image,
            processing_time_ms=elapsed_ms,
            original_size=original_size,
            processed_size=processed_size,
        )
    finally:
        try:
            _release_free_memory()
        finally:
            _inference_lock.release()

def image_to_jpeg_bytes(image: Image.Image, quality: int = 92) -> bytes:
    """Encode a PIL Image as JPEG bytes."""
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()
