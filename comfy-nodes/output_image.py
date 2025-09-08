import folder_paths
from nodes import SaveImage
import os

class ShellAgentSaveImages(SaveImage):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "output_name": ("STRING", {"multiline": False, "default": "output_image"},),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."})
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }
        
    CATEGORY = "shellagent"
    
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["output_name"],
            "type": "array",
            "items": {
                "type": "string",
                "url_type": "image",
            }
        }
        return schema
    
    def save_images(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None, **extra_kwargs):
        results = super().save_images(images, filename_prefix, prompt, extra_pnginfo)
        results["shellagent_kwargs"] = extra_kwargs
        return results
    
    
class ShellAgentSaveImage(ShellAgentSaveImages):
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["output_name"],
            "type": "string",
            "url_type": "image",
        }
        return schema
    
    
class ShellAgentSaveVideoVHS:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filenames": ("VHS_FILENAMES", {"tooltip": "The filenames to save."}),
                "output_name": ("STRING", {"multiline": False, "default": "output_video"},),
            },
        }
        
    RETURN_TYPES = ()
    FUNCTION = "save_video"

    OUTPUT_NODE = True

    CATEGORY = "shellagent"
    DESCRIPTION = "Saves the input images to your ComfyUI output directory."
    
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["output_name"],
            "type": "string",
            "url_type": "video",
        }
        return schema
        
    def save_video(self, filenames, **kwargs):
        status, output_files = filenames
        if len(output_files) == 0:
            raise ValueError("the filenames are empty")
        print("output_files", output_files)
        video_path = output_files[-1]
        cwd = os.getcwd()
        # preview_image = os.path.relpath(preview_image)
        video_path = os.path.relpath(video_path, folder_paths.base_path)
        results = {"ui": {"video": [video_path]}}
        return results
    
    
NODE_CLASS_MAPPINGS = {
    "ShellAgentPluginSaveImage": ShellAgentSaveImage,
    "ShellAgentPluginSaveImages": ShellAgentSaveImages,
    "ShellAgentPluginSaveVideoVHS": ShellAgentSaveVideoVHS,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ShellAgentPluginSaveImage": "Save Image (ShellAgent Plugin)",
    "ShellAgentPluginSaveImages": "Save Images (ShellAgent Plugin)",
    "ShellAgentPluginSaveVideoVHS": "Save Video - VHS (ShellAgent Plugin)",
}