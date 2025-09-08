import os
import subprocess
import json
import logging
from functools import partial
import re
import glob
import sys
from folder_paths import models_dir as MODELS_DIR
from folder_paths import base_path as BASE_PATH
from folder_paths import get_full_path


from .utils.utils import compute_sha256, windows_to_linux_path
from .utils.pytree import tree_map
from .file_upload import collect_local_file, process_local_file_path_async


model_list_json = json.load(open(os.path.join(os.path.dirname(__file__), "model_info.json")))
model_loaders_info = json.load(open(os.path.join(os.path.dirname(__file__), "model_loader_info.json")))
node_deps_info = json.load(open(os.path.join(os.path.dirname(__file__), "node_deps_info.json")))
node_blacklist = json.load(open(os.path.join(os.path.dirname(__file__), "node_blacklist.json")))
node_remote_skip_models = json.load(open(os.path.join(os.path.dirname(__file__), "node_remote.json")))

model_suffix = [".ckpt", ".safetensors", ".bin", ".pth", ".pt", ".onnx", ".gguf", ".sft", ".ttf"]
extra_packages = ["transformers", "timm", "diffusers", "accelerate"]


def get_full_path_or_raise(folder_name: str, filename: str) -> str:
    full_path = get_full_path(folder_name, filename)
    if full_path is None:
        raise FileNotFoundError(f"Model in folder '{folder_name}' with filename '{filename}' not found.")
    return full_path


def handle_model_info(ckpt_path, filename, rel_save_path):
    ckpt_path = windows_to_linux_path(ckpt_path)
    metadata_path = ckpt_path + ".json"
    if os.path.isfile(metadata_path):
        metadata = json.load(open(metadata_path))
        model_id = metadata["id"]
    else:
        logging.info(f"computing sha256 of {ckpt_path}")
        if not os.path.isfile(ckpt_path):
            raise NotImplementedError(f"please install {ckpt_path} first!")
        model_id = compute_sha256(ckpt_path)
        data = {
            "id": model_id,
            "save_path": rel_save_path,
            "filename": filename,
        }
        json.dump(data, open(metadata_path, "w"))
    if model_id in model_list_json:
        urls = [item["url"] for item in model_list_json[model_id]["links"]][:10] # use the top 10
    else:
        urls = []
        
    item = {
        "filename": windows_to_linux_path(filename),
        "save_path": windows_to_linux_path(rel_save_path),
        "urls": urls,
    }
    return model_id, item


def inspect_repo_version(module_path):
    # Create and return the JSON result
    result = {
        "name": os.path.basename(module_path),
        "repo": "",
        "commit": ""
    }
    
    if not os.path.isdir(os.path.join(module_path, ".git")):
        return result
    
    # Get the remote repository URL
    try:
        remote_url = subprocess.check_output(
            ['git', 'config', '--get', 'remote.origin.url'],
            cwd=module_path
        ).strip().decode()
    except Exception:
        return result

    # Get the latest commit hash
    try:
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=module_path
        ).strip().decode()
    except Exception:
        return result

    # Create and return the JSON result
    result = {
        "name": os.path.basename(module_path),
        "repo": remote_url,
        "commit": commit_hash
    }
    return result

def fetch_model_searcher_results(model_ids):
    import requests
    url = "https://models-searcher.myshell.life/search_urls"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "sha256": model_ids
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        results = [item[:10] for item in response.json()]
    else:
        results = None
    return results

def split_package_version(require_line):
    require_line = require_line.strip()
    
    pattern = r"^([a-zA-Z0-9_\-\[\]]+)(.*)$"
    match = re.match(pattern, require_line.strip())
    
    if match:
        package_name = match.group(1)  # First capturing group is the package name
        version_specifier = match.group(2) if match.group(2) else ""  # Second group is the version, if present
        return package_name, version_specifier
    else:
        assert len(require_line) == 0 or require_line.strip()[0] == "#", require_line
        return None, None

def get_package_version(package_name):
    try:
        if sys.version_info >= (3, 8):
            from importlib.metadata import version, PackageNotFoundError
            return version(package_name)
        else:
            from pkg_resources import get_distribution, DistributionNotFound
            return get_distribution(package_name).version
    except Exception:
        return None
    
def resolve_dependencies(prompt, custom_dependencies): # resolve custom nodes and models at the same time
    from nodes import NODE_CLASS_MAPPINGS
    import folder_paths
    
    custom_nodes = []
    ckpt_paths = {}
    
    file_mapping_dict = {}
    
    SKIP_FOLDER_NAMES = ["configs", "custom_nodes"]
    def collect_unknown_models(filename, node_id, node_info, custom_node_path):
        if type(filename) != str:
            return
        is_model = False
        for possible_suffix in model_suffix:
            if filename.endswith(possible_suffix):
                is_model = True
        if is_model:
            print(f"find {filename}, is_model=True")
            # find possible paths
            matching_files = {}
            # Walk through all subdirectories and files in the directory
            rel_save_path = None
            for possible_folder_name in folder_paths.folder_names_and_paths:
                if possible_folder_name in SKIP_FOLDER_NAMES:
                    print(f"skip {possible_folder_name}")
                    continue
                full_path = folder_paths.get_full_path(possible_folder_name, filename)
                if full_path is None:
                    continue
                rel_save_path = os.path.relpath(folder_paths.folder_names_and_paths[possible_folder_name][0][0], folder_paths.models_dir)
                matching_files[full_path] = {
                    "rel_save_path": rel_save_path
                }

            print(f"matched files: {matching_files}")
            
            # step 2: search for all the files under "models"
            
            for full_path in glob.glob(f"{folder_paths.models_dir}/**/*", recursive=True):
                if os.path.isfile(full_path) and full_path.endswith(filename) and full_path not in matching_files:
                    folder_path = full_path[:-len(filename)]
                    rel_save_path = os.path.relpath(folder_path, folder_paths.models_dir)
                    matching_files[full_path] = {
                        "rel_save_path": rel_save_path
                    }
                    
            print(f"matched files: {matching_files}")
            
            # step 3: search inside the custom nodes
            if custom_node_path is not None:
                for full_path in glob.glob(f"{custom_node_path}/**/*", recursive=True):
                    if os.path.isfile(full_path) and full_path.endswith(filename) and full_path not in matching_files:
                        folder_path = full_path[:-len(filename)]
                        rel_save_path = os.path.relpath(folder_path, folder_paths.models_dir)
                        matching_files[full_path] = {
                            "rel_save_path": rel_save_path
                        }
            
            if len(matching_files) == 0:
                raise ValueError(f"Cannot find model: `{filename}`, Node ID: `{node_id}`, Node Info: `{node_info}`")
            
            elif len(matching_files) <= 3:
                for full_path, info in matching_files.items():
                    ckpt_paths[full_path] = {
                        "filename": filename,
                        "rel_save_path": info["rel_save_path"]
                    }
                    return
            else:
                raise ValueError(f"Multiple models of `{filename}` founded, Node ID: `{node_id}`, Node Info: `{node_info}`, Possible paths: `{list(matching_files.keys())}`")
            
    
    for node_id, node_info in prompt.items():
        node_class_type = node_info.get("class_type")
        if node_class_type is None:
            raise NotImplementedError(f"Missing nodes founded, please first install the missing nodes using ComfyUI Manager")
        node_cls = NODE_CLASS_MAPPINGS[node_class_type]
        
        skip_model_check = False
        
        custom_node_path = None
        if hasattr(node_cls, "RELATIVE_PYTHON_MODULE") and node_cls.RELATIVE_PYTHON_MODULE.startswith("custom_nodes."):
            print(node_cls.RELATIVE_PYTHON_MODULE)
            custom_nodes.append(node_cls.RELATIVE_PYTHON_MODULE)
            custom_node_path = os.path.join(BASE_PATH, node_cls.RELATIVE_PYTHON_MODULE.replace(".", "/"))
            if node_cls.RELATIVE_PYTHON_MODULE[len("custom_nodes."):] in node_remote_skip_models:
                skip_model_check = True
                print(f"skip model check for {node_class_type}")
                
        if node_class_type in model_loaders_info:
            for field_name, filename in node_info["inputs"].items():
                if type(filename) != str:
                    continue
                for item in model_loaders_info[node_class_type]:
                    pattern = item["field_name"]
                    if re.match(f"^{pattern}$", field_name) and any([filename.endswith(possible_suffix) for possible_suffix in model_suffix]):
                        ckpt_path = get_full_path_or_raise(item["save_path"], filename)
                        if hasattr(folder_paths, "map_legacy"):
                            save_folder = folder_paths.map_legacy(item["save_path"])
                        else:
                            save_folder = item["save_path"]
                        rel_save_path = os.path.relpath(folder_paths.folder_names_and_paths[save_folder][0][0], folder_paths.models_dir)
                        ckpt_paths[ckpt_path] = {
                            "filename": filename,
                            "rel_save_path": rel_save_path
                        }
        elif not skip_model_check:
            tree_map(lambda x: collect_unknown_models(x, node_id, node_info, custom_node_path), node_info["inputs"])

        list(map(partial(collect_local_file, mapping_dict=file_mapping_dict), node_info["inputs"].values()))
            
    print("ckpt_paths:", ckpt_paths)
    custom_nodes = list(set(custom_nodes))
    # step 0: comfyui version
    repo_info = inspect_repo_version(BASE_PATH)
    if repo_info["repo"] == "":
        repo_info["require_recheck"] = True
        if repo_info["name"] in custom_dependencies["custom_nodes"]:
            repo_info["repo"] = custom_dependencies["custom_nodes"][repo_info["name"]].get("repo", "")
            repo_info["commit"] = custom_dependencies["custom_nodes"][repo_info["name"]].get("commit", "")
    comfyui_version = repo_info

    # step 1: custom nodes
    custom_nodes_list = []
    custom_nodes_names = []
    requirements_lines = []
    for custom_node in custom_nodes:
        try:
            repo_info = inspect_repo_version(os.path.join(BASE_PATH, custom_node.replace(".", "/")))
            custom_nodes_list.append(repo_info)
            if repo_info["repo"] == "":
                repo_info["require_recheck"] = True
                if repo_info["name"] in custom_dependencies["custom_nodes"]:
                    repo_info["repo"] = custom_dependencies["custom_nodes"][repo_info["name"]].get("repo", "")
                    repo_info["commit"] = custom_dependencies["custom_nodes"][repo_info["name"]].get("commit", "")
            custom_nodes_names.append(repo_info["name"])
        except:
            print(f"failed to resolve repo info of {custom_node}")
        requirement_file = os.path.join(BASE_PATH, custom_node.replace(".", "/"), "requirements.txt")
        if os.path.isfile(requirement_file):
            try:
                requirements_lines += open(requirement_file).readlines()
            except:
                pass
    requirements_lines = list(set(requirements_lines))
    requirements_packages = [package_name for package_name, version_specifier in map(split_package_version, requirements_lines) if package_name is not None]
    package_names = set(requirements_packages + extra_packages)
    pypi_deps = {
        package_name: get_package_version(package_name)
        for package_name in package_names
    }
    
    for repo_name in custom_nodes_names:
        if repo_name in node_deps_info:
            for deps_node in node_deps_info[repo_name]:
                if deps_node["name"] not in custom_nodes_names:
                    repo_info = inspect_repo_version(os.path.join(BASE_PATH, "custom_nodes", deps_node["name"]))
                    deps_node["commit"] = repo_info["commit"]
                    custom_nodes_list.append(deps_node)
                    custom_nodes_names.append(deps_node["name"])
                    
    black_list_nodes = []
    for repo_name in custom_nodes_names:
        if repo_name in node_blacklist:
            black_list_nodes.append({"name": repo_name, "reason": node_blacklist[repo_name]["reason"]})
    
    # step 2: models
    models_dict = {}
    missing_model_ids = []
    for ckpt_path, ckpt_info in ckpt_paths.items():
        model_id, item = handle_model_info(ckpt_path, ckpt_info["filename"], ckpt_info["rel_save_path"])
        models_dict[model_id] = item
        if len(item["urls"]) == 0:
            item["require_recheck"] = True
            if model_id in custom_dependencies["models"]:
                item["urls"] = custom_dependencies["models"][model_id].get("urls", [])
            missing_model_ids.append(model_id)
            
    # try to fetch from myshell model searcher
    missing_model_results_myshell = fetch_model_searcher_results(missing_model_ids)
    if missing_model_results_myshell is not None:
        for missing_model_id, missing_model_urls in zip(missing_model_ids, missing_model_results_myshell):
            if len(missing_model_urls) > 0:
                models_dict[missing_model_id]["require_recheck"] = False
                models_dict[missing_model_id]["urls"] = missing_model_urls
                print("successfully fetch results from myshell", models_dict[missing_model_id])

    # step 3: handle local files
    process_local_file_path_async(file_mapping_dict, max_workers=20)
    files_dict = {
        v[0]: {
            "filename": windows_to_linux_path(os.path.relpath(v[2], BASE_PATH)) if not v[3] else v[2], 
            "urls": [v[1]]} for v in file_mapping_dict.values()}
    
    depencencies = {
        "comfyui_version": comfyui_version,
        "custom_nodes": custom_nodes_list,
        "models": models_dict,
        "files": files_dict,
        "pypi": pypi_deps
    }
    
    return_dict = {
        "dependencies": depencencies,
        "black_list_nodes": black_list_nodes,
    }
    return return_dict
