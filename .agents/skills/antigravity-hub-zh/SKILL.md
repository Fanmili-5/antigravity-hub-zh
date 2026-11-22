---
name: antigravity-hub-zh
description: Checks compatibility, installs an authorized Chinese UI patch, or restores the Google-signed original for the macOS Antigravity Hub. Use when asked to inspect, localize, or restore Antigravity.app.
---

# Antigravity Hub 中文补丁

Use the checkout containing this skill, its root `README.md`, and `install.sh` / `restore.sh`. Run commands from that checkout on the user's Mac. If only this Skill was copied into another workspace, use the local release folder supplied by the user. Read the project's README for supported versions and signing implications.

- **Check compatibility.** Run `./install.sh --check`. Hub can stay open. A successful build does not establish that all UI labels translate. If the check fails, report the first actionable error and the installed Hub version.
- **Install.** When the user asks to install, complete the check first. Run `./install.sh` after Hub has fully quit. The installer checks the source signature and retains a complete Google-signed backup. Verify that the installer succeeded before opening the Hub again.
- **Restore.** When the user asks to restore, run `./restore.sh` after Hub has fully quit and verify its reported Google signature check. Open Hub again only as part of the requested restart.

The target is `/Applications/Antigravity.app`. When responding inside that same app, stop at the preflight and give the terminal command that can run after it closes. For an incompatible build preserve the current app and use the user's build output to diagnose the mismatch.
