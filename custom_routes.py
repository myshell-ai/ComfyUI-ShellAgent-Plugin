from io import BytesIO
from pprint import pprint
from aiohttp import web
import os
import requests
import folder_paths
import json
import server
from PIL import Image
import time
import execution
import random
import traceback
import uuid
import asyncio
import logging
from urllib.parse import quote
import threading
import hashlib
import aiohttp
from aiohttp import ClientSession, web
import aiofiles
from typing import Dict, List, Union, Any, Optional
from PIL import Image
import copy
import struct
from aiohttp import web, ClientSession, ClientError, ClientTimeout, ClientResponseError
import atexit
from datetime import datetime
import nodes
import traceback
import re
import keyword
import uuid

from .dependency_checker import resolve_dependencies, inspect_repo_version
from folder_paths import base_path as BASE_PATH

WORKFLOW_ROOT = "shellagent/comfy_workflow"

CustomNodeTypeMap = {
    "ShellAgentPluginInputText": "text",
    "ShellAgentPluginInputInteger": "integer",
    "ShellAgentPluginInputFloat": "number",
    "ShellAgentPluginInputImage": "image",
    "ShellAgentPluginInputVideo": "video",
    "ShellAgentPluginSaveImage": "image",
    "ShellAgentPluginSaveVideoVHS": "video",
}

# Regular expression for a valid Python variable name
variable_name_pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'

def is_valid_variable_name(name):
    # Check if it matches the pattern and is not a keyword
    if re.match(variable_name_pattern, name) and not keyword.iskeyword(name):
        return True
    return False

def schema_validator(prompt):
    from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    input_names = []
    output_names = []
    schemas = {
        "inputs": {},
        "outputs": {}
    }
    for node_id, node_info in prompt.items():
        node_class_type = node_info.get("class_type")
        if node_class_type is None:
            raise NotImplementedError(f"Missing nodes founded, please first install the missing nodes using ComfyUI Manager")
        node_cls = NODE_CLASS_MAPPINGS[node_class_type]
        if hasattr(node_cls, "RELATIVE_PYTHON_MODULE") and node_cls.RELATIVE_PYTHON_MODULE.startswith("custom_nodes.ComfyUI-ShellAgent-Plugin"):
            schema = {}
            if "input_name" in node_info["inputs"]:
                mode = "inputs"
                input_name = node_info["inputs"]["input_name"]
                if input_name not in input_names:
                    input_names.append(input_name)
                else:
                    raise ValueError(f"Duplicated input_name found in node {NODE_DISPLAY_NAME_MAPPINGS[node_class_type]} with ID={node_id}")
                # handle the schema at the same time
                schema["name"] = input_name
                
            elif "output_name" in node_info["inputs"]:
                mode = "outputs"
                output_name = node_info["inputs"]["output_name"]
                if output_name not in output_names:
                    output_names.append(output_name)
                else:
                    raise ValueError(f"Duplicated output_name found in node {NODE_DISPLAY_NAME_MAPPINGS[node_class_type]} with ID={node_id}")
                schema["name"] = output_name
            else:
                # neither input nor output
                continue
            if hasattr(node_cls, "validate"):
                schema = node_cls.validate(**node_info["inputs"])
                # validate schema
                if not is_valid_variable_name(schema["title"]):
                    raise ValueError(f'`{schema["title"]}` is not a valid variable name!')
            else:
                raise NotImplementedError("the validate is not implemented")
            schemas[mode][node_id] = schema
    return schemas
            
                
@server.PromptServer.instance.routes.get("/shellagent/list_workflow") # data same as queue prompt, plus workflow_name
async def shellagent_list_workflow(request):
    workflow_ids = os.listdir(WORKFLOW_ROOT)
    # append the metadata
    data = []
    for workflow_id in workflow_ids:

        metadata_file = os.path.join(WORKFLOW_ROOT, workflow_id, "metadata.json")
        metadata = json.load(open(metadata_file))
        item = {
            "id": workflow_id,
            "metadata": metadata
        }
        data.append(item)
    return web.json_response(data, status=400)
    
@server.PromptServer.instance.routes.post("/shellagent/get_file") # data same as queue prompt, plus workflow_name
async def shellagent_get_file(request):
    data = await request.json()
    assert data["filename"] in [
        "workflow_api.json",
        "dependencies.json",
        "metadata.json",
        "extra_data.json",
        "schemas.json",
    ]
    
    data = json.load(open(os.path.join(WORKFLOW_ROOT, data["workflow_id"], data["filename"])))
    return web.json_response(data, status=400)
    
@server.PromptServer.instance.routes.post("/shellagent/export") # data same as queue prompt, plus workflow_name
async def shellagent_export(request):
    data = await request.json()
    prompt = data["prompt"]
    custom_dependencies = data.get("custom_dependencies",  {
        "models": {},
        "custom_nodes": {}
    })
    # extra_data = data["extra_data"]
    workflow_id = str(uuid.uuid4())
    
    # metadata.json
    # metadata = {
    #     "name": data["workflow_name"],
    #     "workflow_id": workflow_id,
    #     "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # }
    
    return_dict = {}
    status = 200
    try:
        schemas = schema_validator(prompt)
        # custom_node.json
        dependency_results = resolve_dependencies(prompt, custom_dependencies)
        # save_root = os.path.join(WORKFLOW_ROOT, workflow_id)
        # os.makedirs(save_root, exist_ok=True)
        
        # fname_mapping = {
        #     "workflow_api.json": prompt,
        #     "dependencies.json": dependency_results,
        #     # "metadata.json": metadata,
        #     # "extra_data.json": extra_data,
        #     "schemas.json": schemas,
        # }
        
        # for fname, dict_to_save in fname_mapping.items():
        #     with open(os.path.join(save_root, fname), "w") as f:
        #         json.dump(dict_to_save, f, indent=2)
        warning_message = ""
        if dependency_results.get("black_list_nodes", []):
            warning_message = "The following nodes cannot be deployed to myshell:\n"
            for item in dependency_results["black_list_nodes"]:
                warning_message += f"  {item['name']}: {item['reason']}\n"
                
        if len(schemas["inputs"]) + len(schemas["outputs"]) == 0:
            warning_message += f"The workflow contains neither inputs nor outputs!\n"
        
        return_dict = {
            "success": True,
            "dependencies": dependency_results["dependencies"],
            "warning_message": warning_message,
            "schemas": schemas
        }
    except Exception as e:
        status = 400
        return_dict = {
            "success": False,
            "message_detail": str(traceback.format_exc()),
            "message": str(e),
        }
    return web.json_response(return_dict, status=status)


@server.PromptServer.instance.routes.post("/shellagent/inspect_version") # data same as queue prompt, plus workflow_name
async def shellagent_inspect_version(request):
    data = await request.json()
    comfyui_version = inspect_repo_version(BASE_PATH)
    comfyui_shellagent_plugin_version = inspect_repo_version(os.path.dirname(__file__))
    return_dict = {
        "comfyui_version": comfyui_version,
        "comfyui_shellagent_plugin_version": comfyui_shellagent_plugin_version,
    }
    return web.json_response(return_dict, status=200)


@server.PromptServer.instance.routes.post("/shellagent/get_mac_addr") # data same as queue prompt, plus workflow_name
async def shellagent_get_mac_addr(request):
    data = await request.json()
    return_dict = {
        "mac_addr": uuid.getnode()
    }
    return web.json_response(return_dict, status=200)

@server.PromptServer.instance.routes.post("/shellagent/check_exist") # check if the file or folder exist
async def shellagent_check_exist(request):
    data = await request.json()

    return_dict = {
        "exist": uuid.getnode() == data["mac_addr"] and os.path.exists(data["path"]) # really exist, instead of same name
    }
    return web.json_response(return_dict, status=200)