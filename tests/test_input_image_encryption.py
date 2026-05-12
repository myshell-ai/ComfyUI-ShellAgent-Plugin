import importlib.util
import sys
import tempfile
import types
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
INPUT_IMAGE_PATH = ROOT / "comfy-nodes" / "input_image.py"


def load_input_image_module():
    sys.modules.setdefault("folder_paths", types.SimpleNamespace(get_input_directory=lambda: ""))
    sys.modules.setdefault(
        "node_helpers",
        types.SimpleNamespace(pillow=lambda fn, *args, **kwargs: fn(*args, **kwargs)),
    )
    sys.modules.setdefault(
        "torch",
        types.SimpleNamespace(
            from_numpy=lambda value: value,
            zeros=lambda *args, **kwargs: None,
            cat=lambda values, dim=0: values,
            float32="float32",
        ),
    )
    sys.modules.setdefault(
        "cv2",
        types.SimpleNamespace(
            IMREAD_COLOR=1,
            COLOR_BGR2RGB=1,
            imdecode=lambda *args, **kwargs: None,
            cvtColor=lambda image, code: image,
        ),
    )
    sys.modules.setdefault(
        "pillow_heif",
        types.SimpleNamespace(register_heif_opener=lambda: None),
    )

    spec = importlib.util.spec_from_file_location("shellagent_input_image", INPUT_IMAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_png_bytes():
    buffer = BytesIO()
    Image.new("RGB", (2, 2), (255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


class InputImageEncryptionTests(unittest.TestCase):
    def setUp(self):
        self.module = load_input_image_module()

    def test_encrypt_flag_encrypts_plain_image_file_for_future_runs(self):
        plain_bytes = make_png_bytes()
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "input.png"
            image_path.write_bytes(plain_bytes)

            image = self.module.open_encrypted_image_file(str(image_path))

            self.assertEqual(image.size, (2, 2))
            self.assertNotEqual(image_path.read_bytes(), plain_bytes)
            with self.assertRaises(UnidentifiedImageError):
                Image.open(image_path).verify()

            decrypted = self.module.xor_decrypt_bytes(image_path.read_bytes(), self.module.ENCRYPTION_KEY)
            Image.open(BytesIO(decrypted)).verify()

    def test_encrypt_flag_accepts_previously_encrypted_image_file(self):
        encrypted = self.module.xor_decrypt_bytes(make_png_bytes(), self.module.ENCRYPTION_KEY)
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "input.png"
            image_path.write_bytes(encrypted)

            image = self.module.open_encrypted_image_file(str(image_path))

            self.assertEqual(image.size, (2, 2))
            self.assertEqual(image_path.read_bytes(), encrypted)


if __name__ == "__main__":
    unittest.main()
