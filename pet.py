#!/usr/bin/env python3
import argparse
import base64
import fcntl
import hashlib
import html
import json
import os
import plistlib
import shlex
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.local_config import APP_STATE, appearance_lock, read_object, revision, write_object
from tools.orbit_events import hook, send

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "dist"
APP = BUILD / "Orbit Pet.app"
EXAMPLE = ROOT / "pet/examples/gugugaga-slate"
ACTIVE = APP_STATE / "active-pet.json"
PET_FILES = ("pet.json", "atlas.png")
HOOK_NAME = "antigravity-hub-tools-pet"
EVENTS = ("idle", "thinking", "done", "error")
LEGACY_HOOK_SCRIPT = Path(os.environ.get("AGY_ORBIT_HOOK_SCRIPT", str(ROOT / "pet.py"))).absolute()
HOOK_SCRIPT = APP_STATE / "orbit_events.py"


def hook_commands():
    def handler(event):
        command = shlex.join([sys.executable, "-I", "-B", str(HOOK_SCRIPT), event])
        return [{"type": "command", "command": command, "timeout": 12}]

    return {"PreInvocation": handler("think"), "Stop": handler("stop")}


def is_our_hook(candidate):
    if not isinstance(candidate, dict) or set(candidate) - {"PreInvocation", "Stop", "enabled"}:
        return False
    for event, argument in (("PreInvocation", "think"), ("Stop", "stop")):
        try:
            handler, = candidate[event]
            command = shlex.split(handler["command"])
        except (KeyError, TypeError, ValueError, AttributeError):
            return False
        current = command[1:] == ["-I", "-B", str(HOOK_SCRIPT), argument]
        legacy_args = command[2:] if command[1:2] == ["-B"] else command[1:]
        legacy = legacy_args == [str(LEGACY_HOOK_SCRIPT), "hook", argument]
        if not (current or legacy):
            return False
    return True


def install_hook_script():
    source = (ROOT / "tools/orbit_events.py").read_bytes()
    if revision(HOOK_SCRIPT) is not None and HOOK_SCRIPT.read_bytes() == source:
        return
    HOOK_SCRIPT.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=HOOK_SCRIPT.parent, prefix=".orbit-hook-") as temporary:
        staged = Path(temporary) / HOOK_SCRIPT.name
        staged.write_bytes(source)
        staged.chmod(0o600)
        os.replace(staged, HOOK_SCRIPT)


def configure(workspace, enabled):
    workspace = workspace.resolve(strict=True)
    if not workspace.is_dir() or (workspace / ".agents").is_symlink():
        raise ValueError("需要有效的本地工作区目录，且 .agents 不能是符号链接。")
    config = workspace / ".agents/hooks.json"
    old = revision(config)
    hooks = read_object(config) if old is not None else {}
    existing = hooks.get(HOOK_NAME)
    if HOOK_NAME in hooks and not is_our_hook(existing):
        raise ValueError("同名 Hook 属于其他源码目录或已有自定义配置，请先在原目录停用它。")
    if enabled:
        install_hook_script()
        commands = hook_commands()
        if existing == commands:
            return config
        hooks[HOOK_NAME] = commands
    elif HOOK_NAME in hooks:
        del hooks[HOOK_NAME]
    else:
        return config
    write_object(config, hooks, old)
    return config


def build():
    if sys.platform != "darwin":
        raise ValueError("菜单栏工作台和桌宠需要 macOS。")
    if sys.version_info < (3, 9):
        raise ValueError("菜单栏工作台和桌宠需要 Python 3.9 或更高版本。")
    BUILD.mkdir(exist_ok=True)
    with (BUILD / ".orbit-build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _build_locked()


def _build_locked():
    sources = [ROOT / "pet" / name for name in ("main.swift", "Assets.swift", "Activity.swift", "Workbench.swift")]
    manifest = ROOT / "pet/Info.plist"
    assets = [EXAMPLE / name for name in PET_FILES]
    workbench_files = [ROOT / name for name in (
        "pack.py", "pet.py", "theme.py", "tools/local_config.py", "tools/orbit_events.py",
        "packs/fjord/pack.json", "packs/fjord/wallpaper.jpg",
    )] + assets
    driver = json.dumps({"checkout": str(ROOT), "python": sys.executable}).encode("utf-8")
    fingerprint = hashlib.sha256(
        driver + b"".join(path.read_bytes() for path in [*sources, manifest, *workbench_files])
    ).hexdigest()
    build_mark = APP / "Contents/Resources/source.sha256"
    executable = APP / "Contents/MacOS/orbit-pet"
    if executable.is_file() and os.access(executable, os.X_OK) and build_mark.is_file() and build_mark.read_text() == fingerprint:
        return APP
    if APP.exists() and send("ping", "manual"):
        raise ValueError("请从菜单栏退出正在运行的桌宠，再构建新版工作台。")
    compiler = subprocess.run(["/usr/bin/xcrun", "--find", "swiftc"], capture_output=True)
    if compiler.returncode != 0:
        raise ValueError("找不到 Swift 编译器。请在终端运行 xcode-select --install，安装完成后重试。")
    print("正在本机编译菜单栏工作台和桌宠…", file=sys.stderr)
    with tempfile.TemporaryDirectory(dir=BUILD, prefix=".orbit-build-") as staging:
        candidate = Path(staging) / APP.name
        contents = candidate / "Contents"
        (contents / "MacOS").mkdir(parents=True)
        default_pet = contents / "Resources/DefaultPet"
        default_pet.mkdir(parents=True)
        (contents / "Info.plist").write_bytes(plistlib.dumps(plistlib.loads(manifest.read_bytes())))
        for asset in assets:
            (default_pet / asset.name).write_bytes(asset.read_bytes())
        for file in workbench_files:
            bundled = contents / "Resources/Workbench" / file.relative_to(ROOT)
            bundled.parent.mkdir(parents=True, exist_ok=True)
            bundled.write_bytes(file.read_bytes())
        (contents / "Resources/WorkbenchDriver.json").write_bytes(driver)
        subprocess.run(["/usr/bin/xcrun", "swiftc", "-O", "-module-cache-path", BUILD / ".swift-cache",
                        *sources, "-o", contents / "MacOS/orbit-pet"], check=True)
        (contents / "Resources/source.sha256").write_text(fingerprint)
        subprocess.run(["/usr/bin/codesign", "--sign", "-", "--force", candidate], check=True)
        previous = Path(staging) / "previous.app"
        if APP.exists():
            APP.rename(previous)
        try:
            candidate.rename(APP)
        except OSError:
            if previous.exists():
                previous.rename(APP)
            raise
    return APP


def asset_tool(*args, quiet=False):
    installed = os.environ.get("AGY_ORBIT_ASSET_BINARY")
    executable = Path(installed) if installed else build() / "Contents/MacOS/orbit-pet"
    subprocess.run([executable, *args], check=True,
                   stdout=subprocess.DEVNULL if quiet else None)


def create_pet(source, output, name, sheet, keep_background):
    output = output.resolve()
    if output.exists():
        raise ValueError(f"请选择尚不存在的桌宠包目录：{output}")
    if sheet and keep_background:
        raise ValueError("四姿势图集需要透明背景。")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".orbit-import-") as temporary:
        candidate = Path(temporary) / "pet"
        candidate.mkdir()
        asset_tool("--prepare-pet", source.resolve(strict=True), candidate, name,
                   "poses" if sheet else "portrait", "keep" if keep_background else "auto")
        if output.exists():
            raise ValueError(f"桌宠包目录刚被创建：{output}")
        candidate.rename(output)
    return output


def package_bytes(package):
    data = {}
    for filename, limit in (("pet.json", 4096), ("atlas.png", 8 * 1024 * 1024)):
        path = package / filename
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise ValueError(f"桌宠包文件无效：{filename}")
        data[filename] = path.read_bytes()
    return data


def stage_pet(package):
    files = package_bytes(package)
    identifier = hashlib.sha256(b"".join(files.values())).hexdigest()
    library = APP_STATE / "Pets"
    library.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = library / identifier
    with tempfile.TemporaryDirectory(dir=library, prefix=".orbit-verify-") as temporary:
        candidate = Path(temporary) / "pet"
        candidate.mkdir()
        for filename, data in files.items():
            (candidate / filename).write_bytes(data)
        asset_tool("--validate-pet", candidate)
        if not target.exists():
            try:
                candidate.rename(target)
            except FileExistsError:
                if package_bytes(target) != files:
                    raise
        if package_bytes(target) != files:
            raise ValueError("已安装的同内容桌宠目录已被修改。")
    return identifier


def use_pet(package):
    identifier = stage_pet(package)
    with appearance_lock():
        write_object(ACTIVE, {"id": identifier}, revision(ACTIVE))
    send("reload", "manual")


def preview_pet(package, output):
    asset_tool("--validate-pet", package)
    files = package_bytes(package)
    manifest = json.loads(files["pet.json"])
    name = html.escape(manifest["name"])
    atlas = base64.b64encode(files["atlas.png"]).decode("ascii")
    preview = (ROOT / "pet/preview.html").read_text(encoding="utf-8")
    mode = "poses" if manifest["layout"] == "poses" else "portrait"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(preview.replace("__ATLAS__", atlas).replace("__MODE__", mode)
                      .replace("__PET_NAME__", name), encoding="utf-8")
    return output.resolve()


def main():
    parser = argparse.ArgumentParser(description="构建、启动或连接 Antigravity Hub 桌宠。")
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("build", "start", "stop", "reset"):
        commands.add_parser(name)
    create = commands.add_parser("create", help="由本地图片制作桌宠包")
    create.add_argument("image", type=Path)
    create.add_argument("output", type=Path)
    create.add_argument("--name", required=True)
    create.add_argument("--sheet", action="store_true", help="2×2 的透明四姿势图集")
    create.add_argument("--keep-background", action="store_true")
    preview = commands.add_parser("preview", help="生成离线预览")
    preview.add_argument("package", type=Path, nargs="?", default=EXAMPLE)
    preview.add_argument("--out", type=Path, default=BUILD / "pet-preview.html")
    preview.add_argument("--open", action="store_true")
    use = commands.add_parser("use", help="切换到指定桌宠包")
    use.add_argument("package", type=Path)
    demo = commands.add_parser("demo")
    demo.add_argument("state", choices=EVENTS)
    for name in ("enable", "disable"):
        command = commands.add_parser(name)
        command.add_argument("workspace", type=Path)
    delivery = commands.add_parser("hook")
    delivery.add_argument("event", choices=("think", "stop"))
    args = parser.parse_args()
    if args.action in ("build", "start"):
        app = build()
        if args.action == "start":
            subprocess.run(["/usr/bin/open", "-a", app], check=True)
        print(app)
    elif args.action == "stop":
        print("已请求退出桌宠。" if send("quit", "manual") else "桌宠未运行。")
    elif args.action == "create":
        print(create_pet(args.image, args.output, args.name, args.sheet, args.keep_background))
    elif args.action == "preview":
        preview = preview_pet(args.package, args.out)
        if args.open:
            subprocess.run(["/usr/bin/open", preview], check=True)
        print(preview)
    elif args.action == "use":
        use_pet(args.package)
        print("桌宠已切换。")
    elif args.action == "reset":
        with appearance_lock():
            write_object(ACTIVE, {}, revision(ACTIVE))
        send("reload", "manual")
        print("已切回内置示例。")
    elif args.action == "demo":
        if not send(args.state, "manual"):
            raise ValueError("请先用 python3 pet.py start 启动桌宠。")
    elif args.action == "hook":
        hook(args.event)
    else:
        print(configure(args.workspace, args.action == "enable"))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"桌宠操作未完成：{error}")
