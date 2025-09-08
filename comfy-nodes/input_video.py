import folder_paths
from PIL import Image, ImageOps
import numpy as np
import torch
import os
import uuid
from tqdm import tqdm


# class ShellAgentPluginInputImage:
#     @classmethod
#     def INPUT_TYPES(s):
#         input_dir = folder_paths.get_input_directory()
#         files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
#         files = sorted(files)
#         return {
#             "required": {
#                 "input_name": (
#                     "STRING",
#                     {"multiline": False, "default": "input_image"},
#                 ),
#                 "default_value": (
#                     "STRING", {"image_upload": True, "default": files[0] if len(files) else ""},
#                 ),
#             },
#             "optional": {
#                 "description": (
#                     "STRING",
#                     {"multiline": True, "default": ""},
#                 ),
#             }
#         }

#     RETURN_TYPES = ("IMAGE",)
#     RETURN_NAMES = ("image",)

#     FUNCTION = "run"

#     CATEGORY = "shellagent"

#     def run(self, input_name, default_value=None, display_name=None, description=None):
#         input_dir = folder_paths.get_input_directory()
#         image_path = default_value
#         try:
#             if image_path.startswith('http'):
#                 import requests
#                 from io import BytesIO
#                 print("Fetching image from url: ", image)
#                 response = requests.get(image)
#                 image = Image.open(BytesIO(response.content))
#             elif image_path.startswith('data:image/png;base64,') or image_path.startswith('data:image/jpeg;base64,') or image_path.startswith('data:image/jpg;base64,'):
#                 import base64
#                 from io import BytesIO
#                 print("Decoding base64 image")
#                 base64_image = image_path[image_path.find(",")+1:]
#                 decoded_image = base64.b64decode(base64_image)
#                 image = Image.open(BytesIO(decoded_image))
#             else:
#                 # local path
#                 image_path = os.path.join(input_dir, image_path)
#                 image = Image.open(image_path).convert("RGB")

#             image = ImageOps.exif_transpose(image)
#             image = image.convert("RGB")
#             image = np.array(image).astype(np.float32) / 255.0
#             image = torch.from_numpy(image)[None,]
#             return [image]
#         except Exception as e:
#             raise e

video_extensions = ["webm", "mp4", "mkv", "gif"]

class ShellAgentPluginInputVideo:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = []
        for f in os.listdir(input_dir):
            if os.path.isfile(os.path.join(input_dir, f)):
                file_parts = f.split(".")
                if len(file_parts) > 1 and (file_parts[-1] in video_extensions):
                    files.append(f)
                
        return {
            "required": {
                "input_name": (
                    "STRING",
                    {"multiline": False, "default": "input_video"},
                ),
                "default_value": (
                    sorted(files),
                    { "video_upload": True }
                ),
                # "default_value": (
                #     "STRING", {"video_upload": True, "default": files[0] if len(files) else ""},
                # ),
            },
            "optional": {
                "description": (
                    "STRING",
                    {"multiline": True, "default": ""},
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video",)

    FUNCTION = "run"

    CATEGORY = "shellagent"
    
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["input_name"],
            "type": "string",
            "default": kwargs["default_value"],
            "description": kwargs["description"],
            "url_type": "video"
        }
        return schema
    
    @classmethod
    def VALIDATE_INPUTS(s, input_name, default_value, description=""):
        video = default_value
        if video.startswith("http"):
            return True
        if not folder_paths.exists_annotated_filepath(video):
            return "Invalid video file: {}".format(video)
        return True

    def run(self, input_name, default_value=None, description=None):
        input_dir = folder_paths.get_input_directory()
        if default_value.startswith("http"):
            import requests

            print("Fetching video from URL: ", default_value)
            response = requests.get(default_value, stream=True)
            file_size = int(response.headers.get("Content-Length", 0))
            file_extension = default_value.split(".")[-1].split("?")[
                0
            ]  # Extract extension and handle URLs with parameters
            if file_extension not in video_extensions:
                file_extension = ".mp4"

            unique_filename = str(uuid.uuid4()) + "." + file_extension
            video_path = os.path.join(input_dir, unique_filename)
            chunk_size = 1024  # 1 Kibibyte

            num_bars = int(file_size / chunk_size)

            with open(video_path, "wb") as out_file:
                for chunk in tqdm(
                    response.iter_content(chunk_size=chunk_size),
                    total=num_bars,
                    unit="KB",
                    desc="Downloading",
                    leave=True,
                ):
                    out_file.write(chunk)
        else:
            if os.path.isfile(default_value):
                video_path = default_value
            else:
                video_path = os.path.abspath(os.path.join(input_dir, default_value))

        return (video_path,)


NODE_CLASS_MAPPINGS = {
    # "ShellAgentPluginInputImage": ShellAgentPluginInputImage,
    "ShellAgentPluginInputVideo": ShellAgentPluginInputVideo,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    # "ShellAgentPluginInputImage": "Input Image (ShellAgent Plugin)",
    "ShellAgentPluginInputVideo": "Input Video (ShellAgent Plugin)"
}
