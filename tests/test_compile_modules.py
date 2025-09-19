import compileall
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    "facegen.py",
    "facecam.py",
    "faceme.py",
    "rollcall_edge.py",
    "face_recognition_ad_system.py",
    "face_register.py",
    "ad_manager.py",
]


def test_project_sources_compile():
    for module in MODULES:
        target = PROJECT_ROOT / module
        assert target.exists(), f"{module} 檔案不存在"
        compiled = compileall.compile_file(str(target), force=True, quiet=1)
        assert compiled, f"{module} 編譯失敗"
