# 用图片做桌宠

桌宠在 macOS 上独立运行。需要 Python 3.9+ 和 Apple Command Line Tools。单张带背景的照片可在 macOS 14+ 通过系统 Vision 本地抠图。

## 从一张图做起

```bash
python3 pet.py create "/path/to/cat.jpg" ./my-cat --name "我的猫"
python3 pet.py preview ./my-cat --open
python3 pet.py use ./my-cat
python3 pet.py start
```

支持静态 PNG、JPEG、WebP，单张输入不超过 24 MiB。透明图会自动裁到角色边缘、居中并对齐底部。普通照片会尝试分离前景，推荐主体完整、与背景有明显区分的图。想保留原背景可加 `--keep-background`。预览页面离线运行，可点按四种状态，切换深浅背景检查边缘。

单张图模式使用同一个角色图，待机轻晃、思考歪头、完成跳跃、需查看轻抖。挑战不同的表情或姿势时，可以换用四姿势图集。

## 让四个状态有各自的姿势

可以自己绘制四格插画，或使用你有权分享的角色图。图集应为正方形、真正透明的 PNG 或 WebP，每格保留边距并画出全身。四张图从左到右、从上到下依次是待机、思考、完成、需查看。请保持脸、衣服、镜头和人物比例一致。 [内置示例](../pet/examples/gugugaga/README.md)

```bash
python3 pet.py create "/path/to/poses.png" ./my-pet --name "我的桌宠" --sheet
python3 pet.py preview ./my-pet --open
python3 pet.py use ./my-pet
```

项目会裁切四格并统一尺度，生成可分享的 `pet.json` 和透明 `atlas.png`。分享自己有权分发的图片即可。接收者用 `use` 加载整个包，无需再次生图。运行时会根据状态选用对应姿势，并播放轻晃、歪头、跳跃或轻抖。

## 内置示例与还原

```bash
python3 pet.py preview --open
python3 pet.py reset
python3 pet.py start
```

默认示例是石墨配色的「咕咕嘎嘎 · 极地向导」。桌宠已启动时，`use` 和 `reset` 会即时切换角色。点桌宠可以看最近活动、打招呼和打开 Hub，拖动可移动位置。要让它跟随代理活动，按[桌宠联动指南](CUSTOMIZATIONS.md#桌宠)启用指定项目的 Hook。
