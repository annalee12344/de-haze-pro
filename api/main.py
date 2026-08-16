"""
FastAPI application for the Dark Channel Prior dehazing service.

Endpoints
---------
GET  /api/health   → service health check
POST /api/dehaze   → dehaze an uploaded image

Designed to work both in local development and on Hugging Face Spaces.
In production (HF Spaces), the built React frontend is served as static
files from this same FastAPI process, so everything runs on a single port.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from io import BytesIO

from api.inference import (
    ImageValidationError,
    ServiceBusyError,
    dispatch_dehaze,
    image_to_jpeg_bytes,
    MAX_DIMENSION,
    MIN_DIMENSION,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg",  # some browsers send this
}

logger = logging.getLogger("dehaze-api")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DeHaze API",
    description="Dark Channel Prior image dehazing service",
    version="1.0.0",
)

# CORS — permissive in development.  In production on HF Spaces the
# frontend is served from the same origin, so CORS isn't needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=[
        "X-Processing-Time-Ms",
        "X-Original-Width",
        "X-Original-Height",
        "X-Processed-Width",
        "X-Processed-Height",
    ],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    """Service health check."""
    import torch
    return {
        "status": "ok",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "max_dimension": MAX_DIMENSION,
        "max_upload_mb": MAX_UPLOAD_BYTES / (1024 * 1024),
    }


@app.post("/api/dehaze")
async def dehaze_endpoint(
    image: UploadFile = File(..., description="Hazy image (JPEG, PNG, or WEBP)"),
    omega: float = Form(default=0.95, ge=0.5, le=1.0, description="Haze removal strength"),
    algorithm: str = Form(default="dark_channel_prior", description="Dehazing algorithm to use"),
):
    """
    Dehaze an uploaded image using the Dark Channel Prior algorithm.

    Accepts multipart/form-data with:
    - `image`: the hazy image file (JPEG, PNG, or WEBP, max 20 MB)
    - `omega`: (optional) haze removal strength, 0.5–1.0, default 0.95

    Returns the dehazed image as JPEG with metadata in response headers.
    """
    # ---- validate content type ---------------------------------------------
    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{content_type}'. "
                   f"Accepted: JPEG, PNG, WEBP.",
        )

    # ---- read and validate size --------------------------------------------
    image_bytes = await image.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large ({len(image_bytes) / 1024 / 1024:.1f} MB). "
                   f"Maximum is {MAX_UPLOAD_BYTES / 1024 / 1024:.0f} MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(status_code=422, detail="Empty file uploaded.")

    # ---- open as PIL Image -------------------------------------------------
    try:
        pil_image = Image.open(BytesIO(image_bytes))
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Cannot decode the uploaded file as an image.",
        )

    # ---- check dimensions before processing --------------------------------
    w, h = pil_image.size
    max_allowed = 3840  # reject absurdly large images outright
    if w > max_allowed or h > max_allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Image dimensions ({w}×{h}) exceed the maximum "
                   f"({max_allowed}×{max_allowed}). Please resize first.",
        )

    # ---- run dehazing ------------------------------------------------------
    try:
        result = dispatch_dehaze(pil_image, algorithm=algorithm, omega=omega)
    except ServiceBusyError as exc:
        # One inference at a time on a 512MB instance — reject fast instead
        # of silently queuing, so the client can retry with backoff.
        raise HTTPException(status_code=503, detail=str(exc))
    except ImageValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Dehazing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Dehazing failed: {exc}",
        )

    # ---- encode result as JPEG ---------------------------------------------
    jpeg_bytes = image_to_jpeg_bytes(result.image, quality=92)

    return Response(
        content=jpeg_bytes,
        media_type="image/jpeg",
        headers={
            "X-Processing-Time-Ms": f"{result.processing_time_ms:.0f}",
            "X-Original-Width": str(result.original_size[0]),
            "X-Original-Height": str(result.original_size[1]),
            "X-Processed-Width": str(result.processed_size[0]),
            "X-Processed-Height": str(result.processed_size[1]),
        },
    )


# ---------------------------------------------------------------------------
# Static file serving for production (Hugging Face Spaces)
#
# In production, the React frontend is pre-built and its output files
# are placed in a `static/` directory at the project root.
# ---------------------------------------------------------------------------
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.is_dir():
    from fastapi.responses import FileResponse
    from fastapi import Request

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        # Try to serve the exact file
        file_path = _static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Fallback to index.html for React Router
        index_path = _static_dir / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
        
        raise HTTPException(status_code=404, detail="File not found")
