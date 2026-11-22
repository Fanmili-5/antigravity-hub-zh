import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

import pack
from tools.local_config import read_object, revision, write_object


class PackTests(unittest.TestCase):
    def test_archive_must_be_a_regular_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            pipe = Path(temporary) / "stream.zip"
            os.mkfifo(pipe)
            with self.assertRaisesRegex(ValueError, "普通"):
                pack.read_archive(pipe)

    def test_export_never_follows_an_existing_destination_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            destination, target = folder / "alias.zip", folder / "missing.zip"
            destination.symlink_to(target)
            with self.assertRaises(FileExistsError):
                pack.export_pack(pack.demo_payload(), destination)
            self.assertFalse(target.exists())
            self.assertTrue(destination.is_symlink())

    def test_preview_handles_a_pack_without_a_wallpaper(self):
        files = pack.demo_payload()
        manifest = pack.verify_payload(files)
        manifest["name"] = "风格 <演示>"
        entries = pack.payload(manifest, None, {path.removeprefix("pet/"): files[path]
                                                  for path in ("pet/pet.json", "pet/atlas.png")})
        with tempfile.TemporaryDirectory() as temporary, patch.object(pack, "validate_images"):
            preview = pack.preview_pack(entries, Path(temporary) / "preview.html").read_text()
            self.assertIn("风格 &lt;演示&gt;", preview)
            self.assertIn(f'class="poses {manifest["skin"]["art"]} "', preview)
            self.assertNotIn("__WALLPAPER__", preview)

    def test_fixture_round_trips_and_reexports_identically(self):
        files = pack.demo_payload()
        self.assertEqual(pack.verify_payload(files)["name"], "峡湾 · 极地向导")
        with tempfile.TemporaryDirectory() as temporary, patch.object(pack, "validate_images"):
            first, second = (Path(temporary) / name for name in ("original.zip", "export.zip"))
            pack.export_pack(files, first)
            unpacked = pack.read_archive(first)
            self.assertEqual(unpacked, files)
            pack.export_pack(unpacked, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with self.assertRaises(FileExistsError):
                pack.export_pack(files, first)

    def test_import_rejects_unknown_duplicates_and_symlinks(self):
        files = pack.demo_payload()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "bad.zip"
            for bad_entry in ("../hook.sh", "assets/unknown.sh"):
                with ZipFile(target, "w") as archive:
                    for filename, source in files.items():
                        archive.writestr(filename, source)
                    archive.writestr(bad_entry, b"unsafe")
                with self.assertRaises(ValueError):
                    pack.read_archive(target)
            with ZipFile(target, "w") as archive:
                for filename, source in files.items():
                    if filename == "wallpaper.jpg":
                        item = ZipInfo(filename)
                        item.create_system = 3
                        item.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(item, source)
                    else:
                        archive.writestr(filename, source)
            with self.assertRaises(ValueError):
                pack.read_archive(target)
            with self.assertRaises(ValueError):
                pack.json_payload(b'{"version":1,"version":2}')
            with self.assertRaises(ValueError):
                pack.verify_payload({**files, "wallpaper.jpg": b"altered"})

    def test_failed_appearance_switch_restores_previous_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            skin, pet, marker = (path / f"{name}.json" for name in ("skin", "pet", "pack"))
            originals = {skin: {"name": "original"}, pet: {"id": "old"}}
            for file, original in originals.items():
                write_object(file, original, None)

            def fail_last(file, value, expected):
                if file == marker:
                    raise OSError("test interruption")
                write_object(file, value, expected)

            with patch.object(pack, "write_object", side_effect=fail_last):
                with self.assertRaises(OSError):
                    pack.commit(((skin, originals[skin], {"name": "new"}),
                                 (pet, originals[pet], {"id": "new"}), (marker, {}, {"id": "new"})))
            for file, original in originals.items():
                self.assertEqual(read_object(file), original)
            self.assertIsNone(revision(marker))

    def test_activity_packet_projects_exclude_private_payload(self):
        from tools.orbit_events import workspace_label

        payload = {"workspacePaths": ["/local/path/项目甲"], "lastUserInput": "private", "transcriptPath": "/private"}
        metadata = workspace_label(payload)
        self.assertEqual(metadata["label"], "项目甲")
        self.assertNotIn("private", json.dumps(metadata))
        self.assertNotIn("/local/path", json.dumps(metadata))
        self.assertNotEqual(metadata["group"], workspace_label({"workspacePaths": ["/different/项目甲"]})["group"])
