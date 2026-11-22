import argparse
import hashlib
import sys


def fingerprint(text, mode="web"):
    if mode == "tray_expression":
        text = " ".join(text.split())
    elif mode == "web":
        text = text.strip()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if mode != "web":
        return digest
    length = len(text.encode("utf-16-le")) // 2
    return f"{length}:{digest}"


def main():
    parser = argparse.ArgumentParser(description="从标准输入读入本地标签，仅输出匹配指纹。")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--menu-label", action="store_const", dest="mode", const="menu_label")
    modes.add_argument("--native-literal", action="store_const", dest="mode", const="native_literal")
    modes.add_argument("--tray-expression", action="store_const", dest="mode", const="tray_expression")
    args = parser.parse_args()
    # Remove the terminal's final line ending while retaining spaces used by native labels.
    original = sys.stdin.read().rstrip("\r\n")
    if not original:
        parser.error("请输入文本")
    print(fingerprint(original, args.mode or "web"))


if __name__ == "__main__":
    main()
