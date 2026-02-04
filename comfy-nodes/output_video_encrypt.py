import folder_paths
import os
import json
import subprocess
import numpy as np
import re
import shutil
import datetime
import itertools
import torch
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from comfy.utils import ProgressBar

# Fixed encryption key - use the same key for decryption
ENCRYPTION_KEY = b"ShellAgentSecretKey2024!"


def xor_encrypt_file(filepath, key):
    """
    Fast XOR encryption using NumPy vectorization.
    Completely corrupts the file so it cannot be viewed directly.
    To decrypt, simply call this function again with the same key.
    """
    with open(filepath, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    
    # Create repeated key array matching data length
    key_array = np.frombuffer(key * ((len(data) // len(key)) + 1), dtype=np.uint8)[:len(data)]
    
    # Vectorized XOR - 50-100x faster than Python loop
    encrypted = np.bitwise_xor(data, key_array)
    
    with open(filepath, 'wb') as f:
        f.write(encrypted.tobytes())


def xor_decrypt_file(filepath, key):
    """
    Decrypt a file encrypted with xor_encrypt_file.
    XOR encryption is symmetric, so decryption is the same as encryption.
    """
    xor_encrypt_file(filepath, key)


def tensor_to_bytes(tensor):
    """Convert tensor to uint8 bytes"""
    tensor = tensor.cpu().numpy() * 255
    return np.clip(tensor, 0, 255).astype(np.uint8)


def find_ffmpeg():
    """Find ffmpeg executable path."""
    # Try to find ffmpeg in PATH
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    
    # Try common locations
    common_paths = [
        os.path.join(os.path.dirname(__file__), "ffmpeg"),
        os.path.join(os.path.dirname(__file__), "ffmpeg.exe"),
        os.path.join(folder_paths.base_path, "ffmpeg"),
        os.path.join(folder_paths.base_path, "ffmpeg.exe"),
        "C:/ffmpeg/bin/ffmpeg.exe",
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]
    
    for path in common_paths:
        if os.path.isfile(path):
            return path
    
    # Try imageio-ffmpeg as fallback
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    
    return None


# Find ffmpeg at module load
FFMPEG_PATH = find_ffmpeg()


# Video format configurations
VIDEO_FORMATS = {
    "h264-mp4": {
        "extension": "mp4",
        "main_pass": ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"],
        "dim_alignment": 2,
        "description": "H.264 MP4 - Mac/iOS兼容 ✅ 推荐日常使用",
        "compatible": True,  # Mac兼容标记
    },
    "h265-mp4": {
        "extension": "mp4",
        "main_pass": ["-c:v", "libx265", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-tag:v", "hvc1"],
        "dim_alignment": 2,
        "description": "H.265/HEVC MP4 - 更好的压缩率",
        "compatible": True,
    },
    "vp9-webm": {
        "extension": "webm",
        "main_pass": ["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-pix_fmt", "yuv420p"],
        "dim_alignment": 2,
        "description": "VP9 WebM - 网页友好",
        "compatible": True,
    },
    "avi": {
        "extension": "avi",
        "main_pass": ["-c:v", "mjpeg", "-q:v", "3", "-pix_fmt", "yuvj420p"],
        "dim_alignment": 2,
        "description": "Motion JPEG AVI - 旧格式",
        "compatible": True,
    },
    "mov": {
        "extension": "mov",
        "main_pass": ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"],
        "dim_alignment": 2,
        "description": "QuickTime MOV - Mac原生格式",
        "compatible": True,
    },
    # 新增: 高级H.264格式 - 允许自定义参数
    "h264-advanced": {
        "extension": "mp4",
        "main_pass": [],  # 将由用户参数填充
        "dim_alignment": 2,
        "description": "H.264 高级模式 - 可自定义参数 ⚙️",
        "advanced": True,  # 标记为高级模式
        "compatible": "depends",  # 取决于用户选择的pix_fmt
    },
    # 新增: H.264 High 4:4:4 专业格式 (yuv444p)
    "h264-high444": {
        "extension": "mp4",
        "main_pass": ["-c:v", "libx264", "-profile:v", "high444", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv444p"],
        "dim_alignment": 2,
        "description": "H.264 High444 - 专业后期 ⚠️ Mac不兼容",
        "compatible": False,  # Mac不兼容
        "professional": True,
    },
    # 新增: FFmpeg手动模式 - 完全自定义
    "ffmpeg-manual": {
        "extension": "mp4",
        "main_pass": [],  # 完全由用户参数填充
        "dim_alignment": 2,
        "description": "FFmpeg 手动模式 - 专家级自定义 🔧",
        "manual": True,  # 标记为手动模式
        "compatible": "depends",
    },
}


def get_format_list():
    """Get list of available formats for the dropdown."""
    formats = ["image/gif", "image/webp"]
    for fmt in VIDEO_FORMATS.keys():
        formats.append(f"video/{fmt}")
    return formats


class ShellAgentVideoCombineEncrypt:
    """
    Video combine node with encryption support.
    Combines images into video and encrypts the output files.
    The encrypted files cannot be played or viewed directly.
    
    Supports: GIF, WebP, MP4 (H.264/H.265), WebM (VP9), AVI, MOV
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "frame_rate": ("FLOAT", {"default": 24, "min": 1, "max": 120, "step": 1}),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1, "tooltip": "循环次数。0 = GIF/WebP无限循环"}),
                "filename_prefix": ("STRING", {"default": "ShellAgent_Encrypted"}),
                "format": (get_format_list(),),
                "quality": ("INT", {"default": 85, "min": 1, "max": 100, "step": 1, "tooltip": "质量等级 (越高质量越好,文件越大)"}),
                "pingpong": ("BOOLEAN", {"default": False, "tooltip": "反转并追加帧以实现无缝循环"}),
                "encrypt": ("BOOLEAN", {"default": True, "tooltip": "如果启用,输出文件将被加密,无法直接查看"}),
            },
            "optional": {
                "audio": ("AUDIO", {"tooltip": "可选音频,与视频混流"}),
                "vae": ("VAE", {"tooltip": "可选VAE,用于解码latent输入"}),
                # 高级参数 - 仅在选择高级格式时使用
                "advanced_preset": (
                    ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                    {"default": "medium", "tooltip": "编码速度预设 (越慢质量越好)"}
                ),
                "advanced_tune": (
                    ["none", "film", "animation", "grain", "stillimage", "fastdecode", "zerolatency"],
                    {"default": "none", "tooltip": "编码优化类型"}
                ),
                "advanced_crf": (
                    "INT",
                    {"default": 20, "min": 0, "max": 51, "step": 1, "tooltip": "质量控制 (0=无损, 20=推荐, 51=最差)"}
                ),
                "advanced_pix_fmt": (
                    ["yuv420p", "yuv444p", "yuv444p10le"],
                    {"default": "yuv420p", "tooltip": "像素格式 (yuv420p=Mac兼容, yuv444p=高质量但Mac不兼容)"}
                ),
                "advanced_colorspace": (
                    ["bt709", "bt601", "bt2020nc"],
                    {"default": "bt709", "tooltip": "色彩空间元数据"}
                ),
                "advanced_color_range": (
                    ["tv", "pc"],
                    {"default": "pc", "tooltip": "色彩范围 (tv=16-235, pc=0-255全范围)"}
                ),
                "advanced_x264_params": (
                    "STRING",
                    {"default": "", "tooltip": "高级x264参数,例如: aq-mode=3:aq-strength=0.8"}
                ),
                # 手动模式专用参数
                "manual_videocodec": (
                    "STRING",
                    {"default": "libx264", "tooltip": "手动模式: 视频编解码器"}
                ),
                "manual_audio_codec": (
                    "STRING",
                    {"default": "aac", "tooltip": "手动模式: 音频编解码器"}
                ),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("VHS_FILENAMES",)
    RETURN_NAMES = ("Filenames",)
    OUTPUT_NODE = True
    CATEGORY = "shellagent"
    FUNCTION = "combine_video"
    DESCRIPTION = "Combines images into video with optional encryption. Supports GIF, WebP, MP4, WebM, AVI, MOV. Encrypted files cannot be viewed directly."

    @classmethod
    def VALIDATE_INPUTS(cls, format, **kwargs):
        return True

    def _decode_latents_with_vae(self, latents, vae):
        """
        Decode latent tensors to images using VAE.
        Processes in batches to manage memory usage.
        """
        downscale_ratio = getattr(vae, "downscale_ratio", 8)
        width = latents.size(-1) * downscale_ratio
        height = latents.size(-2) * downscale_ratio

        # Calculate batch size based on resolution to avoid OOM
        frames_per_batch = max(1, (1920 * 1080 * 16) // (width * height))

        decoded_frames = []
        num_latents = latents.size(0)

        for i in range(0, num_latents, frames_per_batch):
            batch = latents[i:i + frames_per_batch]
            decoded_batch = vae.decode(batch)
            # VAE decode returns tensor, collect frames
            for frame in decoded_batch:
                # Handle extra dimensions
                while len(frame.shape) > 3:
                    frame = frame[0]
                decoded_frames.append(frame)

        # Stack all decoded frames
        return torch.stack(decoded_frames)

    def _mux_audio_with_video(self, video_path, audio, frame_rate, total_frames, video_format):
        """
        Mux audio with video file using ffmpeg.
        Returns the path to the new file with audio, or None if failed.
        """
        if FFMPEG_PATH is None:
            return None

        # Get audio waveform
        try:
            waveform = audio.get('waveform')
            if waveform is None:
                return None
            sample_rate = audio.get('sample_rate', 44100)
        except (AttributeError, TypeError):
            return None

        # Create output path with audio suffix
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}-audio{ext}"

        # Get audio channels
        channels = waveform.size(1)

        # Calculate minimum audio duration to match video
        min_audio_dur = total_frames / frame_rate + 1

        # Prepare audio data (convert from torch tensor to bytes)
        # Audio waveform shape: (1, channels, samples) -> need (samples, channels) for f32le format
        audio_data = waveform.squeeze(0).transpose(0, 1).numpy().tobytes()

        # Audio codec selection based on format
        audio_codec = ["-c:a", "aac", "-b:a", "192k"]  # Default to AAC
        if ext.lower() == ".webm":
            audio_codec = ["-c:a", "libopus", "-b:a", "128k"]
        elif ext.lower() == ".avi":
            audio_codec = ["-c:a", "mp3", "-b:a", "192k"]

        # Build ffmpeg command for muxing
        mux_args = [
            FFMPEG_PATH,
            "-v", "error",
            "-y",  # Overwrite output
            "-i", video_path,  # Input video
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-f", "f32le",
            "-i", "-",  # Input audio from stdin
            "-c:v", "copy",  # Copy video stream
        ] + audio_codec + [
            "-af", f"apad=whole_dur={min_audio_dur}",
            "-shortest",
            output_path
        ]

        try:
            result = subprocess.run(
                mux_args,
                input=audio_data,
                capture_output=True,
                check=True
            )
            return output_path
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8') if e.stderr else "Unknown error"
            print(f"Warning: Failed to mux audio: {error_msg}")
            return None
        except Exception as e:
            print(f"Warning: Failed to mux audio: {str(e)}")
            return None

    def combine_video(
        self,
        images,
        frame_rate: float,
        loop_count: int,
        filename_prefix="ShellAgent_Encrypted",
        format="image/gif",
        quality=85,
        pingpong=False,
        encrypt=True,
        prompt=None,
        extra_pnginfo=None,
        audio=None,
        vae=None,
        # 高级参数 (可选)
        advanced_preset="medium",
        advanced_tune="none",
        advanced_crf=20,
        advanced_pix_fmt="yuv420p",
        advanced_colorspace="bt709",
        advanced_color_range="pc",
        advanced_x264_params="",
        # 手动模式参数 (可选)
        manual_videocodec="libx264",
        manual_audio_codec="aac",
    ):
        if images is None or len(images) == 0:
            return ((True, []),)

        # Handle VAE decoding if vae is provided and images are latents
        if vae is not None:
            if isinstance(images, dict) and 'samples' in images:
                # images is actually latents, decode with VAE
                images = self._decode_latents_with_vae(images['samples'], vae)
            elif isinstance(images, torch.Tensor) and len(images.shape) == 4 and images.shape[1] in [4, 16]:
                # Looks like latent format (B, C, H, W) with typical latent channels
                images = self._decode_latents_with_vae(images, vae)

        # Ensure images is a tensor
        if isinstance(images, dict) and 'samples' in images:
            images = images['samples']

        if isinstance(images, torch.Tensor) and images.size(0) == 0:
            return ((True, []),)

        num_frames = len(images)
        pbar = ProgressBar(num_frames)
        first_image = images[0]
        
        # Get output directory
        output_dir = folder_paths.get_output_directory()
        (
            full_output_folder,
            filename,
            _,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path(filename_prefix, output_dir)
        
        output_files = []
        
        # Setup metadata
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))
        metadata.add_text("CreationTime", datetime.datetime.now().isoformat(" ")[:19])
        
        # Find next counter
        max_counter = 0
        matcher = re.compile(f"{re.escape(filename)}_(\\d+)\\D*\\..+", re.IGNORECASE)
        for existing_file in os.listdir(full_output_folder):
            match = matcher.fullmatch(existing_file)
            if match:
                file_counter = int(match.group(1))
                if file_counter > max_counter:
                    max_counter = file_counter
        counter = max_counter + 1
        
        # Save first frame as png to keep metadata
        png_file = f"{filename}_{counter:05}.png"
        png_path = os.path.join(full_output_folder, png_file)
        Image.fromarray(tensor_to_bytes(first_image)).save(
            png_path,
            pnginfo=metadata,
            compress_level=4,
        )
        output_files.append(png_path)
        
        # Handle pingpong - create reversed frames
        if pingpong:
            images_list = list(images)
            # Add reversed frames (excluding first and last to avoid duplicates)
            images = images_list + images_list[-2:0:-1]
            num_frames = len(images)
        
        format_type, format_ext = format.split("/")

        # Track the main output file for audio muxing
        video_file_path = None
        total_frames_output = num_frames
        video_format_config = None

        if format_type == "image":
            # Use PIL for gif/webp - audio not supported for image formats
            self._create_animated_image(
                images, full_output_folder, filename, counter,
                format_ext, frame_rate, loop_count, quality,
                output_files, pbar, num_frames
            )
        else:
            # Use ffmpeg for video formats
            video_file_path, total_frames_output, video_format_config = self._create_video(
                images, full_output_folder, filename, counter,
                format_ext, frame_rate, loop_count, quality,
                output_files, pbar, first_image,
                # 传递高级参数
                advanced_preset, advanced_tune, advanced_crf, advanced_pix_fmt,
                advanced_colorspace, advanced_color_range, advanced_x264_params,
                manual_videocodec
            )

            # Handle audio muxing for video formats
            if audio is not None and video_file_path is not None:
                # Check if audio has valid waveform
                audio_waveform = None
                try:
                    audio_waveform = audio.get('waveform') if isinstance(audio, dict) else None
                except (AttributeError, TypeError):
                    pass

                if audio_waveform is not None:
                    audio_output_path = self._mux_audio_with_video(
                        video_file_path,
                        audio,
                        frame_rate,
                        total_frames_output,
                        video_format_config
                    )
                    if audio_output_path is not None and os.path.exists(audio_output_path):
                        output_files.append(audio_output_path)

        # Encrypt all output files if encryption is enabled
        if encrypt:
            for filepath in output_files:
                if os.path.exists(filepath):
                    xor_encrypt_file(filepath, ENCRYPTION_KEY)
        
        # Return filenames in VHS format
        previews = [
            {
                "filename": os.path.basename(output_files[-1]),
                "subfolder": subfolder,
                "type": "output",
                "format": format,
                "frame_rate": frame_rate,
            }
        ]
        
        return {"ui": {"gifs": previews}, "result": ((True, output_files),)}

    def _create_animated_image(self, images, output_folder, filename, counter, 
                                format_ext, frame_rate, loop_count, quality,
                                output_files, pbar, num_frames):
        """Create animated GIF or WebP using PIL."""
        image_kwargs = {}
        
        if format_ext == "gif":
            image_kwargs['disposal'] = 2
            image_kwargs['optimize'] = False
        elif format_ext == "webp":
            image_kwargs['quality'] = quality
            image_kwargs['method'] = 4
        
        file = f"{filename}_{counter:05}.{format_ext}"
        file_path = os.path.join(output_folder, file)
        
        frames = []
        for img in images:
            frames.append(Image.fromarray(tensor_to_bytes(img)))
            pbar.update(1)
        
        frames[0].save(
            file_path,
            format=format_ext.upper(),
            save_all=True,
            append_images=frames[1:],
            duration=round(1000 / frame_rate),
            loop=loop_count,
            **image_kwargs
        )
        output_files.append(file_path)

    def _create_video(self, images, output_folder, filename, counter,
                      format_ext, frame_rate, loop_count, quality,
                      output_files, pbar, first_image,
                      advanced_preset="medium", advanced_tune="none", advanced_crf=20,
                      advanced_pix_fmt="yuv420p", advanced_colorspace="bt709",
                      advanced_color_range="pc", advanced_x264_params="",
                      manual_videocodec="libx264"):
        """
        Create video using ffmpeg.
        支持高级参数和手动模式。
        Returns tuple of (video_file_path, total_frames, video_format_dict).
        """
        if FFMPEG_PATH is None:
            raise ProcessLookupError(
                "ffmpeg is required for video outputs and could not be found.\n"
                "Please install ffmpeg:\n"
                "  - Windows: Download from https://ffmpeg.org/download.html\n"
                "  - Linux: sudo apt install ffmpeg\n"
                "  - Or install imageio-ffmpeg: pip install imageio-ffmpeg"
            )

        # Get format configuration
        video_format = VIDEO_FORMATS.get(format_ext, VIDEO_FORMATS["h264-mp4"])

        # ============ 处理高级模式和手动模式 ============
        is_advanced = video_format.get("advanced", False)
        is_manual = video_format.get("manual", False)
        is_high444 = video_format.get("professional", False)

        if is_advanced or is_manual:
            # 高级模式或手动模式: 使用用户提供的参数构建main_pass
            main_pass = [
                "-c:v", manual_videocodec if is_manual else "libx264",
                "-preset", advanced_preset,
                "-crf", str(advanced_crf),
                "-pix_fmt", advanced_pix_fmt,
            ]

            # 如果选择了yuv444p,需要指定profile
            if advanced_pix_fmt in ["yuv444p", "yuv444p10le"]:
                main_pass.insert(2, "-profile:v")
                main_pass.insert(3, "high444")

            # 添加tune参数(如果不是none)
            if advanced_tune and advanced_tune != "none":
                main_pass.extend(["-tune", advanced_tune])

            # 添加色彩空间元数据
            main_pass.extend([
                "-color_range", advanced_color_range,
                "-colorspace", advanced_colorspace,
                "-color_primaries", advanced_colorspace,
                "-color_trc", advanced_colorspace,
            ])

            # 添加x264高级参数(如果提供)
            if advanced_x264_params and advanced_x264_params.strip():
                main_pass.extend(["-x264-params", advanced_x264_params.strip()])

            # 添加faststart(MP4优化)
            if extension == "mp4":
                main_pass.extend(["-movflags", "+faststart"])

            # 更新video_format字典以便后续使用
            video_format = video_format.copy()
            video_format["main_pass"] = main_pass
        elif is_high444:
            # High444专业模式: 已经预配置好了,但可以调整CRF
            main_pass = video_format["main_pass"].copy()
            # 用户可能想调整质量
            if "-crf" in main_pass:
                crf_index = main_pass.index("-crf") + 1
                main_pass[crf_index] = str(advanced_crf) if advanced_crf != 20 else main_pass[crf_index]
        else:
            # 标准模式: 使用预设配置
            main_pass = video_format["main_pass"].copy()
        # ============ 高级模式处理结束 ============

        # Calculate dimensions with alignment
        height, width = first_image.shape[0], first_image.shape[1]
        dim_alignment = video_format.get("dim_alignment", 2)

        # Ensure dimensions are divisible by alignment
        aligned_width = ((width + dim_alignment - 1) // dim_alignment) * dim_alignment
        aligned_height = ((height + dim_alignment - 1) // dim_alignment) * dim_alignment

        dimensions = f"{aligned_width}x{aligned_height}"

        # Output file path
        extension = video_format.get("extension", "mp4")
        file = f"{filename}_{counter:05}.{extension}"
        file_path = os.path.join(output_folder, file)

        # 仅在标准模式下,根据quality参数调整CRF/质量值
        # 高级模式和手动模式使用用户明确指定的参数
        if not is_advanced and not is_manual:
            # Map quality (1-100) to CRF (51-0) for x264/x265, or to appropriate scale
            if "-crf" in main_pass:
                crf_index = main_pass.index("-crf") + 1
                # Quality 100 -> CRF 0, Quality 1 -> CRF 51
                crf_value = int(51 - (quality / 100 * 51))
                main_pass[crf_index] = str(crf_value)
            elif "-q:v" in main_pass:
                q_index = main_pass.index("-q:v") + 1
                # For MJPEG: quality 100 -> 1, quality 1 -> 31
                q_value = int(1 + ((100 - quality) / 100 * 30))
                main_pass[q_index] = str(q_value)

        # Build ffmpeg command
        args = [
            FFMPEG_PATH,
            "-v", "error",
            "-y",  # Overwrite output
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", dimensions,
            "-r", str(frame_rate),
            "-i", "-",  # Read from stdin
        ] + main_pass + [file_path]

        # Prepare frame data with padding if needed
        frame_data_list = []
        total_frames = 0
        for img in images:
            img_bytes = tensor_to_bytes(img)
            h, w = img_bytes.shape[:2]

            # Pad to aligned dimensions if necessary
            if h != aligned_height or w != aligned_width:
                padded = np.zeros((aligned_height, aligned_width, 3), dtype=np.uint8)
                padded[:h, :w] = img_bytes
                frame_data_list.append(padded.tobytes())
            else:
                frame_data_list.append(img_bytes.tobytes())
            pbar.update(1)
            total_frames += 1

        frame_data = b''.join(frame_data_list)

        # Run ffmpeg
        try:
            result = subprocess.run(
                args,
                input=frame_data,
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8') if e.stderr else "Unknown error"
            raise Exception(
                f"FFmpeg error:\n{error_msg}\n"
                f"Command: {' '.join(args)}"
            )
        except FileNotFoundError:
            raise ProcessLookupError(
                f"ffmpeg not found at: {FFMPEG_PATH}\n"
                "Please ensure ffmpeg is properly installed."
            )

        output_files.append(file_path)
        return file_path, total_frames, video_format


NODE_CLASS_MAPPINGS = {
    "ShellAgentPluginVideoCombineEncrypt": ShellAgentVideoCombineEncrypt,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ShellAgentPluginVideoCombineEncrypt": "Video Combine Encrypt (ShellAgent Plugin)",
}
