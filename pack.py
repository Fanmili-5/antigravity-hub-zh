#!/usr/bin/env python3
import argparse
import base64
import binascii
import hashlib
import html
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

import pet
import theme
from tools.local_config import APP_STATE, appearance_lock, read_object, revision, write_object

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "packs/fjord"
LIBRARY = APP_STATE / "Packs"
SELECTION = APP_STATE / "active-pack.json"
LIMITS = {"pack.json": 8192, "wallpaper.jpg": 3 * 1024 * 1024,
          "pet/pet.json": 4096, "pet/atlas.png": 8 * 1024 * 1024}
REQUIRED = {"pack.json", "pet/pet.json", "pet/atlas.png"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def json_payload(data):
    def pairs(items):
        result = dict(items)
        if len(result) != len(items):
            raise ValueError("套装 JSON 有重复字段。")
        return result

    result = json.loads(data, object_pairs_hook=pairs)
    if not isinstance(result, dict):
        raise ValueError("套装清单必须是 JSON 对象。")
    return result


def name_value(name):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 48 or not name.isprintable():
        raise ValueError("套装名称须为 1–48 个可显示字符。")
    return name.strip()


def payload(manifest, picture, pet_files):
    skin = theme.validate_skin(manifest["skin"])
    entries = {"pet/" + name: blob for name, blob in pet_files.items()}
    if picture is not None:
        entries["wallpaper.jpg"] = picture
    index = {"version": 1, "name": name_value(manifest["name"]), "skin": skin,
             "sha256": {name: sha(blob) for name, blob in entries.items()}}
    return {"pack.json": json_bytes(index), **entries}


def verify_payload(entries):
    names = set(entries)
    if not REQUIRED <= names <= LIMITS.keys():
        raise ValueError("套装需要清单、桌宠图集及可选 JPEG 壁纸。")
    for name, data in entries.items():
        if not 0 < len(data) <= LIMITS[name]:
            raise ValueError(f"素材文件大小无效：{name}")
    index = json_payload(entries["pack.json"])
    checks = {key: sha(entries[key]) for key in entries if key != "pack.json"}
    if (set(index) != {"version", "name", "skin", "sha256"} or type(index["version"]) is not int or
            index["version"] != 1 or index["sha256"] != checks):
        raise ValueError("套装版本不受支持，或素材校验值不符。")
    pet_info = json_payload(entries["pet/pet.json"])
    if (set(pet_info) != {"version", "name", "layout"} or type(pet_info["version"]) is not int or
            pet_info["version"] != 1 or pet_info["layout"] not in ("poses", "portrait")):
        raise ValueError("桌宠清单格式不符。")
    name_value(index["name"])
    name_value(pet_info["name"])
    theme.validate_skin(index["skin"])
    if not entries["pet/atlas.png"].startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("桌宠图集必须是 PNG。")
    if "wallpaper.jpg" in entries and not entries["wallpaper.jpg"].startswith(b"\xff\xd8\xff"):
        raise ValueError("套装壁纸必须是 JPEG。")
    return index


def read_archive(path):
    if path.stat().st_size > sum(LIMITS.values()) + 4096:
        raise ValueError("套装 ZIP 超出大小限制。")
    with ZipFile(path) as archive:
        members = archive.infolist()
        names = {item.filename for item in members}
        if len(names) != len(members) or not REQUIRED <= names <= LIMITS.keys():
            raise ValueError("套装有重复、缺失或未知文件。")
        entries = {}
        for item in members:
            mode = (item.external_attr >> 16) & 0o170000
            if (mode not in (0, stat.S_IFREG) or item.flag_bits & 1 or
                    not 0 < item.file_size <= LIMITS[item.filename]):
                raise ValueError(f"套装文件无效：{item.filename}")
            with archive.open(item) as stream:
                entries[item.filename] = stream.read(LIMITS[item.filename] + 1)
    verify_payload(entries)
    return entries


def demo_payload():
    return payload(read_object(DEMO / "pack.json"), (DEMO / "wallpaper.jpg").read_bytes(),
                   pet.package_bytes(pet.EXAMPLE))


def write_entries(directory, entries):
    (directory / "pet").mkdir(parents=True)
    for name, data in entries.items():
        (directory / name).write_bytes(data)


def validate_images(directory):
    pet.asset_tool("--validate-pet", directory / "pet", quiet=True)
    picture = directory / "wallpaper.jpg"
    if picture.exists():
        pet.asset_tool("--validate-wallpaper", picture, quiet=True)


def package_id(entries):
    manifest = verify_payload(entries)
    return sha(json_bytes(manifest))


def read_directory(directory):
    entries = {}
    for key, limit in LIMITS.items():
        file = directory / key
        size = revision(file)
        if size is None and key == "wallpaper.jpg":
            continue
        if size is None or not 0 < file.stat().st_size <= limit:
            raise ValueError(f"套装库文件大小无效：{key}")
        entries[key] = file.read_bytes()
    verify_payload(entries)
    return entries


def lookup(reference):
    if reference == "fjord":
        return demo_payload()
    if re.fullmatch(r"[a-f0-9]{64}", reference):
        entries = read_directory(LIBRARY / reference)
        if package_id(entries) != reference:
            raise ValueError("已导入的套装已被修改，请重新导入。")
        return entries
    return read_archive(Path(reference))


def import_pack(path):
    entries = read_archive(path)
    identifier = package_id(entries)
    LIBRARY.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = LIBRARY / identifier
    with tempfile.TemporaryDirectory(dir=LIBRARY, prefix=".import-") as temp:
        candidate = Path(temp) / "pack"
        write_entries(candidate, entries)
        validate_images(candidate)
        with appearance_lock():
            if not target.exists():
                candidate.rename(target)
            else:
                lookup(identifier)
    return identifier


def state(path):
    return read_object(path) if revision(path) is not None else {}


def selection_matches(selection, skin, sprite):
    return selection.get("fingerprint") == sha(json_bytes([skin, sprite]))


def commit(triples):
    written = []
    try:
        for path, old, new in triples:
            expected = revision(path)
            write_object(path, new, expected)
            written.append((path, old, expected, revision(path)))
    except (OSError, ValueError):
        for path, old, previous, current in reversed(written):
            if previous is None and revision(path) == current:
                path.unlink()
            else:
                write_object(path, old, current)
        raise


def apply_pack(reference):
    if reference != "fjord" and not re.fullmatch(r"[a-f0-9]{64}", reference):
        raise ValueError("先导入 ZIP 再切换到该套装。")
    entries = lookup(reference)
    manifest = verify_payload(entries)
    with tempfile.TemporaryDirectory(prefix="agy-pack-apply-") as temporary:
        directory = Path(temporary) / "pack"
        write_entries(directory, entries)
        validate_images(directory)
        sprite_id = pet.stage_pet(directory / "pet")
    skin = manifest["skin"].copy()
    if "wallpaper.jpg" in entries:
        skin["image"] = base64.b64encode(entries["wallpaper.jpg"]).decode("ascii")
    sprite = {"id": sprite_id}
    with appearance_lock():
        old_skin, old_sprite, previous = (state(path) for path in (theme.ACTIVE, pet.ACTIVE, SELECTION))
        before = previous["before"] if selection_matches(previous, old_skin, old_sprite) else [old_skin, old_sprite]
        active = {"id": reference, "before": before, "fingerprint": sha(json_bytes([skin, sprite]))}
        commit(((theme.ACTIVE, old_skin, skin), (pet.ACTIVE, old_sprite, sprite), (SELECTION, previous, active)))
    pet.send("reload", "manual")
    return manifest["name"]


def restore_pack():
    with appearance_lock():
        skin, sprite, active = (state(path) for path in (theme.ACTIVE, pet.ACTIVE, SELECTION))
        if not selection_matches(active, skin, sprite):
            raise ValueError("当前外观没有可撤销的套装切换，或已单独修改壁纸或桌宠。")
        original_skin, original_sprite = active["before"]
        commit(((theme.ACTIVE, skin, original_skin), (pet.ACTIVE, sprite, original_sprite), (SELECTION, active, {})))
    pet.send("reload", "manual")


def current_payload(name):
    with appearance_lock():
        skin, sprite = state(theme.ACTIVE), state(pet.ACTIVE)
        if not skin:
            raise ValueError("请先选择一个皮肤，再导出当前组合。")
        encoded = skin.pop("image", None)
        if encoded is not None and (not isinstance(encoded, str) or len(encoded) > 4194304):
            raise ValueError("当前壁纸不符合套装格式。")
        picture = base64.b64decode(encoded, validate=True) if encoded is not None else None
        selection = sprite.get("id")
        if selection is not None and not re.fullmatch(r"[a-f0-9]{64}", selection):
            raise ValueError("当前桌宠标识无效。")
        folder = APP_STATE / "Pets" / selection if selection else pet.EXAMPLE
        entries = payload({"name": name or skin["name"], "skin": skin}, picture, pet.package_bytes(folder))
    verify_payload(entries)
    return entries


def export_pack(entries, path):
    verify_payload(entries)
    path = path.resolve()
    if path.suffix.lower() != ".zip":
        raise ValueError("导出文件请使用 .zip 后缀。")
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".agy-export-") as temporary:
        directory = Path(temporary) / "assets"
        write_entries(directory, entries)
        validate_images(directory)
        candidate = Path(temporary) / "pack.zip"
        with ZipFile(candidate, "w", compression=ZIP_DEFLATED) as archive:
            for name, data in sorted(entries.items()):
                entry = ZipInfo(name)
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, data, compress_type=ZIP_DEFLATED)
        os.link(candidate, path)


def preview_pack(entries, output):
    if output.suffix.lower() != ".html":
        raise ValueError("预览文件请使用 .html 后缀。")
    index = verify_payload(entries)
    with tempfile.TemporaryDirectory(prefix="agy-pack-preview-") as temporary:
        directory = Path(temporary) / "assets"
        write_entries(directory, entries)
        validate_images(directory)
    metadata = json_payload(entries["pet/pet.json"])
    skin = index["skin"]
    picture = base64.b64encode(entries.get("wallpaper.jpg", b"")).decode("ascii")
    atlas = base64.b64encode(entries["pet/atlas.png"]).decode("ascii")
    replacements = {"__NAME__": html.escape(index["name"]), "__PET__": html.escape(metadata["name"]),
                    "__PICTURE__": picture, "__ATLAS__": atlas, "__TINT__": skin["tint"],
                    "__BLUR__": str(skin["blur"]), "__VEIL__": str(skin["veil"] / 100),
                    "__LAYOUT__": metadata["layout"]}
    template = (ROOT / "packs/preview.html").read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = re.sub("|".join(replacements), lambda match: replacements[match[0]], template)
    output.write_text(result, encoding="utf-8")
    return output.resolve()


def describe(reference, entries, pet_dir, wallpaper):
    index = verify_payload(entries)
    if wallpaper and not wallpaper.is_file():
        wallpaper = None
    return {"id": reference, "name": index["name"], "skin": index["skin"], "petPath": str(pet_dir),
            "wallpaperPath": str(wallpaper) if wallpaper else None}


def library_status():
    entries = [describe("fjord", demo_payload(), pet.EXAMPLE, DEMO / "wallpaper.jpg")]
    if LIBRARY.is_dir():
        for folder in sorted(LIBRARY.iterdir(), key=lambda path: path.name):
            if folder.is_symlink() or not re.fullmatch(r"[a-f0-9]{64}", folder.name):
                continue
            try:
                files = lookup(folder.name)
                entries.append(describe(folder.name, files, folder / "pet", folder / "wallpaper.jpg"))
            except (OSError, ValueError):
                continue
    skin, sprite, linked = (state(path) for path in (theme.ACTIVE, pet.ACTIVE, SELECTION))
    active = linked.get("id") if selection_matches(linked, skin, sprite) else None
    return {"packs": entries, "active": active, "skin": skin.get("name")}


def main():
    parser = argparse.ArgumentParser(description="Antigravity Hub 外观套装。")
    commands = parser.add_subparsers(dest="action", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--json", action="store_true")
    inbound = commands.add_parser("import")
    inbound.add_argument("file", type=Path)
    for action in ("apply", "preview", "export"):
        command = commands.add_parser(action)
        command.add_argument("pack")
        if action == "preview":
            command.add_argument("--out", type=Path, default=ROOT / "dist/pack-preview.html")
            command.add_argument("--open", action="store_true")
        if action == "export":
            command.add_argument("file", type=Path)
            command.add_argument("--name", help="导出当前组合时使用的名称")
    commands.add_parser("restore")
    commands.add_parser("workbench")
    args = parser.parse_args()
    if args.action == "list":
        listing = library_status()
        if args.json:
            print(json.dumps(listing, ensure_ascii=False))
        else:
            for entry in listing["packs"]:
                print(entry["id"], entry["name"], "当前应用" if entry["id"] == listing["active"] else "")
    elif args.action == "import":
        print(import_pack(args.file))
    elif args.action == "apply":
        print(f"已应用 {apply_pack(args.pack)}")
    elif args.action == "restore":
        restore_pack()
        print("已恢复切换套装前的外观。")
    elif args.action == "preview":
        preview = preview_pack(lookup(args.pack), args.out)
        if args.open:
            subprocess.run(["/usr/bin/open", preview], check=True)
        print(preview)
    elif args.action == "export":
        entries = current_payload(args.name) if args.pack == "current" else lookup(args.pack)
        export_pack(entries, args.file)
        print(args.file.resolve())
    elif not pet.send("workbench", "manual"):
        subprocess.run(["/usr/bin/open", "-a", pet.build(), "--args", "--workbench"], check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, TypeError, RuntimeError, BadZipFile,
            binascii.Error, subprocess.CalledProcessError) as error:
        raise SystemExit(f"套装操作未完成：{error}")
