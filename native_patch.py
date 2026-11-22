import json
import re

from asar_patch import sha256

JS_STRING = r"""(?:'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\\n]|\\.)*`)"""


def replace_matching(source, pattern, translations, description, rewrite, fingerprint=lambda text: text):
    matches = {}
    for match in re.finditer(pattern, source, flags=re.MULTILINE):
        digest = sha256(fingerprint(match["value"]).encode())
        if digest not in translations:
            continue
        if digest in matches:
            raise ValueError(f"{description} 的同一位置匹配多次")
        matches[digest] = match
    if matches.keys() != translations.keys():
        raise ValueError(f"{description} 存在未匹配的修改位置")
    edits = sorted(((match, translations[key]) for key, match in matches.items()),
                   key=lambda edit: edit[0].start("value"), reverse=True)
    for match, value in edits:
        start, end = match.span("value")
        source = source[:start] + rewrite(match["value"], value) + source[end:]
    return source


def javascript_string(value):
    return json.dumps(value, ensure_ascii=False)


def escape_template_text(value):
    return value.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def translate_literal(original, translation):
    if original.startswith("`"):
        interpolation = original.find("${")
        if interpolation < 0:
            raise ValueError("模板字符串缺少预期的插值")
        return "`" + escape_template_text(translation) + original[interpolation:]
    return javascript_string(translation)


def patch_main(source, rules):
    for prop, translations in rules.items():
        value = rf"\[\s*{JS_STRING}\s*,\s*{JS_STRING}\s*\]" if prop == "buttons" else JS_STRING
        pattern = rf"^[ \t]*{re.escape(prop)}\s*:\s*(?P<value>{value})"
        source = replace_matching(source, pattern, translations, f"主进程菜单 {prop}",
                                  translate_literal)
    return source


def patch_tray(source, rules):
    def tray_label(original, translations):
        count = re.search(r"\${\s*([A-Za-z_$][\w$]*)\s*}", original)
        if not count:
            raise ValueError("未找到托盘计数变量")
        count = count[1]
        empty, suffix = translations
        return f"{count} > 0 ? `${{{count}}}{escape_template_text(suffix)}` : {javascript_string(empty)}"

    pattern = r"^[ \t]*[A-Za-z_$][\w$]*\.label\s*=\s*(?P<value>[^;]+);"
    return replace_matching(source, pattern, rules, "托盘菜单", tray_label,
                            lambda value: " ".join(value.split()))


def patch_updater(source, rules):
    pattern = rf"^[ \t]*[^\n;]+\]\s*=\s*(?P<value>{JS_STRING});"
    return replace_matching(source, pattern, rules, "更新菜单", translate_literal)


def patch_menu(source, labels, helper):
    # Restrict injection to Electron's menu registration within the host's setup function.
    setup = re.search(r"^function\s+setupApplicationMenu\s*\([^)]*\)\s*\{(?P<body>[\s\S]*?)^\}",
                      source, flags=re.MULTILINE)
    if not setup:
        raise ValueError("未找到原生菜单初始化函数")
    body = setup["body"]
    calls = list(re.finditer(
        r"^(?P<indent>[ \t]*)[\w$.]+\.setApplicationMenu\(\s*(?P<arg>[\w$]+)\s*\)\s*;",
        body, flags=re.MULTILINE,
    ))
    if len(calls) != 1:
        raise ValueError("无法唯一定位原生菜单注册位置")
    call = calls[0]
    index = setup.start("body") + call.start()
    line = f'{call["indent"]}hubTranslateNativeMenu({call["arg"]});\n'
    if helper.count("/* MENU_LABELS */ {}") != 1:
        raise ValueError("原生菜单模板异常")
    return source[:index] + line + source[index:] + "\n" + helper.replace(
        "/* MENU_LABELS */ {}", javascript_string(labels), 1
    )


def patch_native(dist, rules, helper):
    for file, patcher in (
        ("main", patch_main), ("tray", patch_tray), ("updater", patch_updater),
        ("menu", lambda source, labels: patch_menu(source, labels, helper)),
    ):
        path = dist / f"{file}.js"
        path.write_text(patcher(path.read_text(), rules[file]))
