# v0.1.0-alpha.7

Antigravity Hub 中文工具箱的首个公开版本。适用于 macOS 上的 Antigravity Hub。

- **中文界面**覆盖菜单、会话入口、模型、主要设置和常见扩展。用户在本机生成补丁，`./restore.sh` 可恢复完整的 Google 签名原版。
- **壁纸和磨砂**支持本地图片、预设和套装 ZIP。菜单栏工作台可以预览、导入、切换和导出。
- **桌宠**可独立运行。内置「咕咕嘎嘎 · 极地向导」，也支持用户自己的图片和可选的真实会话联动。

在 Apple Silicon、macOS 26.5.1 上实测 Hub 2.34.0。其他版本可先做兼容检查。

```bash
./install.sh --check
```

下载 ZIP 和 `SHA256SUMS.txt`，在同一目录运行 `shasum -a 256 -c SHA256SUMS.txt`。安装、还原和独立桌宠入口见 [项目 README](../README.md)。
