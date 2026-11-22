# 贡献指南

## 报告漏译和兼容性问题

请提供 Hub 版本、macOS 版本、芯片架构、界面位置，以及预期结果和实际结果。漏译可用短标签、自己的描述或文字指纹定位。截图请裁剪到相关控件，并遮盖账号、会话、文件路径和地址栏。问题报告和拉取请求应保持应用文件、完整界面原文、登录信息和个人数据在本机。

## 添加译文

1. 在本机确认目标是产品控件，避开消息、命令、文件内容及用户自行输入的值。
2. 运行 `python3 tools/fingerprint.py`，粘贴控件文本，按 Control-D 结束输入。输出为 UTF-16 长度和 SHA-256。
3. 在 `translations.json` 的对应控件组加入指纹和中文译文。设置正文放在 `web.settings`。控件识别规则放在 `i18n_zh.js`，同一个英文词在不同控件上可以对应不同译法。
4. 运行 `python3 -B -m unittest discover -s tests` 和 `./install.sh --check`。如有实机测试，请说明验证过的版本和入口。

原生针对本地 JavaScript 字符串字面量使用 `--native-literal`，Electron 菜单标签使用 `--menu-label`，托盘计数字段使用 `--tray-expression`。这些模式只输出 SHA-256，输入和原版应用留在你的电脑上。公开测试使用原创的模拟菜单和 DOM 数据。
