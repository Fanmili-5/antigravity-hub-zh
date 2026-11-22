#!/usr/bin/env python3
import json
import plistlib
import re
import subprocess
import tempfile
from pathlib import Path

from asar_patch import ASAR_PATH, CHANGED, PLIST_PATH, read_asar
from native_patch import patch_native

PROJECT = Path(__file__).resolve().parent
ASAR_VERSION = "@electron/asar@4.3.2"
ADDED = {"dist/i18n_zh.js", "dist/agy-skin.js"}


def build(app, asar_cli):
    info = plistlib.loads((app / PLIST_PATH).read_bytes())
    version = info.get("CFBundleVersion")
    if info.get("CFBundleIdentifier") != "com.google.antigravity" or not version:
        raise ValueError("未识别到 macOS Antigravity Hub。")
    print(f"正在检查本机 Hub {version} 并生成汉化补丁。", flush=True)

    original = app / ASAR_PATH
    base, original_files = read_asar(original)
    integrity = info.get("ElectronAsarIntegrity", {}).get("Resources/app.asar", {})
    if ("dist/i18n_zh.js" in original_files or integrity.get("algorithm") != "SHA256" or
            base["header_sha256"] != integrity.get("hash")):
        raise ValueError("原版 ASAR 的完整性检查失败，或此版本使用了不同的打包方式。")

    catalogue = json.loads((PROJECT / "translations.json").read_text())
    engine = (PROJECT / "i18n_zh.js").read_text()
    marker = "/* CATALOGUE */ {}"
    if engine.count(marker) != 1:
        raise ValueError("Web 翻译模板异常。")
    engine = engine.replace(marker, json.dumps(catalogue["web"], ensure_ascii=False, indent=4), 1)
    native_template = (PROJECT / "menu_zh.js").read_text()

    with tempfile.TemporaryDirectory(prefix="agy-i18n-build-") as build_dir:
        work = Path(build_dir)
        unpacked = work / "extracted"
        patched = work / "app.asar.patched"
        subprocess.run([*asar_cli, "extract", original, unpacked], check=True)
        dist = unpacked / "dist"
        check_web_entry(dist)
        (dist / "i18n_zh.js").write_text(engine)
        preload = dist / "preload.js"
        preload.write_text(preload.read_text() + "\n" + engine)
        patch_skin(dist)
        try:
            patch_native(dist, catalogue["native"], native_template)
        except ValueError as error:
            raise ValueError(f"{version} 原生菜单结构与当前规则不兼容：{error}") from error
        for path in CHANGED | ADDED:
            subprocess.run(["node", "--check", unpacked / path], check=True)

        subprocess.run([*asar_cli, "pack", unpacked, patched,
                        "--unpack-dir", "node_modules/chrome-devtools-mcp"], check=True)
        output, patched_files = read_asar(patched)
        changed = {p for p in original_files.keys() | patched_files.keys()
                   if original_files.get(p) != patched_files.get(p)}
        if changed != CHANGED | ADDED:
            raise ValueError(f"补丁文件变化超出预期：{sorted(changed)}")

        manifest = {
            "bundle_version": info["CFBundleVersion"],
            "original": base, "patched": output,
        }
        archive = patched.read_bytes()
    print(f"本机补丁生成并校验通过，设置词典含 {len(catalogue['web']['settings'])} 条。", flush=True)
    return archive, manifest


def check_web_entry(dist):
    # These anchors keep the injected preload on the known Hub window and loopback origin.
    utils = (dist / "utils.js").read_text()
    constants = (dist / "constants.js").read_text()
    has_preload = re.search(r"""\bpreload\s*:[^;\n]+['"]preload\.js['"]""", utils)
    isolated = re.search(r"\bcontextIsolation\s*:\s*true", utils)
    no_node = re.search(r"\bnodeIntegration\s*:\s*false", utils)
    origin = re.search(r"""\bWINDOW_ORIGIN\s*=\s*['"]https://127\.0\.0\.1['"]""", constants)
    if not all((has_preload, isolated, no_node, origin)):
        raise ValueError("当前 Hub 的 preload 或页面入口已变化，需要更新注入规则。")


def patch_skin(dist):
    path = dist / "utils.js"
    source = path.read_text()
    window = re.search(r"^function createWindow\(url, [^\n]+\) \{[\s\S]*?^\}", source, re.MULTILINE)
    if not window:
        raise ValueError("无法定位 Hub 窗口，当前版本暂不兼容皮肤。")
    body = window[0]
    anchors = list(re.finditer(r"^(?P<indent>[ \t]*)registerWindowWebContents\(win, hubContents\);[ \t]*$",
                              body, re.MULTILINE))
    if len(anchors) != 1 or not re.search(r"\bconst hubContents = getHubWebContents\(win\);", body):
        raise ValueError("无法验证皮肤所需的 Hub 页面入口。")
    anchor, = anchors
    index = window.start() + anchor.start()
    line = f'{anchor["indent"]}require("./agy-skin.js").attachSkin(hubContents, url);\n'
    path.write_text(source[:index] + line + source[index:])
    (dist / "agy-skin.js").write_bytes((PROJECT / "themes/runtime.js").read_bytes())
