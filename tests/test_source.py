import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from native_patch import patch_main, patch_menu, patch_tray, patch_updater
from tools.fingerprint import fingerprint
from tools.package_release import FILES, package

ROOT = Path(__file__).resolve().parents[1]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class SourceTests(unittest.TestCase):
    def test_fingerprint_preserves_javascript_string_length(self):
        self.assertEqual(fingerprint(" 🧪 Widget \n"), "9:" + digest("🧪 Widget"))
        self.assertEqual(fingerprint("token ", "menu_label"), digest("token "))

    def test_catalogue_contains_only_fingerprints_and_translations(self):
        data = json.loads((ROOT / "translations.json").read_text())
        web = data["web"]
        for table in [web["settings"], web["settingsTitles"], *web["controls"].values()]:
            self.assertTrue(table)
            self.assertTrue(all(re.fullmatch(r"\d+:[0-9a-f]{64}", key) for key in table))
            self.assertTrue(all(isinstance(value, str) and value for value in table.values()))
        self.assertTrue(all(re.fullmatch(r"\d+:[0-9a-f]{64}", key)
                            for key in web["patterns"].values()))
        native = data["native"]
        for table in [native["menu"], native["tray"], native["updater"], *native["main"].values()]:
            self.assertTrue(table)
            self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", key) for key in table))

    def test_scope_and_duplicate_native_match(self):
        original = """
const panels = {
    label: 'Example panel',
    title: 'Example panel',
};
"""
        rule = {"label": {digest("'Example panel'"): "示例面板"}}
        patched = patch_main(original, rule)
        self.assertIn('label: "示例面板"', patched)
        self.assertIn("title: 'Example panel'", patched)
        with self.assertRaises(ValueError):
            patch_main(original + original, rule)
        with self.assertRaises(ValueError):
            patch_main(original.replace("Example", "Other"), rule)

    def test_menu_helper_uses_only_target_registration(self):
        source = """
function setupApplicationMenu(selected) {
    host.Menu.setApplicationMenu(selected);
}
function unrelated(fallback) {
    host.Menu.setApplicationMenu(fallback);
}
"""
        helper = (ROOT / "menu_zh.js").read_text()
        patched = patch_menu(source, {digest("Example entry"): "示例项目"}, helper)
        self.assertEqual(patched.count("hubTranslateNativeMenu(selected);"), 1)
        self.assertNotIn("hubTranslateNativeMenu(fallback);", patched)
        self.assertNotIn("Example entry", patched)

    def test_buttons_template_and_count_keep_data(self):
        source = """
const panel = {
    label: `Visit ${record.title}`,
    buttons: ['Example yes', 'Example no'],
};
"""
        rules = {
            "label": {digest("`Visit ${record.title}`"): "访问 ${value} ` "},
            "buttons": {digest("['Example yes', 'Example no']"): ["同意", "拒绝"]},
        }
        patched = patch_main(source, rules)
        self.assertIn(r"访问 \${value} \` ${record.title}", patched)
        self.assertIn('["同意", "拒绝"]', patched)
        expression = 'total ? `${total} examples` : "idle"'
        count = patch_tray(f"  meter.label = {expression};",
                           {digest(expression): ["离线", " 个示例"]})
        self.assertIn('`${total} 个示例`', count)
        update = patch_updater('  phases["Example"] = "Waiting for demo";',
                               {digest('"Waiting for demo"'): "等待示例"})
        self.assertIn('"等待示例"', update)

    def test_release_archive_is_reproducible_and_source_only(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            result = package(directory)
            first = result.read_bytes()
            self.assertEqual(package(directory).read_bytes(), first)
            with ZipFile(result) as archive:
                files = {name.split("/", 1)[1] for name in archive.namelist()}
                self.assertEqual(files, set(FILES))
                self.assertTrue(all(not name.endswith((".app", ".asar", ".dmg", ".zip")) for name in files))
                for shell in ("install.sh", "restore.sh"):
                    item = next(info for info in archive.infolist() if info.filename.endswith(f"/{shell}"))
                    self.assertTrue(item.external_attr >> 16 & 0o111)
            self.assertIn(hashlib.sha256(first).hexdigest(), (directory / "SHA256SUMS.txt").read_text())


if __name__ == "__main__":
    unittest.main()
