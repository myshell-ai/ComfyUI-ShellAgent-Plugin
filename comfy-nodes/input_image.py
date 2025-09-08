import folder_paths
import node_helpers

from PIL import Image, ImageOps, ImageSequence, ImageFile
import numpy as np
import torch
import os
import uuid
import tqdm
from io import BytesIO
import PIL
import cv2
from pillow_heif import register_heif_opener

register_heif_opener()

def safe_open_image(image_bytes):
    try:
        image_pil = Image.open(BytesIO(image_bytes))
    except PIL.UnidentifiedImageError as e:
        print(e)
        # Convert response content (bytes) to a NumPy array
        image_array = np.frombuffer(image_bytes, np.uint8)
        
        # Decode the image from the NumPy array (OpenCV format: BGR)
        image_cv = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if image_cv is not None:
            # Convert the BGR image to RGB
            image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
            
            # Convert the RGB NumPy array to a PIL Image
            image_pil = Image.fromarray(image_rgb)
        else:
            raise ValueError("The image cannot be identified by neither PIL nor OpenCV")
    return image_pil

class ShellAgentPluginInputImage:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        files = sorted(files)
        return {
            "required": {
                "input_name": (
                    "STRING",
                    {"multiline": False, "default": "input_image", "forceInput": False},
                ),
                "default_value": (
                    sorted(files), {"image_upload": True, "forceInput": False}
                ),
            },
            "optional": {
                "description": (
                    "STRING",
                    {"multiline": False, "default": "", "forceInput": False},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    # RETURN_NAMES = ("image",)

    FUNCTION = "run"

    CATEGORY = "shellagent"
    
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["input_name"],
            "type": "string",
            "default": kwargs["default_value"],
            "description": kwargs.get("description", ""),
            "url_type": "image"
        }
        return schema
    
    @classmethod
    def VALIDATE_INPUTS(s, input_name, default_value, description=""):
        image = default_value
        
        if image.startswith("http"):
            return True
        
        if image == "":
            return "Invalid image file: please check if the image is empty or invalid"
        
        if os.path.isfile(image):
            return True
        
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)

        return True
    
    def convert_image_mask(self, img):
        output_images = []
        output_masks = []
        w, h = None, None

        excluded_formats = ['MPO']
        
        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]
            
            if image.size[0] != w or image.size[1] != h:
                continue
            
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]

        return (output_image, output_mask)


    def run(self, input_name, default_value=None, display_name=None, description=None):
        image_path = default_value
        input_dir = folder_paths.get_input_directory()
        try:
            if image_path.startswith('http'):
                import requests
                from io import BytesIO
                print("Fetching image from url: ", image_path)
                response = requests.get(image_path)
                image = safe_open_image(response.content)
            elif image_path.startswith('data:image/png;base64,') or image_path.startswith('data:image/jpeg;base64,') or image_path.startswith('data:image/jpg;base64,'):
                import base64
                from io import BytesIO
                print("Decoding base64 image")
                base64_image = image_path[image_path.find(",")+1:]
                decoded_image = base64.b64decode(base64_image)
                image = Image.open(BytesIO(decoded_image))
            else:
                if not os.path.isfile(image_path): # abs path
                    # local path
                    image_path = os.path.join(input_dir, image_path)
                image = node_helpers.pillow(Image.open, image_path)

            return self.convert_image_mask(image)
            # image = ImageOps.exif_transpose(image)
            # image = image.convert("RGB")
            # image = np.array(image).astype(np.float32) / 255.0
            # image = torch.from_numpy(image)[None,]
            # return [image]
        except Exception as e:
            raise e

# video_extensions = ["webm", "mp4", "mkv", "gif"]

# class ShellAgentPluginInputVideo:
#     @classmethod
#     def INPUT_TYPES(s):
#         input_dir = folder_paths.get_input_directory()
#         files = []
#         for f in os.listdir(input_dir):
#             if os.path.isfile(os.path.join(input_dir, f)):
#                 file_parts = f.split(".")
#                 if len(file_parts) > 1 and (file_parts[-1] in video_extensions):
#                     files.append(f)
                
#         return {
#             "required": {
#                 "input_name": (
#                     "STRING",
#                     {"multiline": False, "default": "input_video"},
#                 ),
#                 "default_value": (
#                     "STRING", {"video_upload": True, "default": files[0] if len(files) else ""},
#                 ),
#             },
#             "optional": {
#                 "description": (
#                     "STRING",
#                     {"multiline": True, "default": ""},
#                 ),
#             }
#         }

#     RETURN_TYPES = ("STRING",)
#     RETURN_NAMES = ("video",)

#     FUNCTION = "run"

#     CATEGORY = "shellagent"

#     def run(self, input_name, default_value=None, description=None):
#         input_dir = folder_paths.get_input_directory()
#         if default_value.startswith("http"):
#             import requests

#             print("Fetching video from URL: ", default_value)
#             response = requests.get(default_value, stream=True)
#             file_size = int(response.headers.get("Content-Length", 0))
#             file_extension = default_value.split(".")[-1].split("?")[
#                 0
#             ]  # Extract extension and handle URLs with parameters
#             if file_extension not in video_extensions:
#                 file_extension = ".mp4"

#             unique_filename = str(uuid.uuid4()) + "." + file_extension
#             video_path = os.path.join(input_dir, unique_filename)
#             chunk_size = 1024  # 1 Kibibyte

#             num_bars = int(file_size / chunk_size)

#             with open(video_path, "wb") as out_file:
#                 for chunk in tqdm(
#                     response.iter_content(chunk_size=chunk_size),
#                     total=num_bars,
#                     unit="KB",
#                     desc="Downloading",
#                     leave=True,
#                 ):
#                     out_file.write(chunk)
#         elif os.path.isfile(default_value):
#             video_path = default_value
#         else:
#             video_path = os.path.abspath(os.path.join(input_dir, default_value))

#         return (video_path,)


NODE_CLASS_MAPPINGS = {
    "ShellAgentPluginInputImage": ShellAgentPluginInputImage,
    # "ShellAgentPluginInputVideo": ShellAgentPluginInputVideo,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ShellAgentPluginInputImage": "Input Image (ShellAgent Plugin)",
    # "ShellAgentPluginInputVideo": "Input Video (ShellAgent Plugin)"
}