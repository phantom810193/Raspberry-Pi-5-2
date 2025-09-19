import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _install_stub(module_name: str, module):
    if module_name not in sys.modules:
        sys.modules[module_name] = module


_install_stub('cv2', MagicMock())
_install_stub('face_recognition', MagicMock())
numpy_module = ModuleType('numpy')
numpy_module.bool_ = bool
numpy_module.isscalar = lambda value: isinstance(value, (int, float, bool))
_install_stub('numpy', numpy_module)

mysql_connector = MagicMock()
mysql_package = ModuleType('mysql')
mysql_package.connector = mysql_connector
_install_stub('mysql', mysql_package)
_install_stub('mysql.connector', mysql_connector)

pil_package = ModuleType('PIL')
pil_image = MagicMock()
pil_imagetk = MagicMock()
pil_package.Image = pil_image
pil_package.ImageTk = pil_imagetk
_install_stub('PIL', pil_package)
_install_stub('PIL.Image', pil_image)
_install_stub('PIL.ImageTk', pil_imagetk)

tk_module = MagicMock()
ttk_module = MagicMock()
_install_stub('tkinter', tk_module)
_install_stub('tkinter.ttk', ttk_module)

from face_recognition_ad_system import FaceRecognitionAdSystem


@pytest.fixture(autouse=True)
def reset_env():
    """確保每次測試都在乾淨的環境變數狀態下執行。"""
    original_environ = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_environ)


def _build_system(monkeypatch, tmp_path: Path, env_content: str):
    env_path = tmp_path / ".env"
    env_path.write_text(env_content, encoding="utf-8")
    monkeypatch.setenv("FACE_AD_ENV_FILE", str(env_path))
    monkeypatch.setattr(FaceRecognitionAdSystem, "connect_database", lambda self: None)
    monkeypatch.setattr(FaceRecognitionAdSystem, "load_face_data", lambda self: None)
    monkeypatch.setattr(FaceRecognitionAdSystem, "init_camera", lambda self: None)
    system = FaceRecognitionAdSystem()
    return system, env_path


def test_env_file_overrides_defaults(monkeypatch, tmp_path):
    system, env_path = _build_system(
        monkeypatch,
        tmp_path,
        """
FACE_AD_DB_HOST=example.com
FACE_AD_DB_USER=demo
FACE_AD_DB_PASSWORD=secret
FACE_AD_DB_NAME=demo_db
FACE_AD_DB_PORT=13306
FACE_AD_CAMERA_SOURCE=1
FACE_AD_CAMERA_WIDTH=800
FACE_AD_CAMERA_HEIGHT=600
FACE_AD_CAMERA_FPS=25
FACE_AD_RECOGNITION_TOLERANCE=0.45
FACE_AD_RECOGNITION_MODEL=cnn
"""
    )

    assert system.env_file_path == env_path
    assert system.config["database"]["host"] == "example.com"
    assert system.config["database"]["user"] == "demo"
    assert system.config["database"]["password"] == "secret"
    assert system.config["database"]["database"] == "demo_db"
    assert system.config["database"]["port"] == 13306
    assert system.config["camera"]["source"] == 1
    assert system.config["camera"]["width"] == 800
    assert system.config["camera"]["height"] == 600
    assert system.config["camera"]["fps"] == 25
    assert system.config["recognition"]["tolerance"] == pytest.approx(0.45)
    assert system.config["recognition"]["model"] == "cnn"


def test_invalid_env_values_keep_defaults(monkeypatch, tmp_path):
    system, _ = _build_system(
        monkeypatch,
        tmp_path,
        """
FACE_AD_CAMERA_WIDTH=invalid
FACE_AD_CAMERA_HEIGHT=oops
FACE_AD_CAMERA_FPS=broken
FACE_AD_RECOGNITION_TOLERANCE=nan
"""
    )

    assert system.config["camera"]["width"] == 640
    assert system.config["camera"]["height"] == 480
    assert system.config["camera"]["fps"] == 30
    assert system.config["recognition"]["tolerance"] == pytest.approx(0.6)


def test_camera_source_as_path(monkeypatch, tmp_path):
    system, _ = _build_system(
        monkeypatch,
        tmp_path,
        """
FACE_AD_CAMERA_SOURCE=/dev/video1
"""
    )

    assert system.config["camera"]["source"] == "/dev/video1"
