#!/usr/bin/env python3
import argparse
import base64
import json
import re
import subprocess
import tempfile
from pathlib import Path

from tools.local_config import APP_STATE, appearance_lock, read_object, revision, write_object

PRESETS = Path(__file__).resolve().parent / "themes/presets.json"
ACTIVE = APP_STATE / "skin.json"
ART = ("jade", "dusk", "sand")
IMAGE_LIMIT = 10 * 1024 * 1024


def validate_skin(value):
    if not isinstance(value, dict) or set(value) != {"name", "art", "tint", "veil", "blur"}:
        raise ValueError("主题需要 name、art、tint、veil、blur 五个字段。")
    if (not isinstance(value["name"], str) or not 1 <= len(value["name"].strip()) <= 48 or
            not value["name"].isprintable() or value["art"] not in ART):
        raise ValueError("主题名称或内置背景样式无效。")
    if not isinstance(value["tint"], str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value["tint"]):
        raise ValueError("tint 必须是 #RRGGBB。")
    for key, lower, upper in (("veil", 45, 96), ("blur", 0, 24)):
        if type(value[key]) is not int or not lower <= value[key] <= upper:
            raise ValueError(f"{key} 必须是 {lower}–{upper} 的整数。")
    return dict(value)


def read_background(path):
    if not path.is_file() or path.stat().st_size > IMAGE_LIMIT:
        raise ValueError("请选择 10 MiB 以内的本地 PNG 或 JPEG。")
    with path.open("rb") as image:
        signature = image.read(12)
    if not (signature.startswith(b"\x89PNG\r\n\x1a\n") or signature.startswith(b"\xff\xd8\xff")):
        raise ValueError("背景只接受 PNG 或 JPEG。")
    with tempfile.TemporaryDirectory(prefix="agy-hub-wallpaper-") as directory:
        target = Path(directory) / "wallpaper.jpg"
        subprocess.run(["/usr/bin/sips", "-s", "format", "jpeg", "-s", "formatOptions", "85",
                        "-Z", "2560", path.resolve(), "--out", target], check=True, capture_output=True)
        data = target.read_bytes()
    if not data.startswith(b"\xff\xd8\xff") or len(data) > 3 * 1024 * 1024:
        raise ValueError("无法生成有效的主题背景。")
    return base64.b64encode(data).decode("ascii")


def selected_skin(reference, presets):
    return validate_skin(presets[reference] if reference in presets else read_object(Path(reference)))


def main():
    parser = argparse.ArgumentParser(description="管理 Antigravity Hub 的壁纸与磨砂玻璃皮肤。")
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("list", "status", "restore"):
        commands.add_parser(action)
    show = commands.add_parser("show")
    show.add_argument("skin", help="内置主题 ID 或本地 JSON 文件")
    apply = commands.add_parser("apply")
    apply.add_argument("skin", help="内置主题 ID 或本地 JSON 文件")
    apply.add_argument("--image", type=Path, help="可选的本地 PNG 或 JPEG 壁纸")
    apply.add_argument("--veil", type=int, help="覆盖面板遮罩强度（45–96）")
    apply.add_argument("--blur", type=int, help="覆盖背景模糊强度（0–24）")
    args = parser.parse_args()
    presets = read_object(PRESETS)

    if args.action == "list":
        for key, preset in presets.items():
            print(key, validate_skin(preset)["name"])
    elif args.action == "status":
        active = read_object(ACTIVE) if revision(ACTIVE) is not None else {}
        print(active.get("name", "默认外观"))
    elif args.action == "restore":
        with appearance_lock():
            write_object(ACTIVE, {}, revision(ACTIVE))
        print("已关闭皮肤。")
    else:
        skin = selected_skin(args.skin, presets)
        if args.action == "show":
            print(json.dumps(skin, ensure_ascii=False, indent=2))
            return
        for key in ("veil", "blur"):
            value = getattr(args, key)
            if value is not None:
                skin[key] = value
        skin = validate_skin(skin)
        if args.image:
            skin["image"] = read_background(args.image)
        with appearance_lock():
            write_object(ACTIVE, skin, revision(ACTIVE))
        print(f"已选择 {skin['name']}。安装过本工具补丁的 Hub 会应用皮肤。")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"主题操作未完成：{error}")
