import folder_paths
from PIL import Image, ImageOps
import numpy as np
import torch

class ShellAgentPluginInputText:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_name": (
                    "STRING",
                    {"multiline": False, "default": "input_text"},
                ),
            },
            "optional": {
                "default_value": (
                    "STRING",
                    {"multiline": True, "default": ""},
                ),
                "description": (
                    "STRING",
                    {"multiline": True, "default": ""},
                ),
                "choices": (
                    "STRING",
                    {"multiline": False, "default": ""},
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    FUNCTION = "run"

    CATEGORY = "shellagent"
    
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["input_name"],
            "type": "string",
            "default": kwargs["default_value"],
            "description": kwargs.get("description", ""),
        }
        if kwargs.get("choices", "") != "":
            schema["enums"] = eval(kwargs["choices"])
        return schema

    def run(self, input_name, default_value=None, display_name=None, description=None, choices=None):
        return [default_value]
    
    
class ShellAgentPluginInputFloat:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_name": (
                    "STRING",
                    {"multiline": False, "default": "input_float"},
                ),
            },
            "optional": {
                "default_value": (
                    "FLOAT",
                    {"default": 0.},
                ),
                "minimum": (
                    "FLOAT",
                    {"default": 0.},
                ),
                "maximum": (
                    "FLOAT",
                    {"default": 0.},
                ),
                "description": (
                    "STRING",
                    {"default": ""},
                ),
                "choices": (
                    "STRING",
                    {"multiline": False, "default": ""},
                ),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("float",)

    FUNCTION = "run"

    CATEGORY = "shellagent"
    
    @classmethod
    def validate(cls, **kwargs):
        if "mininum" in kwargs and "maxinum" in kwargs and kwargs["minimum"] > kwargs["maximum"]:
            raise ValueError("mininum cannot be greater than maximum")
        schema = {
            "title": kwargs["input_name"],
            "type": "number",
            "default": kwargs["default_value"],
            "description": kwargs.get("description", ""),
        }
        if kwargs.get("choices", "") != "":
            schema["enums"] = eval(kwargs["choices"])
        if "minimum" in kwargs:
            schema["minimum"] = kwargs["minimum"]
        if "maximum" in kwargs:
            schema["maximum"] = kwargs["maximum"]
        return schema


    def run(self, input_name, default_value=None, display_name=None, description=None, **kwargs):
        return [default_value]
    
    
class ShellAgentPluginInputInteger:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_name": (
                    "STRING",
                    {"multiline": False, "default": "input_integer"},
                ),
            },
            "optional": {
                "default_value": (
                    "INT",
                    {"default": 0.},
                ),
                "minimum": (
                    "INT",
                    {"default": 0.},
                ),
                "maximum": (
                    "INT",
                    {"default": 0.},
                ),
                "step": (
                    "INT",
                    {"default": 1, "min": 1, "max": 10000},
                ),
                "description": (
                    "STRING",
                    {"multiline": True, "default": ""},
                ),
                "choices": (
                    "STRING",
                    {"multiline": False, "default": ""},
                ),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("int",)

    FUNCTION = "run"

    CATEGORY = "shellagent"
    
    @classmethod
    def validate(cls, **kwargs):
        if "mininum" in kwargs and "maxinum" in kwargs and kwargs["minimum"] > kwargs["maximum"]:
            raise ValueError("mininum cannot be greater than maximum")
        schema = {
            "title": kwargs["input_name"],
            "type": "integer",
            "default": kwargs["default_value"],
            "description": kwargs["description"],
        }
        if kwargs.get("choices", "") != "":
            schema["enums"] = eval(kwargs["choices"])
        if "minimum" in kwargs:
            schema["minimum"] = kwargs["minimum"]
        if "maximum" in kwargs:
            schema["maximum"] = kwargs["maximum"]
        if "step" in kwargs:
            schema["multiple_of"] = kwargs["step"]
        return schema

    def run(self, input_name, default_value=None, display_name=None, description=None, **kwargs):
        return [default_value]

class ShellAgentPluginInputBoolean:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_name": (
                    "STRING",
                    {"multiline": False, "default": "input_bool"},
                ),
            },
            "optional": {
                "default_value": (
                    "BOOLEAN",
                    {"default": False},
                ),
                "description": (
                    "STRING",
                    {"multiline": True, "default": ""},
                ),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("boolean",)

    FUNCTION = "run"

    CATEGORY = "shellagent"
    
    @classmethod
    def validate(cls, **kwargs):
        schema = {
            "title": kwargs["input_name"],
            "type": "boolean",
            "default": kwargs["default_value"],
            "description": kwargs.get("description", ""),
        }
        return schema

    def run(self, input_name, default_value=None, display_name=None, description=None, **kwargs):
        return [default_value]


NODE_CLASS_MAPPINGS = {
    "ShellAgentPluginInputText": ShellAgentPluginInputText,
    "ShellAgentPluginInputFloat": ShellAgentPluginInputFloat,
    "ShellAgentPluginInputInteger": ShellAgentPluginInputInteger,
    "ShellAgentPluginInputBoolean": ShellAgentPluginInputBoolean,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ShellAgentPluginInputText": "Input Text (ShellAgent Plugin)",
    "ShellAgentPluginInputFloat": "Input Float (ShellAgent Plugin)",
    "ShellAgentPluginInputInteger": "Input Integer (ShellAgent Plugin)",
    "ShellAgentPluginInputBoolean": "Input Boolean (ShellAgent Plugin)",
}