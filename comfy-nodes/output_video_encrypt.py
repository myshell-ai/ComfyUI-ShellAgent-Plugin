import folder_paths
import os
import json
import subprocess
import numpy as np
import re
import shutil
import datetime
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
        "main_pass": ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p"],
        "dim_alignment": 2,
        "description": "H.264 MP4 - Best compatibility",
    },
    "h265-mp4": {
        "extension": "mp4",
        "main_pass": ["-c:v", "libx265", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-tag:v", "hvc1"],
        "dim_alignment": 2,
        "description": "H.265/HEVC MP4 - Better compression",
    },
    "vp9-webm": {
        "extension": "webm",
        "main_pass": ["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-pix_fmt", "yuv420p"],
        "dim_alignment": 2,
        "description": "VP9 WebM - Web friendly",
    },
    "avi": {
        "extension": "avi",
        "main_pass": ["-c:v", "mjpeg", "-q:v", "3", "-pix_fmt", "yuvj420p"],
        "dim_alignment": 2,
        "description": "Motion JPEG AVI",
    },
    "mov": {
        "extension": "mov",
        "main_pass": ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p"],
        "dim_alignment": 2,
        "description": "QuickTime MOV",
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
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1, "tooltip": "Number of loops. 0 = infinite for GIF/WebP"}),
                "filename_prefix": ("STRING", {"default": "ShellAgent_Encrypted"}),
                "format": (get_format_list(),),
                "quality": ("INT", {"default": 85, "min": 1, "max": 100, "step": 1, "tooltip": "Quality level (higher = better quality, larger file)"}),
                "pingpong": ("BOOLEAN", {"default": False, "tooltip": "Reverse and append frames for seamless loop"}),
                "encrypt": ("BOOLEAN", {"default": True, "tooltip": "If enabled, output files will be encrypted and cannot be viewed directly."}),
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
    ):
        if images is None or len(images) == 0:
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
        
        if format_type == "image":
            # Use PIL for gif/webp
            self._create_animated_image(
                images, full_output_folder, filename, counter, 
                format_ext, frame_rate, loop_count, quality, 
                output_files, pbar, num_frames
            )
        else:
            # Use ffmpeg for video formats
            self._create_video(
                images, full_output_folder, filename, counter,
                format_ext, frame_rate, loop_count, quality,
                output_files, pbar, first_image
            )
        
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
                      output_files, pbar, first_image):
        """Create video using ffmpeg."""
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
        
        # Adjust quality based on format
        main_pass = video_format["main_pass"].copy()
        
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


NODE_CLASS_MAPPINGS = {
    "ShellAgentPluginVideoCombineEncrypt": ShellAgentVideoCombineEncrypt,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ShellAgentPluginVideoCombineEncrypt": "Video Combine Encrypt (ShellAgent Plugin)",
}
