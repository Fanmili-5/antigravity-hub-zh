#!/usr/bin/env python3
import argparse
import ctypes
import fcntl
import os
import plistlib
import re
import subprocess
import tempfile
from pathlib import Path

from asar_patch import ASAR_PATH, HUB, PLIST_PATH, read_asar, sha256
from build_patch import ASAR_VERSION, build

TEAM_ID = "EQHXZ8M8AV"


def bundle_info(app):
    info = plistlib.loads((app / PLIST_PATH).read_bytes())
    if info.get("CFBundleIdentifier") != "com.google.antigravity":
        raise ValueError(f"目标必须是 Antigravity Hub：{app}")
    return info


def verify(app, *, official=False):
    command = ["/usr/bin/codesign", "--verify", "--deep", "--strict"]
    if official:
        command.extend(["-R", f'=anchor apple generic and certificate leaf[subject.OU] = "{TEAM_ID}"'])
    subprocess.run([*command, app], check=True)


def signing_info(app):
    return subprocess.run(
        ["/usr/bin/codesign", "-dv", "--verbose=2", app], capture_output=True,
        text=True, check=True,
    ).stderr


def is_official(app):
    return f"TeamIdentifier={TEAM_ID}" in signing_info(app).splitlines()


def require_closed(app):
    executable = app / "Contents/MacOS/Antigravity"
    matches = subprocess.run(
        ["/usr/bin/pgrep", "-fq", "^" + re.escape(str(executable)) + "([[:space:]]|$)"]
    )
    if matches.returncode == 0:
        raise ValueError("请先完全退出 Antigravity Hub，再运行脚本。")
    if matches.returncode != 1:
        raise ValueError("无法确认 Hub 是否正在运行，请在 macOS 终端运行脚本。")


def swap_paths(first, second):
    # RENAME_SWAP replaces both directory entries in one filesystem operation.
    rename = ctypes.CDLL(None, use_errno=True).renameatx_np
    rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    rename.restype = ctypes.c_int
    if rename(-2, os.fsencode(first), -2, os.fsencode(second), 0x00000002):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def prepare_patch(original, staged, manifest, archive):
    subprocess.run(["/usr/bin/ditto", original, staged], check=True)
    (staged / ASAR_PATH).write_bytes(archive)
    subprocess.run([
        "/usr/libexec/PlistBuddy", "-c",
        "Set :ElectronAsarIntegrity:Resources/app.asar:hash " + manifest["patched"]["header_sha256"],
        staged / PLIST_PATH,
    ], check=True)
    subprocess.run([
        "/usr/bin/codesign", "--force", "--sign", "-", "--preserve-metadata=identifier,entitlements",
        staged,
    ], check=True)
    verify(staged)


def base_app(app, backup):
    original_is_active = is_official(app)
    original = app if original_is_active else backup
    if not original.is_dir():
        raise ValueError(f"未找到可验证的 Google 原版 Hub：{original}")
    verify(original, official=True)
    if not original_is_active:
        active_info = bundle_info(app)
        if (active_info["CFBundleVersion"] != bundle_info(original)["CFBundleVersion"] or
                "Signature=adhoc" not in signing_info(app).splitlines()):
            raise ValueError("当前安装与已有原版备份不对应。")
        verify(app)
        _, active_files = read_asar(app / ASAR_PATH)
        if "dist/i18n_zh.js" not in active_files:
            raise ValueError("当前 Hub 由其他方式修改，请先恢复其官方原版。")
    return original


def install(app, backup, state, original, manifest, archive):
    original_is_active = original == app
    if not original_is_active and sha256((app / ASAR_PATH).read_bytes()) == manifest["patched"]["sha256"]:
        print("当前补丁已安装，磁盘签名验证通过。")
        return

    with tempfile.TemporaryDirectory(prefix="staging-", dir=state) as work:
        staged = Path(work) / app.name
        prepare_patch(original, staged, manifest, archive)
        verify(original, official=True)
        if (bundle_info(original)["CFBundleVersion"] != manifest["bundle_version"] or
                sha256((original / ASAR_PATH).read_bytes()) != manifest["original"]["sha256"]):
            raise ValueError("构建期间原版 Hub 已变化，请重新运行安装。")
        if original_is_active:
            if backup.exists():
                # Keep any prior official backup, such as one from before an app update.
                if is_official(backup):
                    saved = Path(tempfile.mkdtemp(prefix="official-", dir=state))
                    os.rename(backup, saved / app.name)
                else:
                    os.rename(backup, Path(work) / "previous.app")
            os.rename(staged, backup)
            staged = backup
        require_closed(app)
        swap_paths(app, staged)
    print(f"补丁已安装。原版完整备份：{backup}")


def restore(app, backup):
    if is_official(app):
        verify(app, official=True)
        print("当前 Hub 已是 Google 签名的官方原版。")
        return
    if not backup.is_dir():
        raise ValueError(f"找不到完整原版备份：{backup}")
    current, original = bundle_info(app), bundle_info(backup)
    if current["CFBundleVersion"] != original["CFBundleVersion"]:
        raise ValueError("原版备份与当前 Hub 版本不同，已停止还原。")
    verify(backup, official=True)
    require_closed(app)
    swap_paths(app, backup)
    verify(app, official=True)
    print("已还原完整官方 Hub，Google 签名验证通过。")


def main():
    parser = argparse.ArgumentParser(description="用本机的原版 Antigravity Hub 构建或还原中文补丁。")
    parser.add_argument("action", choices=["install", "restore"])
    parser.add_argument("--app", type=Path, default=HUB, help="目标 Antigravity Hub 应用包")
    parser.add_argument("--check", action="store_true", help="仅检查兼容性并试构建，不改动应用")
    parser.add_argument("--asar-cli", type=Path, help="可选的本机 @electron/asar CLI 路径")
    args = parser.parse_args()
    if args.action == "restore" and args.check:
        parser.error("--check 仅用于 install")
    app = args.app.resolve()
    bundle_info(app)
    state = app.parent / ("." + app.name + "-i18n")
    backup = state / "rollback.app"

    if not args.check:
        require_closed(app)
    if args.action == "install":
        original = base_app(app, backup)
        command = ["node", args.asar_cli] if args.asar_cli else ["npx", "--yes", ASAR_VERSION]
        archive, manifest = build(original, command)
        if args.check:
            print("兼容性构建通过。应用未切换。安装后的界面覆盖仍需实机确认。")
            return

    state.mkdir(mode=0o700, exist_ok=True)
    with (state / "deployment.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == "install":
            if base_app(app, backup) != original:
                raise ValueError("另一安装进程已切换应用，请重新运行。")
            install(app, backup, state, original, manifest, archive)
        else:
            restore(app, backup)


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"操作未完成：{error}")
