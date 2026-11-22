import hashlib
import json
import struct
from pathlib import Path

HUB = Path("/Applications/Antigravity.app")
ASAR_PATH = Path("Contents/Resources/app.asar")
PLIST_PATH = Path("Contents/Info.plist")
CHANGED = {f"dist/{name}.js" for name in ("preload", "main", "menu", "updater", "tray", "utils")}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_asar(path):
    data = path.read_bytes()
    header_size, json_size = struct.unpack_from("<I4xI", data, 4)
    header = data[16:16 + json_size]
    payload_start = 8 + header_size

    def files(tree, prefix=""):
        for name, entry in tree.items():
            name = prefix + name
            if "files" in entry:
                yield from files(entry["files"], name + "/")
            elif "offset" in entry:
                start = payload_start + int(entry["offset"])
                stop = start + entry["size"]
                if start < payload_start or stop < start or stop > len(data):
                    raise ValueError(f"ASAR 条目超出范围：{name}")
                yield name, (False, sha256(data[start:stop]), bool(entry.get("executable")))
            elif entry.get("unpacked"):
                external = Path(f"{path}.unpacked") / name
                yield name, (True, sha256(external.read_bytes()), bool(entry.get("executable")))
            else:
                raise ValueError(f"不支持的 ASAR 条目：{name}")

    return {
        "sha256": sha256(data),
        "header_sha256": sha256(header),
    }, dict(files(json.loads(header)["files"]))
