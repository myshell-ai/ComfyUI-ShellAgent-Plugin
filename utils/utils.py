import hashlib
import time
from pathlib import PurePosixPath, Path, PureWindowsPath
import base64
import re

def windows_to_linux_path(windows_path):
    return PureWindowsPath(windows_path).as_posix()

def compute_sha256(file_path, chunk_size=1024 ** 2):
    # Create a new sha256 hash object
    start = time.time()
    sha256 = hashlib.sha256()
    print("start compute sha256 for", file_path)
    # Open the file in binary mode
    with open(file_path, 'rb') as file:
        # Read the file in chunks to handle large files efficiently
        while chunk := file.read(chunk_size):
            sha256.update(chunk)
    print("finish compute sha256 for", file_path, f"time: {time.time() - start}")
    # Return the hexadecimal digest of the hash
    return sha256.hexdigest()


def get_alphanumeric_hash(input_string: str) -> str:
    # Generate a SHA-256 hash of the input string
    sha256_hash = hashlib.sha256(input_string.encode()).digest()
    
    # Encode the hash in base64 to get a string with [A-Za-z0-9+/=]
    base64_hash = base64.b64encode(sha256_hash).decode('ascii')
    
    # Remove any non-alphanumeric characters (+, /, =)
    alphanumeric_hash = re.sub(r'[^a-zA-Z0-9]', '', base64_hash)
    
    return alphanumeric_hash