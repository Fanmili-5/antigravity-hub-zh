import json
import fcntl
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

APP_STATE = Path.home() / "Library/Application Support/Antigravity Hub Tools"


@contextmanager
def appearance_lock():
    APP_STATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (APP_STATE / "appearance.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def read_object(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"需要普通 JSON 文件：{path}")

    def pairs(items):
        result = dict(items)
        if len(result) != len(items):
            raise ValueError(f"JSON 有重复键：{path}")
        return result

    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    if not isinstance(result, dict):
        raise ValueError(f"需要 JSON 对象：{path}")
    return result


def revision(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"需要普通配置文件：{path}")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def write_object(path, value, expected):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if expected is not None else 0o600
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), mode)
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if revision(path) != expected:
            raise ValueError(f"配置已被其他程序修改，请重试：{path}")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
