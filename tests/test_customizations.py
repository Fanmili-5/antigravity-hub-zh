import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_patch import patch_skin
from pet import HOOK_NAME, configure
from theme import selected_skin, validate_skin
from tools.local_config import read_object

ROOT = Path(__file__).resolve().parents[1]


class CustomizationTests(unittest.TestCase):
    def test_all_presets_and_invalid_css_values(self):
        presets = read_object(ROOT / "themes/presets.json")
        self.assertEqual(set(presets), {"jade", "dusk", "sand"})
        for key, preset in presets.items():
            self.assertEqual(selected_skin(key, presets), preset)
        with self.assertRaises(ValueError):
            validate_skin({**presets["jade"], "tint": "red; background: url(https://example.org)"})
        with self.assertRaises(ValueError):
            validate_skin({**presets["jade"], "blur": True})

    def test_hook_migrates_from_checkout_and_preserves_other_entries(self):
        with tempfile.TemporaryDirectory(prefix="workspace with spaces ") as temporary:
            workspace = Path(temporary)
            agents = workspace / ".agents"
            agents.mkdir()
            hooks = agents / "hooks.json"
            other = {"linter": {"PostToolUse": []}}
            events = {"PreInvocation": "think", "Stop": "stop"}
            old = {
                event: [{"command": shlex.join([sys.executable, "-B", str(ROOT / "pet.py"), "hook", arg])}]
                for event, arg in events.items()
            }
            hooks.write_text(json.dumps({**other, HOOK_NAME: old}))
            helper = workspace / "Application Support/orbit_events.py"
            with patch("pet.HOOK_SCRIPT", helper):
                self.assertEqual(configure(workspace, True), hooks.resolve())
                active = read_object(hooks)
                self.assertEqual(active["linter"], other["linter"])
                self.assertEqual(helper.read_bytes(), (ROOT / "tools/orbit_events.py").read_bytes())
                for event, arg in events.items():
                    command = shlex.split(active[HOOK_NAME][event][0]["command"])
                    self.assertEqual(command[1:], ["-I", "-B", str(helper), arg])
                configure(workspace, False)
            self.assertEqual(read_object(hooks), other)
            original = {**other, HOOK_NAME: {"PreInvocation": []}}
            hooks.write_text(json.dumps(original))
            with self.assertRaises(ValueError):
                configure(workspace, False)
            self.assertEqual(read_object(hooks), original)

    def test_skin_wires_only_the_known_hub_window(self):
        with tempfile.TemporaryDirectory() as temporary:
            dist = Path(temporary)
            source = (
                "function createWindow(url, storage, options) {\n"
                "    const hubContents = getHubWebContents(win);\n"
                "    registerWindowWebContents(win, hubContents);\n}\n"
                "function createOtherWindow() {\n"
                "    registerWindowWebContents(win, hubContents);\n}\n"
            )
            utils = dist / "utils.js"
            utils.write_text(source)
            patch_skin(dist)
            self.assertEqual(utils.read_text().count('.attachSkin(hubContents, url)'), 1)
            self.assertEqual((dist / "agy-skin.js").read_bytes(), (ROOT / "themes/runtime.js").read_bytes())


if __name__ == "__main__":
    unittest.main()
