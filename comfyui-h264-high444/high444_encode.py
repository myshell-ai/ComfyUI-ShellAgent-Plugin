import os
import shutil
import subprocess
import tempfile
from typing import Tuple, Optional

from PIL import Image

try:
    import torch
except Exception:
    torch = None


def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


def _normalize_path(p: str) -> str:
    # ComfyUI works fine with forward slashes on Windows too
    return (p or "").strip().replace("\\", "/")


def _which(exe: str) -> Optional[str]:
    """Cross-platform shutil.which wrapper."""
    import shutil as _shutil
    return _shutil.which(exe)


def _auto_find_ffmpeg(user_value: str) -> str:
    """
    If user_value is provided and exists/works -> use it.
    Else try PATH and a few common install locations.
    """
    user_value = (user_value or "").strip()
    if user_value:
        # If it's a path to an exe
        if os.path.exists(user_value):
            return user_value
        # If it's a command in PATH
        w = _which(user_value)
        if w:
            return w

    # Try standard name in PATH
    w = _which("ffmpeg")
    if w:
        return w

    # Common Windows locations
    candidates = [
        r"C:/ffmpeg/bin/ffmpeg.exe",
        r"C:/Program Files/ffmpeg/bin/ffmpeg.exe",
        r"C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe",
        os.path.expandvars(r"%USERPROFILE%/ffmpeg/bin/ffmpeg.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%/Programs/ffmpeg/bin/ffmpeg.exe"),
        os.path.expandvars(r"%ProgramData%/chocolatey/bin/ffmpeg.exe"),
        os.path.expandvars(r"%ChocolateyInstall%/bin/ffmpeg.exe"),
    ]
    for c in candidates:
        c = _normalize_path(c)
        if c and os.path.exists(c):
            return c

    # Linux/mac common
    for c in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]:
        if os.path.exists(c):
            return c

    raise RuntimeError(
        "FFmpeg not found. Install ffmpeg and ensure it's in PATH, "
        "or set ffmpeg_path to the full executable path (e.g. C:/ffmpeg/bin/ffmpeg.exe)."
    )


def _run(cmd: list, env: Optional[dict] = None) -> Tuple[int, str]:
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        universal_newlines=True,
        bufsize=1,
    )
    out_lines = []
    for line in p.stdout:
        out_lines.append(line)
    p.wait()
    return p.returncode, "".join(out_lines)


def _write_png_frames(images, out_dir: str, prefix: str = "frame_", start_index: int = 0) -> int:
    """
    images: torch tensor [N,H,W,C] float32 0..1 (typical ComfyUI IMAGE)
    Writes PNG frames to out_dir, returns number of frames written.
    """
    _ensure_dir(out_dir)

    if torch is None:
        raise RuntimeError("torch not available in this environment (ComfyUI should have torch).")

    if not isinstance(images, torch.Tensor):
        raise TypeError("images must be a torch.Tensor (ComfyUI IMAGE)")

    if images.dim() != 4 or images.shape[-1] != 3:
        raise ValueError(f"Expected IMAGE with shape [N,H,W,3], got {tuple(images.shape)}")

    n = images.shape[0]
    imgs = torch.clamp(images, 0.0, 1.0).mul(255.0).round().byte().cpu().numpy()  # [N,H,W,3] uint8

    for i in range(n):
        im = Image.fromarray(imgs[i], mode="RGB")
        fn = os.path.join(out_dir, f"{prefix}{start_index + i:05d}.png")
        im.save(fn, format="PNG", compress_level=0)

    return n


def _try_ffprobe_verify(ffprobe_path: str, video_path: str) -> str:
    """
    Best-effort verification. Returns a short text summary or empty string.
    """
    ffprobe_path = (ffprobe_path or "").strip()
    if not ffprobe_path:
        # try auto
        fp = _which("ffprobe")
        if not fp:
            return ""
        ffprobe_path = fp
    else:
        if os.path.exists(ffprobe_path):
            pass
        else:
            fp = _which(ffprobe_path)
            if not fp:
                return ""
            ffprobe_path = fp

    cmd = [
        ffprobe_path,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,profile,pix_fmt",
        "-of", "default=nk=1:nw=1",
        video_path
    ]
    rc, out = _run(cmd)
    if rc != 0:
        return ""
    return out.strip()


class High444H264Encode:
    """
    Encode a ComfyUI IMAGE batch to H.264 High 4:4:4 Predictive via FFmpeg/libx264.
    - Forces: profile=high444, pix_fmt=yuv444p (or yuv444p10le)
    - Adds: explicit color metadata to reduce colorspace/range surprises
    - Supports: optional audio mux, tune, x264-params, bitrate, and debug frame retention
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "fps": ("INT", {"default": 30, "min": 1, "max": 240, "step": 1}),

                # If you keep it relative, it's relative to ComfyUI repo root.
                "output_path": ("STRING", {"default": "output/high444.mp4"}),

                "crf": ("INT", {"default": 16, "min": 0, "max": 51, "step": 1}),
                "preset": (
                    ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                    {"default": "slow"},
                ),
                "tune": (["none", "film", "animation", "grain", "stillimage", "fastdecode", "zerolatency"], {"default": "none"}),

                "pix_fmt": (["yuv444p", "yuv444p10le"], {"default": "yuv444p"}),

                # Metadata only (doesn't magically convert your content),
                # but helps avoid player/website guessing wrong.
                "colorspace": (["bt709", "bt601", "bt2020nc"], {"default": "bt709"}),
                "color_range": (["pc", "tv"], {"default": "pc"}),

                # Optional mux audio track (path to e.g. .wav/.mp3/.m4a)
                "audio_path": ("STRING", {"default": ""}),

                # Leave blank to auto-find; or set full path to ffmpeg exe
                "ffmpeg_path": ("STRING", {"default": ""}),

                # Advanced x264 params (leave blank unless you know what you want)
                # e.g. "aq-mode=3:aq-strength=0.8:deblock=-1,-1"
                "x264_params": ("STRING", {"default": ""}),

                # Optional VBR/CBR cap (kbps). 0 disables.
                "video_bitrate_kbps": ("INT", {"default": 0, "min": 0, "max": 200000, "step": 50}),

                # Keep PNG frames for debugging
                "keep_frames": ("BOOLEAN", {"default": False}),

                # Verify output (best-effort via ffprobe if available)
                "verify_with_ffprobe": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "filename_prefix": ("STRING", {"default": "frame_"}),
                "ffprobe_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video_path", "log")
    FUNCTION = "encode"
    CATEGORY = "video/encode"

    def encode(
        self,
        images,
        fps: int,
        output_path: str,
        crf: int,
        preset: str,
        tune: str,
        pix_fmt: str,
        colorspace: str,
        color_range: str,
        audio_path: str,
        ffmpeg_path: str,
        x264_params: str,
        video_bitrate_kbps: int,
        keep_frames: bool,
        verify_with_ffprobe: bool,
        filename_prefix: str = "frame_",
        ffprobe_path: str = "",
    ) -> Tuple[str, str]:

        fps = _safe_int(fps, 30)
        crf = _safe_int(crf, 16)
        video_bitrate_kbps = _safe_int(video_bitrate_kbps, 0)

        output_path = _normalize_path(output_path)
        if not output_path:
            output_path = "output/high444.mp4"

        out_dir = os.path.dirname(output_path)
        if out_dir:
            _ensure_dir(out_dir)

        ffmpeg = _auto_find_ffmpeg(ffmpeg_path)

        temp_root = tempfile.mkdtemp(prefix="comfyui_high444_")
        frames_dir = os.path.join(temp_root, "frames")
        _ensure_dir(frames_dir)

        try:
            _write_png_frames(images, frames_dir, prefix=filename_prefix)

            pattern = _normalize_path(os.path.join(frames_dir, f"{filename_prefix}%05d.png"))

            profile = "high444"

            cmd = [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel", "info",
                "-framerate", str(fps),
                "-i", pattern,
            ]

            audio_path = _normalize_path(audio_path)
            if audio_path:
                cmd += ["-i", audio_path, "-shortest"]

            # Video encoder core
            cmd += [
                "-c:v", "libx264",
                "-profile:v", profile,
                "-pix_fmt", pix_fmt,
                "-crf", str(crf),
                "-preset", preset,
            ]

            # Tune (optional)
            if tune and tune != "none":
                cmd += ["-tune", tune]

            # Bitrate cap (optional)
            if video_bitrate_kbps > 0:
                cmd += ["-b:v", f"{video_bitrate_kbps}k"]

            # Color metadata
            cmd += [
                "-color_range", color_range,     # pc(full) or tv(limited)
                "-colorspace", colorspace,        # bt709/bt601/bt2020nc
                "-color_primaries", colorspace,
                "-color_trc", colorspace,
            ]

            # Advanced x264 params
            x264_params = (x264_params or "").strip()
            if x264_params:
                cmd += ["-x264-params", x264_params]

            # Audio codec if muxing audio
            if audio_path:
                cmd += ["-c:a", "aac", "-b:a", "192k"]

            # MP4 faststart
            cmd += ["-movflags", "+faststart", output_path]

            rc, log = _run(cmd)

            if rc != 0:
                raise RuntimeError(
                    "FFmpeg failed.\n"
                    f"Command: {' '.join(cmd)}\n"
                    f"Return code: {rc}\n"
                    f"Log:\n{log}"
                )

            # Optional verification
            verify_text = ""
            if verify_with_ffprobe:
                verify_text = _try_ffprobe_verify(ffprobe_path, output_path)
                if verify_text:
                    log += "\n\n[ffprobe verify]\n" + verify_text + "\n"

            return output_path, log

        finally:
            if keep_frames:
                debug_dir = output_path + ".frames"
                try:
                    if os.path.exists(debug_dir):
                        shutil.rmtree(debug_dir)
                    shutil.move(temp_root, debug_dir)
                except Exception:
                    # ignore cleanup errors
                    pass
            else:
                shutil.rmtree(temp_root, ignore_errors=True)
