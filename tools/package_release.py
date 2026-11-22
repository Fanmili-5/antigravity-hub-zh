import argparse
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0-alpha.7"
PNG_FILES = (
    "docs/images/localization-original.png",
    "docs/images/localization-zh.png",
    "docs/images/fjord-live.png",
    "docs/images/orbit-activity.png",
    "pet/examples/gugugaga/atlas.png",
    "pet/examples/gugugaga-slate/atlas.png",
)
JPEG_FILES = ("packs/fjord/wallpaper.jpg", "docs/images/fjord-preview.jpg", "docs/images/toolkit-overview.jpg")
FILES = (
    ".gitignore", ".github/ISSUE_TEMPLATE/feedback.yml", ".github/workflows/ci.yml",
    ".agents/skills/antigravity-hub-zh/SKILL.md",
    ".agents/skills/antigravity-hub-tools/SKILL.md",
    "LICENSE", "README.md", "CONTRIBUTING.md", "CHANGELOG.md",
    "docs/README.en.md", "docs/RELEASE_NOTES.md", "docs/CUSTOMIZATIONS.md", "docs/PET_STUDIO.md", "docs/WORKBENCH.md",
    "asar_patch.py", "build_patch.py", "manage_patch.py", "native_patch.py",
    "install.sh", "restore.sh", "i18n_zh.js", "menu_zh.js", "translations.json",
    "theme.py", "themes/presets.json", "themes/runtime.js",
    "pet.py", "pet/main.swift", "pet/Assets.swift", "pet/Activity.swift", "pet/Workbench.swift", "pet/Info.plist", "pet/preview.html",
    "pack.py", "packs/preview.html", "packs/fjord/pack.json", "packs/fjord/README.md",
    "pet/examples/gugugaga/README.md", "pet/examples/gugugaga/pet.json",
    "pet/examples/gugugaga-slate/README.md", "pet/examples/gugugaga-slate/pet.json",
    "tests/test_source.py", "tests/test_customizations.py", "tests/test_packs.py",
    "tests/test_orbit_events.py", "tests/test_orbit_step_limit.py", "tests/test_skin.cjs", "tests/ActivityTests.swift",
    "tools/fingerprint.py", "tools/local_config.py", "tools/orbit_events.py", "tools/package_release.py",
    *JPEG_FILES,
    *PNG_FILES,
)


def package(output):
    prefix = f"antigravity-hub-zh-v{VERSION}"
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f"{prefix}-source.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(FILES):
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"发行文件必须是普通文件：{name}")
            body = path.read_bytes()
            if name in PNG_FILES:
                if not body.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError(f"图片必须是 PNG：{name}")
            elif name in JPEG_FILES:
                if not body.startswith(b"\xff\xd8\xff"):
                    raise ValueError(f"图片必须是 JPEG：{name}")
            else:
                body.decode("utf-8")
            info = ZipInfo(f"{prefix}/{name}")
            info.create_system = 3
            mode = 0o100755 if name in {"install.sh", "restore.sh"} else 0o100644
            info.external_attr = mode << 16
            archive.writestr(info, body, compress_type=ZIP_DEFLATED)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {archive_path.name}\n")
    return archive_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="在本地生成源码 ZIP 和 SHA-256 清单。")
    parser.add_argument("--output-dir", type=Path, required=True)
    print(package(parser.parse_args().output_dir))
