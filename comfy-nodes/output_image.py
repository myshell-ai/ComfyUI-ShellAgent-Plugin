import folder_paths
from nodes import SaveImage
import os
import numpy as np

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


class ShellAgentSaveImages(SaveImage):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "output_name": ("STRING", {"multiline": False, "default": "output_image"},),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."}),
                "encrypt": ("BOOLEAN", {"default": False, "tooltip": "If enabled, the saved image will be encrypted and cannot be viewed directly. Use the same key to decrypt elsewhere."})
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
    
    def save_images(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None, encrypt=False, **extra_kwargs):
        results = super().save_images(images, filename_prefix, prompt, extra_pnginfo)
        
        # Encrypt saved files if encrypt option is enabled
        if encrypt:
            for img_info in results.get("ui", {}).get("images", []):
                filename = img_info["filename"]
                subfolder = img_info.get("subfolder", "")
                full_path = os.path.join(self.output_dir, subfolder, filename)
                if os.path.exists(full_path):
                    xor_encrypt_file(full_path, ENCRYPTION_KEY)
        
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