import folder_paths
import node_helpers

from PIL import Image, ImageOps, ImageSequence, ImageFile
import numpy as np
import torch
import os
import uuid
import tqdm
import torchaudio
import hashlib
from comfy_extras.nodes_audio import SaveAudio


class LoadAudio:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = folder_paths.filter_files_content_types(
            os.listdir(input_dir), ["audio", "video"])
        return {"required": {"audio": (sorted(files), {"audio_upload": True})}}

    CATEGORY = "audio"

    RETURN_TYPES = ("AUDIO", )
    FUNCTION = "load"

    def load(self, audio):
        audio_path = folder_paths.get_annotated_filepath(audio)
        waveform, sample_rate = torchaudio.load(audio_path)
        audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        return (audio, )

    @classmethod
    def IS_CHANGED(s, audio):
        image_path = folder_paths.get_annotated_filepath(audio)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, audio):
        if not folder_paths.exists_annotated_filepath(audio):
            return "Invalid audio file: {}".format(audio)
        return True


class ShellAgentPluginInputAudio:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = folder_paths.filter_files_content_types(
            os.listdir(input_dir), ["audio", "video"])
        return {
            "required": {
                "input_name": (
                    "STRING",
                    {"multiline": False, "default": "input_audio", "forceInput": False},
                ),
                "default_value": (
                    sorted(files), {"audio_upload": True, "forceInput": False}
                ),
            },
            "optional": {
                "description": (
                    "STRING",
                    {"multiline": True, "default": "", "forceInput": False},
                ),
            }
        }

    RETURN_TYPES = ("AUDIO", )
    FUNCTION = "load"

    CATEGORY = "shellagent"

    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["input_name"],
            "type": "string",
            "default": kwargs["default_value"],
            "description": kwargs.get("description", ""),
            "url_type": "audio"
        }
        return schema

    @classmethod
    def VALIDATE_INPUTS(s, audio):
        if not folder_paths.exists_annotated_filepath(audio):
            return "Invalid audio file: {}".format(audio)
        return True

    @classmethod
    def VALIDATE_INPUTS(s, input_name, default_value, description=""):
        audio = default_value
        if audio.startswith("http"):
            return True

        if not folder_paths.exists_annotated_filepath(audio):
            return "Invalid audio file: {}".format(audio)
        return True

    def load(self, input_name, default_value=None, display_name=None, description=None):
        input_dir = folder_paths.get_input_directory()
        audio_path = default_value
        try:
            if audio_path.startswith('http'):
                import requests
                from io import BytesIO
                print("Fetching audio from url: ", audio_path)
                response = requests.get(audio_path)
                response.raise_for_status()
                audio_file = BytesIO(response.content)
                waveform, sample_rate = torchaudio.load(audio_file)
            else:
                if not os.path.isfile(audio_path):  # abs path
                    # local path
                    audio_path = os.path.join(input_dir, audio_path)
                waveform, sample_rate = torchaudio.load(audio_path)

            audio = {"waveform": waveform.unsqueeze(
                0), "sample_rate": sample_rate}
            return (audio, )
            # image = ImageOps.exif_transpose(image)
            # image = image.convert("RGB")
            # image = np.array(image).astype(np.float32) / 255.0
            # image = torch.from_numpy(image)[None,]
            # return [image]
        except Exception as e:
            raise e


class ShellAgentSaveAudios(SaveAudio):
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"audio": ("AUDIO", ),
                "output_name": ("STRING", {"multiline": False, "default": "output_audio"},),
                             "filename_prefix": ("STRING", {"default": "audio/ComfyUI"})},
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                }
    # {
    #         "required": {
    #             "images": ("IMAGE", {"tooltip": "The audio to save."}),
    #             "output_name": ("STRING", {"multiline": False, "default": "output_image"},),
    #             "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."})
    #         },
    #         "hidden": {
    #             "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
    #         },
    #     }

    CATEGORY = "shellagent"

    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["output_name"],
            "type": "array",
            "items": {
                "type": "string",
                "url_type": "audio",
            }
        }
        return schema

    def save_audio(self, audio, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None, **extra_kwargs):
        results = super().save_audio(audio, filename_prefix, prompt, extra_pnginfo)
        results["shellagent_kwargs"] = extra_kwargs
        return results

    def save_flac(self, audio, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None, **extra_kwargs):
        results = super().save_flac(audio, filename_prefix, "flac", prompt, extra_pnginfo)
        results["shellagent_kwargs"] = extra_kwargs
        return results
    
    
class ShellAgentSaveAudio(ShellAgentSaveAudios):
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["output_name"],
            "type": "string",
            "url_type": "audio",
        }
        return schema


NODE_CLASS_MAPPINGS = {
    "ShellAgentPluginInputAudio": ShellAgentPluginInputAudio,
    "ShellAgentPluginSaveAudios": ShellAgentSaveAudios,
    "ShellAgentPluginSaveAudio": ShellAgentSaveAudio,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ShellAgentPluginInputAudio": "Input Audio (ShellAgent Plugin)",
    "ShellAgentPluginSaveAudios": "Save Audios (ShellAgent Plugin)",
    "ShellAgentPluginSaveAudio": "Save Audio (ShellAgent Plugin)",
}
