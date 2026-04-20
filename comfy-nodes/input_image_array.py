"""
ShellAgent Plugin - Input Image Array Node

接收符合 ShellAgent 标准的图片数组输入：
    {
        "type": "array",
        "items": {"type": "string", "url_type": "image"}
    }

每个 item 可以是: URL / 本地路径 / base64 data URI
节点把数组拆开，展开成:
  - IMAGE (batch): torch.Tensor [N, H, W, C]  (会 resize 到第一张的尺寸)
  - IMAGE_LIST: list[Tensor]  (保留每张原尺寸，配合支持 list 的下游节点)
  - MASK: 对应的 alpha mask batch
  - COUNT: 数量
"""
import os
import json
import base64
import uuid
from io import BytesIO

import numpy as np
import torch
import requests
from PIL import Image, ImageOps, ImageSequence
import PIL
import cv2
from pillow_heif import register_heif_opener

import folder_paths
import node_helpers

register_heif_opener()


# ---------- helpers ----------

def _safe_open_image(image_bytes):
    """PIL 打不开就 fallback 到 OpenCV。"""
    try:
        return Image.open(BytesIO(image_bytes))
    except PIL.UnidentifiedImageError:
        arr = np.frombuffer(image_bytes, np.uint8)
        cv_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if cv_img is None:
            raise ValueError("Image cannot be identified by PIL or OpenCV")
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)


def _load_one(item):
    """把一个 item（URL/路径/base64/dict）加载为 PIL Image。"""
    # dict 兼容: {"url": "..."} 或 {"image": "..."} 或 {"path": "..."}
    if isinstance(item, dict):
        item = (
            item.get("url")
            or item.get("image")
            or item.get("path")
            or item.get("value")
            or ""
        )

    if not isinstance(item, str) or item == "":
        raise ValueError(f"Invalid image item: {item!r}")

    # URL
    if item.startswith(("http://", "https://")):
        resp = requests.get(item, timeout=30)
        resp.raise_for_status()
        return _safe_open_image(resp.content)

    # base64 data URI
    if item.startswith("data:image/"):
        b64 = item[item.find(",") + 1:]
        return Image.open(BytesIO(base64.b64decode(b64)))

    # 本地路径（绝对或相对 input_dir）
    path = item
    if not os.path.isfile(path):
        path = os.path.join(folder_paths.get_input_directory(), item)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Image not found: {item}")
    return node_helpers.pillow(Image.open, path)


def _pil_to_tensor(img):
    """PIL -> (image_tensor[1,H,W,C], mask_tensor[1,H,W])"""
    img = node_helpers.pillow(ImageOps.exif_transpose, img)
    if img.mode == "I":
        img = img.point(lambda i: i * (1 / 255))

    rgb = img.convert("RGB")
    arr = np.array(rgb).astype(np.float32) / 255.0
    image = torch.from_numpy(arr)[None,]

    if "A" in img.getbands():
        a = np.array(img.getchannel("A")).astype(np.float32) / 255.0
        mask = 1.0 - torch.from_numpy(a)
    else:
        mask = torch.zeros((rgb.size[1], rgb.size[0]), dtype=torch.float32)
    return image, mask.unsqueeze(0)


def _parse_array(raw):
    """把输入字符串解析为 list。支持 JSON / 换行分隔 / 单个字符串。"""
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, str):
        raise ValueError(f"Unsupported input type: {type(raw)}")

    s = raw.strip()
    if not s:
        return []

    # 尝试 JSON
    if s.startswith("[") or s.startswith("{"):
        try:
            data = json.loads(s)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                # 兼容 {"items": [...]} / {"images": [...]}
                for k in ("items", "images", "data", "value"):
                    if k in data and isinstance(data[k], list):
                        return data[k]
                return [data]
        except json.JSONDecodeError:
            pass

    # 换行/逗号分隔
    if "\n" in s:
        return [x.strip() for x in s.splitlines() if x.strip()]
    if "," in s and "://" not in s.split(",", 1)[0]:
        # 避免把单个 URL 里的 , 拆掉
        return [x.strip() for x in s.split(",") if x.strip()]

    return [s]


# ---------- node ----------

class ShellAgentPluginInputImageArray:
    """接收 ShellAgent array 结构的图片输入，拆开成 batch / list。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_name": (
                    "STRING",
                    {"multiline": False, "default": "input_images", "forceInput": False},
                ),
                "default_value": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "[]",
                        "placeholder": '["https://example.com/a.png", "https://example.com/b.png"]',
                        "forceInput": False,
                    },
                ),
            },
            "optional": {
                "description": (
                    "STRING",
                    {"multiline": False, "default": "", "forceInput": False},
                ),
                "resize_mode": (
                    ["pad_to_first", "resize_to_first", "none_keep_list_only"],
                    {"default": "resize_to_first"},
                ),
                "min_items": (
                    "INT",
                    {"default": 0, "min": 0, "max": 1024, "step": 1},
                ),
                "max_items": (
                    "INT",
                    {"default": 0, "min": 0, "max": 1024, "step": 1,
                     "tooltip": "0 = unlimited"},
                ),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE", "INT")
    RETURN_NAMES = ("images_batch", "masks_batch", "images_list", "count")
    OUTPUT_IS_LIST = (False, False, True, False)

    FUNCTION = "run"
    CATEGORY = "shellagent"

    # ShellAgent schema: array of images
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["input_name"],
            "type": "array",
            "items": {
                "type": "string",
                "url_type": "image",
            },
            "description": kwargs.get("description", ""),
        }
        min_items = kwargs.get("min_items") or 0
        max_items = kwargs.get("max_items") or 0
        if min_items > 0:
            schema["minItems"] = min_items
        if max_items > 0:
            schema["maxItems"] = max_items
        return schema

    @classmethod
    def VALIDATE_INPUTS(cls, input_name, default_value, **kwargs):
        # 只做轻量校验，真正加载在 run 时；空数组允许（留给运行时填充）
        if default_value is None:
            return "default_value is None"
        try:
            _parse_array(default_value)
        except Exception as e:  # noqa: BLE001
            return f"Invalid array input: {e}"
        return True

    def run(self, input_name, default_value="[]", description="",
            resize_mode="resize_to_first", min_items=0, max_items=0):
        items = _parse_array(default_value)

        if max_items and len(items) > max_items:
            items = items[:max_items]
        if min_items and len(items) < min_items:
            raise ValueError(
                f"Image array has {len(items)} items, need at least {min_items}"
            )

        if not items:
            # 返回一张 1x1 黑图避免下游崩溃
            blank = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
            blank_mask = torch.zeros((1, 1, 1), dtype=torch.float32)
            return (blank, blank_mask, [blank], 0)

        images_list = []
        masks_list = []

        for idx, it in enumerate(items):
            try:
                pil = _load_one(it)
            except Exception as e:  # noqa: BLE001
                raise RuntimeError(f"Failed to load image[{idx}]: {e}") from e

            # 多帧图（gif/tiff）只取第一帧，保持"一个 item 一张图"语义
            try:
                frames = list(ImageSequence.Iterator(pil))
                pil = frames[0]
            except Exception:  # noqa: BLE001
                pass

            img_t, mask_t = _pil_to_tensor(pil)
            images_list.append(img_t)
            masks_list.append(mask_t)

        # ---- list 输出（原尺寸，每张独立） ----
        list_output = [t for t in images_list]

        # ---- batch 输出（要求统一尺寸） ----
        if resize_mode == "none_keep_list_only":
            # 不做 batch，只保留 list。返回第一张当占位
            batch = images_list[0]
            batch_mask = masks_list[0]
        else:
            target_h, target_w = images_list[0].shape[1], images_list[0].shape[2]
            unified_imgs = []
            unified_masks = []
            for img_t, mask_t in zip(images_list, masks_list):
                h, w = img_t.shape[1], img_t.shape[2]
                if h == target_h and w == target_w:
                    unified_imgs.append(img_t)
                    unified_masks.append(mask_t)
                    continue

                if resize_mode == "resize_to_first":
                    # 双线性 resize: [1,H,W,C] -> [1,C,H,W] -> resize -> 回来
                    chw = img_t.permute(0, 3, 1, 2)
                    chw = torch.nn.functional.interpolate(
                        chw, size=(target_h, target_w),
                        mode="bilinear", align_corners=False,
                    )
                    unified_imgs.append(chw.permute(0, 2, 3, 1))

                    m = mask_t.unsqueeze(1)  # [1,1,H,W]
                    m = torch.nn.functional.interpolate(
                        m, size=(target_h, target_w),
                        mode="bilinear", align_corners=False,
                    )
                    unified_masks.append(m.squeeze(1))
                else:  # pad_to_first
                    canvas = torch.zeros((1, target_h, target_w, 3), dtype=torch.float32)
                    ch = min(h, target_h)
                    cw = min(w, target_w)
                    canvas[:, :ch, :cw, :] = img_t[:, :ch, :cw, :]
                    unified_imgs.append(canvas)

                    mcanvas = torch.zeros((1, target_h, target_w), dtype=torch.float32)
                    mcanvas[:, :ch, :cw] = mask_t[:, :ch, :cw]
                    unified_masks.append(mcanvas)

            batch = torch.cat(unified_imgs, dim=0)
            batch_mask = torch.cat(unified_masks, dim=0)

        return (batch, batch_mask, list_output, len(items))


NODE_CLASS_MAPPINGS = {
    "ShellAgentPluginInputImageArray": ShellAgentPluginInputImageArray,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ShellAgentPluginInputImageArray": "Input Image Array (ShellAgent Plugin)",
}
