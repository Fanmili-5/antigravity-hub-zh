import base64
import hashlib
import json
import os
import socket
import stat
import sys
from pathlib import Path

MAX_EVENT_BYTES = 1024 * 1024


def socket_path():
    parent = Path(f"/tmp/agy-hub-pet-{os.getuid()}")
    info = parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("桌宠通信目录权限不正确。")
    return parent / "events.sock"


def send(state, session, project=None):
    try:
        suffix = ""
        if project is not None:
            metadata = json.dumps(project, ensure_ascii=False).encode("utf-8")
            suffix = " " + base64.b64encode(metadata).decode("ascii")
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as channel:
            channel.settimeout(0.15)
            channel.sendto(f"{state} {session}{suffix}".encode("ascii"), str(socket_path()))
        return True
    except (OSError, ValueError):
        return False


def workspace_label(data):
    paths = data.get("workspacePaths")
    if not isinstance(paths, list):
        return None
    for path in paths:
        if not isinstance(path, str) or not 0 < len(path) <= 4096 or "\x00" in path:
            continue
        workspace = Path(path)
        try:
            encoded_path = str(workspace).encode("utf-8")
        except UnicodeEncodeError:
            continue
        name = "".join(character for character in workspace.name if character.isprintable()).strip()[:40]
        return {"group": hashlib.sha256(encoded_path).hexdigest()[:20], "label": name or "工作区"}
    return None


def hook(event):
    response = {"decision": ""} if event == "stop" else {}
    try:
        raw = sys.stdin.buffer.read(MAX_EVENT_BYTES + 1)
        data = json.loads(raw) if len(raw) <= MAX_EVENT_BYTES else None
        session = data.get("conversationId") if isinstance(data, dict) else None
        if isinstance(session, str) and 0 < len(session) <= 256:
            identifier = hashlib.sha256(session.encode()).hexdigest()[:20]
            if event == "think" or data.get("fullyIdle") is False:
                state = "thinking"
            elif (
                event == "stop"
                and data.get("fullyIdle") is True
                and data.get("terminationReason") == "max_steps_exceeded"
            ):
                state = "error"
            else:
                state = "error" if data.get("error") or data.get("terminationReason") == "error" else "done"
            send(state, identifier, workspace_label(data))
    except (ValueError, RecursionError):
        pass
    print(json.dumps(response))


if __name__ == "__main__":
    hook(sys.argv[1])
