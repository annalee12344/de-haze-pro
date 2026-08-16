import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
sys.path.append("../..")
from GuideFilter.boxfilter import boxfilter2d

# from boxfilter import boxfilter2d


class GuidedFilter2d(nn.Module):
    """
    Same public behaviour as the original implementation. `forward` now
    accepts an optional per-call `scale` (in addition to whatever the
    instance was built with) so a single module instance can be used at
    full resolution for small images and at a reduced resolution for large
    ones, without needing two separate module instances.
    """
    def __init__(self, radius: int, eps: float):
        super().__init__()
        self.r = radius
        self.eps = eps

    def forward(self, x, guide, scale=None):
        if guide.shape[1] == 3:
            return guidedfilter2d_color(guide, x, self.r, self.eps, scale)
        elif guide.shape[1] == 1:
            return guidedfilter2d_gray(guide, x, self.r, self.eps, scale)
        else:
            raise NotImplementedError


class FastGuidedFilter2d(GuidedFilter2d):
    """Fast guided filter — same as GuidedFilter2d but defaults to
    subsampling by `s` unless a call-site `scale` overrides it."""
    def __init__(self, radius: int, eps: float, s: int):
        super().__init__(radius, eps)
        self.s = s

    def forward(self, x, guide, scale=None):
        s = scale if scale is not None else self.s
        if guide.shape[1] == 3:
            return guidedfilter2d_color(guide, x, self.r, self.eps, s)
        elif guide.shape[1] == 1:
            return guidedfilter2d_gray(guide, x, self.r, self.eps, s)
        else:
            raise NotImplementedError


def guidedfilter2d_color(guide, src, radius, eps, scale=None):
    """guided filter for a color guide image

    Parameters
    -----
    guide: (B, 3, H, W)-dim torch.Tensor
        guide image
    src: (B, C, H, W)-dim torch.Tensor
        filtering image
    radius: int
        filter radius
    eps: float
        regularization coefficient
    scale: int or None
        if set (> 1), guide/src are downsampled by this factor before the
        O(H*W) linear-system solve and the resulting (a, b) coefficient
        maps are bilinearly upsampled back to full resolution. This is the
        standard "fast guided filter" approximation (He & Sun, 2015) and is
        NOT bit-exact with the full-resolution filter — transmission maps
        are smooth/low-frequency so the visual difference is small, but it
        is an approximation, not a refactor. Pass scale=None (default) for
        the exact original computation.

    Memory notes
    -----
    This produces numerically the same result as the original
    stack/einsum-based implementation (when scale=None) — it is a pure
    refactor, not an approximation. The original built a (B,3,3,H,W)
    inverse-covariance tensor via torch.stack and multiplied it against a
    (B,3,C,H,W) stacked covariance tensor via torch.einsum; einsum's
    internal broadcast-multiply materializes a full (B,3,3,C,H,W) buffer
    before summing. Because every intermediate here is a local variable,
    Python's function-scope keeps ALL of them alive until the function
    returns (nothing is freed just because it's "not needed anymore"),
    so peak memory was effectively the SUM of ~25-30 full-resolution
    tensors. This version computes the same 3x3 symmetric linear solve
    directly, one output channel at a time, and explicitly `del`s each
    intermediate the moment it's no longer needed, so peak memory is
    bounded by a small constant number of full-resolution tensors instead.
    """
    assert guide.shape[1] == 3
    if src.ndim == 3:
        src = src[:, None]

    full_res_guide = None
    if scale is not None and scale > 1:
        full_res_guide = guide
        src = F.interpolate(src, scale_factor=1. / scale, mode="nearest")
        guide = F.interpolate(guide, scale_factor=1. / scale, mode="nearest")
        radius = max(1, radius // scale)

    guide_r, guide_g, guide_b = torch.chunk(guide, 3, 1)  # b x 1 x H x W
    ones = torch.ones_like(guide_r)
    N = boxfilter2d(ones, radius)
    del ones

    mean_I = boxfilter2d(guide, radius) / N  # b x 3 x H x W
    mean_I_r, mean_I_g, mean_I_b = torch.chunk(mean_I, 3, 1)
    del mean_I

    mean_p = boxfilter2d(src, radius) / N  # b x C x H x W

    mean_Ip_r = boxfilter2d(guide_r * src, radius) / N
    cov_Ip_r = mean_Ip_r - mean_I_r * mean_p
    del mean_Ip_r

    mean_Ip_g = boxfilter2d(guide_g * src, radius) / N
    cov_Ip_g = mean_Ip_g - mean_I_g * mean_p
    del mean_Ip_g

    mean_Ip_b = boxfilter2d(guide_b * src, radius) / N
    cov_Ip_b = mean_Ip_b - mean_I_b * mean_p
    del mean_Ip_b

    var_I_rr = boxfilter2d(guide_r * guide_r, radius) / N - mean_I_r * mean_I_r + eps
    var_I_rg = boxfilter2d(guide_r * guide_g, radius) / N - mean_I_r * mean_I_g
    var_I_rb = boxfilter2d(guide_r * guide_b, radius) / N - mean_I_r * mean_I_b
    var_I_gg = boxfilter2d(guide_g * guide_g, radius) / N - mean_I_g * mean_I_g + eps
    var_I_gb = boxfilter2d(guide_g * guide_b, radius) / N - mean_I_g * mean_I_b
    var_I_bb = boxfilter2d(guide_b * guide_b, radius) / N - mean_I_b * mean_I_b + eps

    cov_det = (
        var_I_rr * var_I_gg * var_I_bb
        + var_I_rg * var_I_gb * var_I_rb
        + var_I_rb * var_I_rg * var_I_gb
        - var_I_rb * var_I_gg * var_I_rb
        - var_I_rg * var_I_rg * var_I_bb
        - var_I_rr * var_I_gb * var_I_gb
    )  # b x 1 x H x W

    # Inverse of the symmetric 3x3 covariance matrix, computed directly
    # (equivalent to the original torch.stack(...).squeeze(-3) result, just
    # without ever materializing the (B,3,3,H,W) stacked tensor).
    inv_var_I_rr = (var_I_gg * var_I_bb - var_I_gb * var_I_gb) / cov_det
    inv_var_I_rg = -(var_I_rg * var_I_bb - var_I_rb * var_I_gb) / cov_det
    inv_var_I_rb = (var_I_rg * var_I_gb - var_I_rb * var_I_gg) / cov_det
    inv_var_I_gg = (var_I_rr * var_I_bb - var_I_rb * var_I_rb) / cov_det
    inv_var_I_gb = -(var_I_rr * var_I_gb - var_I_rb * var_I_rg) / cov_det
    inv_var_I_bb = (var_I_rr * var_I_gg - var_I_rg * var_I_rg) / cov_det
    del var_I_rr, var_I_rg, var_I_rb, var_I_gg, var_I_gb, var_I_bb, cov_det

    # a = cov_Ip^T @ inv_Sigma, one output channel at a time — equivalent to
    # the original torch.einsum("bichw,bijhw->bjchw", cov_Ip, inv_sigma).
    a_r = cov_Ip_r * inv_var_I_rr + cov_Ip_g * inv_var_I_rg + cov_Ip_b * inv_var_I_rb
    a_g = cov_Ip_r * inv_var_I_rg + cov_Ip_g * inv_var_I_gg + cov_Ip_b * inv_var_I_gb
    a_b = cov_Ip_r * inv_var_I_rb + cov_Ip_g * inv_var_I_gb + cov_Ip_b * inv_var_I_bb
    del cov_Ip_r, cov_Ip_g, cov_Ip_b
    del inv_var_I_rr, inv_var_I_rg, inv_var_I_rb, inv_var_I_gg, inv_var_I_gb, inv_var_I_bb

    b = mean_p - a_r * mean_I_r - a_g * mean_I_g - a_b * mean_I_b
    del mean_p

    mean_a_r = boxfilter2d(a_r, radius) / N
    del a_r
    mean_a_g = boxfilter2d(a_g, radius) / N
    del a_g
    mean_a_b = boxfilter2d(a_b, radius) / N
    del a_b
    mean_b = boxfilter2d(b, radius) / N
    del b, N

    if scale is not None and scale > 1:
        guide = full_res_guide
        mean_a_r = F.interpolate(mean_a_r, guide.shape[-2:], mode='bilinear')
        mean_a_g = F.interpolate(mean_a_g, guide.shape[-2:], mode='bilinear')
        mean_a_b = F.interpolate(mean_a_b, guide.shape[-2:], mode='bilinear')
        mean_b = F.interpolate(mean_b, guide.shape[-2:], mode='bilinear')
        guide_r, guide_g, guide_b = torch.chunk(guide, 3, 1)

    q = mean_a_r * guide_r + mean_a_g * guide_g + mean_a_b * guide_b + mean_b
    return q


def guidedfilter2d_gray(guide, src, radius, eps, scale=None):
    """guided filter for a gray scale guide image

    Parameters
    -----
    guide: (B, 1, H, W)-dim torch.Tensor
        guide image
    src: (B, C, H, W)-dim torch.Tensor
        filtering image
    radius: int
        filter radius
    eps: float
        regularization coefficient
    """
    if guide.ndim == 3:
        guide = guide[:, None]
    if src.ndim == 3:
        src = src[:, None]

    full_res_guide = None
    if scale is not None and scale > 1:
        full_res_guide = guide
        src = F.interpolate(src, scale_factor=1. / scale, mode="nearest")
        guide = F.interpolate(guide, scale_factor=1. / scale, mode="nearest")
        radius = max(1, radius // scale)

    ones = torch.ones_like(guide)
    N = boxfilter2d(ones, radius)
    del ones

    mean_I = boxfilter2d(guide, radius) / N
    mean_p = boxfilter2d(src, radius) / N
    mean_Ip = boxfilter2d(guide * src, radius) / N
    cov_Ip = mean_Ip - mean_I * mean_p
    del mean_Ip

    mean_II = boxfilter2d(guide * guide, radius) / N
    var_I = mean_II - mean_I * mean_I
    del mean_II

    a = cov_Ip / (var_I + eps)
    del cov_Ip, var_I
    b = mean_p - a * mean_I
    del mean_p, mean_I

    mean_a = boxfilter2d(a, radius) / N
    del a
    mean_b = boxfilter2d(b, radius) / N
    del b, N

    if scale is not None and scale > 1:
        guide = full_res_guide
        mean_a = F.interpolate(mean_a, guide.shape[-2:], mode='bilinear')
        mean_b = F.interpolate(mean_b, guide.shape[-2:], mode='bilinear')

    q = mean_a * guide + mean_b
    return q
