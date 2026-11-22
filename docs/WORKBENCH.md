# 菜单栏工作台

在 macOS 上从项目目录运行以下命令。首次运行需要 Python 3.9+ 和 Xcode Command Line Tools，会在本机编译桌宠和工作台。

```bash
python3 pack.py workbench
```

以后可从菜单栏的星形图标选择「打开工作台」。应用套装时，桌宠会立即切换，壁纸会由已安装本项目补丁的 Hub 实时载入。只想查看效果时，可以在套装库选择一项并预览。

## 试用峡湾套装

1. 在「外观套装」选中「峡湾 · 极地向导」。右侧预览壁纸、磨砂设置和桌宠。
2. 点「应用套装」同时切换。需要撤回时，从「更多」点「撤销套装切换」。
3. 用「导出套装」保存 ZIP，再从「导入套装」选回这个 ZIP。导入后选中预览，点应用才会切换。
4. 用自己的壁纸和桌宠组合时，从「更多」点「导出当前组合」。

套装只含版本、名称、外观参数、可选 JPEG 和桌宠图集。导入时验证允许的文件、大小、SHA-256 和图像格式。重叠套装切换可撤回到本次连续切换前的外观。若之后单独更换了壁纸或桌宠，最新组合由用户保留，之前的撤回记录失效。

## 终端与 Skill

```bash
python3 pack.py preview fjord --open
python3 pack.py export fjord ./fjord.zip
python3 pack.py import ./fjord.zip
python3 pack.py list
python3 pack.py apply fjord
python3 pack.py restore
```

`import` 输出套装标识。把 `apply` 的 `fjord` 换成该标识即可应用导入版。也可以用 `preview ./fjord.zip` 在导入前生成离线预览。通过 `export current ./my-pack.zip --name "我的套装"` 保存当前壁纸和桌宠。导出路径须为新 ZIP。

打开此仓库后，可以对支持 Skill 的助手说「用 antigravity-hub-tools 预览峡湾套装，然后导出到这个目录」。菜单栏和 Skill 调用同一套本地命令。

## 会话活动

在「会话活动」选择工作区启用联动，也可以执行 `python3 pet.py enable "/path/to/project"`。在这些工作区开始会话，工作台会显示按工作区分组的会话、运行或结束状态、持续时间和最后更新时间。标题使用简短会话标识，事件仅在当前桌宠进程内保留，结束后保留最多一小时。运行中的会话若超过十五分钟无新事件会从列表过期，收到下一条事件后重新显示。

Hub 状态通过官方项目级 Hook 传来。启用范围以用户选定的工作区为准。可从界面停用联动，或执行 `python3 pet.py disable "/path/to/project"`。

联动脚本保存在用户的 `~/Library/Application Support/Antigravity Hub Tools` 目录。之前已配置旧版联动的工作区，可重新点「启用工作区」或重跑 `pet.py enable` 更新 Hook。
