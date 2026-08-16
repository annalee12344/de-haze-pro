import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
import numpy as np
import sys
from GuideFilter.guided_filter import GuidedFilter2d, FastGuidedFilter2d


# Dark Channel Prior
class DarkChannelPrior(nn.Module):
    def __init__(
        self,
        kernel_size,
        top_candidates_ratio,
        omega,
        radius,
        eps,
        open_threshold=True,
        depth_est=False,
        # --- memory-only knobs, algorithm is unchanged when left at defaults ---
        # Above this many pixels, the guided filter is run on a downsampled
        # copy of the image (see guided_filter.py's `scale` parameter) to
        # bound its memory use. Set to None to always run at full resolution
        # (the original exact behaviour).
        guided_filter_subsample_thresholds=((3_000_000, 4), (1_000_000, 2)),
    ):
        super().__init__()

        # dark channel prior
        self.kernel_size = kernel_size
        self.pad = nn.ReflectionPad2d(padding=kernel_size // 2)

        # airlight estimation
        self.top_candidates_ratio = top_candidates_ratio
        self.open_threshold = open_threshold

        # raw transmission estimation
        self.omega = omega

        # image guided filtering
        self.radius = radius
        self.eps = eps
        self.guide_filter = GuidedFilter2d(
            radius=self.radius,
            eps=self.eps
        )
        self.guided_filter_subsample_thresholds = guided_filter_subsample_thresholds

        self.depth_est = depth_est

    def _guided_filter_scale(self, h, w):
        """Pick a subsampling factor for the guided filter based on image
        size. Returns None (exact, full-resolution) for images below the
        smallest threshold."""
        if not self.guided_filter_subsample_thresholds:
            return None
        num_pixels = h * w
        for pixel_threshold, scale in self.guided_filter_subsample_thresholds:
            if num_pixels > pixel_threshold:
                return scale
        return None

    def forward(self, image):

        # compute dark channel prior
        b, c, h, w = image.shape

        # Minimum across RGB channels first
        channel_min = torch.min(
            image,
            dim=1,
            keepdim=True
        ).values

        # Local minimum over kernel_size x kernel_size
        channel_min_pad = self.pad(channel_min)
        del channel_min

        dc = -F.max_pool2d(
            -channel_min_pad,
            kernel_size=self.kernel_size,
            stride=1,
            padding=0
        )
        del channel_min_pad

        dc_vis = dc

        # airlight estimation
        top_candidates_nums = max(
            1,
            int(h * w * self.top_candidates_ratio)
        )

        dc_flat = dc.view(b, 1, -1)

        # torch.topk only needs to find the top-k values instead of fully
        # sorting every pixel (torch.argsort) and does not need to allocate
        # a same-size negated copy of `dc` (`-dc`) or a same-size index
        # tensor the way argsort does. top_candidates_ratio is tiny
        # (e.g. 1e-4), so this is both faster and far lighter on memory.
        # sorted=False is fine: only the max over the candidate set matters
        # below, not their relative order.
        _, searchidx = torch.topk(
            dc_flat,
            k=top_candidates_nums,
            dim=-1,
            largest=True,
            sorted=False,
        )
        del dc_flat

        # `expand` is a zero-copy view (dim 1 has size 1), unlike `.repeat`
        # which allocates a real (b, 3, k) copy. Safe here because the
        # result is only read from (via gather), never written to.
        searchidx = searchidx.expand(-1, 3, -1)

        image_ravel = image.view(b, 3, -1)

        value = torch.gather(
            image_ravel,
            dim=2,
            index=searchidx
        )
        del searchidx, image_ravel

        airlight, _ = torch.max(
            value,
            dim=-1,
            keepdim=True
        )
        del value

        airlight = airlight.squeeze(-1)

        if self.open_threshold:
            airlight = torch.clamp(
                airlight,
                max=220
            )

        # get raw transmission
        airlight = airlight.unsqueeze(-1).unsqueeze(-1)

        processed = image / airlight

        processed_channel_min = torch.min(
            processed,
            dim=1,
            keepdim=True
        ).values
        del processed

        processed_channel_min_pad = self.pad(
            processed_channel_min
        )
        del processed_channel_min

        dc_processed = -F.max_pool2d(
            -processed_channel_min_pad,
            kernel_size=self.kernel_size,
            stride=1,
            padding=0
        )
        del processed_channel_min_pad

        raw_t = 1.0 - self.omega * dc_processed
        del dc_processed

        if self.open_threshold:
            raw_t = torch.clamp(
                raw_t,
                min=0.2
            )

        # raw transmission guided filtering
        normalized_img = simple_image_normalization(image)

        gf_scale = self._guided_filter_scale(h, w)
        refined_transmission = self.guide_filter(
            raw_t,
            normalized_img,
            scale=gf_scale,
        )
        del normalized_img

        # recover image
        # NOTE: `.float()` returns the SAME tensor object (no copy) when
        # `image` is already float32, which it always is coming from
        # inference.py. We then do the airlight-recovery arithmetic
        # in-place on that buffer instead of allocating three new
        # full-resolution tensors for `-`, `/`, `+`. This is safe because
        # `image` is not read again after this point, and the caller
        # (inference.py) does not reuse its input tensor after calling the
        # model. This is an exact reformulation, not an approximation.
        image = image.float()
        image.sub_(airlight)
        image.div_(refined_transmission)
        image.add_(airlight)
        dehaze_images = image

        if self.depth_est:
            depth = recover_depth(refined_transmission)

            return (
                dehaze_images,
                dc_vis,
                airlight,
                raw_t,
                refined_transmission,
                depth
            )

        return (
            dehaze_images,
            dc_vis,
            airlight,
            raw_t,
            refined_transmission
        )


def simple_image_normalization(tensor):
    b, c, h, w = tensor.shape

    tensor_ravel = tensor.view(b, 3, -1)

    image_min, _ = torch.min(
        tensor_ravel,
        dim=-1,
        keepdim=True
    )

    image_max, _ = torch.max(
        tensor_ravel,
        dim=-1,
        keepdim=True
    )

    image_min = image_min.unsqueeze(-1)
    image_max = image_max.unsqueeze(-1)

    normalized_image = (
        (tensor - image_min)
        / (image_max - image_min)
    )

    return normalized_image


def recover_depth(transmission, beta=0.001):
    negative_depth = torch.log(transmission)
    return (-negative_depth) / beta
