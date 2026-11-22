---
name: antigravity-hub-tools
description: Manage macOS Antigravity Hub localization, appearance packs, and Orbit desktop pets. Use for previewing, importing, applying or exporting a pack, checking customizations, or turning a picture into a pet.
---

# Antigravity Hub 社区工具集

Run the commands from the source checkout on the user's Mac. Read `README.md` and `docs/CUSTOMIZATIONS.md` for the relevant module. If this skill was copied into another workspace, locate the tools checkout supplied by the user.

- **Chinese UI and skin runtime.** Use `./install.sh --check` for compatibility. To apply the patch, fully quit Hub, run `./install.sh`, and relaunch after success. To switch back to the signed official app, fully quit Hub and run `./restore.sh`. If operating inside that same Hub, perform the check and give the external terminal command for after it closes.
- **Wallpaper and glass.** List curated skins with `python3 theme.py list`. Confirm a skin's settings with `python3 theme.py show jade`. With the runtime already installed, use `python3 theme.py apply jade` for live switching. Add `--image "/absolute/path/to/wallpaper.jpg"`, `--veil 80`, or `--blur 12` only when relevant to the request. `python3 theme.py restore` turns off the skin.
- **Desktop pet.** Use `python3 pet.py start` to build and open Orbit Pet, `python3 pet.py demo thinking` for a local demo, and `python3 pet.py stop` to exit it. Enable or remove the official lifecycle hook only for the workspace requested by the user, using `python3 pet.py enable "/absolute/path/to/workspace"` or `disable` with the same workspace.
- **Create a pet.** Read `docs/PET_STUDIO.md`. Run `python3 pet.py create "/path/to/picture.png" "./new-pet" --name "Name"` with the user-supplied image and an unused output directory. Add `--sheet` for a square transparent four-pose sheet. If asked to generate the four poses, use the assistant's image generation tool if available and follow the grid order in the guide. Run `python3 pet.py preview "./new-pet"` and share the resulting local preview. Apply with `python3 pet.py use "./new-pet"` when the user requests installation. `python3 pet.py reset` switches back to the bundled example.
- **Workbench and appearance packs.** Read `docs/WORKBENCH.md`. Open the native workbench with `python3 pack.py workbench`. Use `python3 pack.py preview fjord` (or a local ZIP) and show the returned HTML file for a preview. Use `python3 pack.py import "/path/to/pack.zip"` to validate and register a pack. Only apply when asked using `python3 pack.py apply fjord` or the ID printed by import. Use `python3 pack.py export fjord "/path/to/new.zip"` or `python3 pack.py export current "/path/to/new.zip" --name "Name"` for a local export. `python3 pack.py restore` reverts an active pack. For the live board, open the workbench and select 会话活动.

Use the same commands as manual users and report their exact success or failure. Keep theme files declarative and only import wallpaper paths supplied or approved by the user.
