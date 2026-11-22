# 皮肤和桌宠

## 皮肤

先安装当前版本的 Hub 补丁并重开 Hub，即可运行下方命令切换壁纸和玻璃材质。Hub 2.34.0 已实测导入本地图片、即时切换、聊天输入区和侧栏磨砂。打开设置时侧栏和内容区恢复实色，返回聊天后壁纸和磨砂恢复。其他版本的显示范围仍待验证。

换肤时，侧栏使用连续的玻璃底色，壁纸延伸到输入框边缘。关掉皮肤后恢复客户端的默认外观。

```bash
python3 theme.py list
python3 theme.py apply jade
python3 theme.py apply dusk --image "/path/to/wallpaper.jpg" --veil 78 --blur 12
python3 theme.py restore
```

内置青瓷云海、暮蓝星环和纸灯余晖三组原创渐变。背景支持本地 PNG 和 JPEG，输入上限 10 MiB，转换后最长边不超过 2560 像素。遮罩 `--veil` 为 45–96，数值越高，面板越接近原色。模糊 `--blur` 为 0–24 像素。选择原色外观执行 `restore`。彻底移除皮肤运行时可退出 Hub 并使用仓库根目录的 `./restore.sh`。

复制一份预设即可制作分享用的纯数据主题。

```bash
python3 theme.py show jade > my-skin.json
python3 theme.py apply ./my-skin.json --image "/path/to/wallpaper.png"
```

主题 JSON 可以编辑名称、调色、遮罩和模糊。分享自有图片时将图片和 JSON 一同提供。运行时只接受预设渐变、受限的颜色及数字和本地转换图片。皮肤设置保存在 `~/Library/Application Support/Antigravity Hub Tools/skin.json`。

## 桌宠

桌宠需 Python 3.9+ 与 Apple Command Line Tools。首次启动从 Swift 源码在本机编译，应用产物位于 `dist/Orbit Pet.app`。可以直接双击编译后的应用。用菜单栏图标隐藏、显示或退出，也可以拖动小窗换位置。内置「咕咕嘎嘎 · 极地向导」，也可[用自己的图片做一只桌宠](PET_STUDIO.md)。

单击桌宠打开活动面板，查看活动会话数和最近三条状态的时间。面板可暂停或恢复跟随、打招呼并播放庆祝动作、打开 Hub。活动记录仅保存在当前桌宠进程内。打开 Hub 后可继续阅读和操作会话。

```bash
python3 pet.py start
python3 pet.py demo thinking
python3 pet.py stop
```

独立演示支持 `idle`、`thinking`、`done`、`error`。要跟随 Hub 的活动，为指定工作区启用 Hook。

```bash
python3 pet.py start
python3 pet.py enable "/path/to/workspace"
# 关闭该项目的联动
python3 pet.py disable "/path/to/workspace"
```

Hub 通过项目的 `.agents/hooks.json` 加载 `PreInvocation` 和 `Stop`。如果 Hub 提示审查，可在设置的「扩展 / Hooks」里确认。Hook 通过本机套接字传递状态和临时会话标识，桌宠关闭时也能正常返回。Hub 2.34.0 已用真实会话验证从思考到完成。当前 Hook 脚本位于 `~/Library/Application Support/Antigravity Hub Tools`。如果旧版 Hook 仍指向原解压目录，切换源码目录前先在原目录停用联动，再从新源码启用。

## 设计参考

皮肤交互参考了 Codex Dream Skin 的壁纸、玻璃材质、主题导入和恢复原貌，运行时适配本项目的 Hub 补丁。桌宠参考了 Agent Pets 的独立窗口与可选状态联动。 [Codex Dream Skin](https://github.com/Fei-Away/Codex-Dream-Skin) · [Agent Pets](https://github.com/ifBars/agent-pets) · [Antigravity Hooks](https://antigravity.google/docs/hooks)
