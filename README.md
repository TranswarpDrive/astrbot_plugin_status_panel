# astrbot_plugin_status_panel

适用于 AstrBot 的 QQ 设备状态面板插件，面向 OneBot v11 / NapCat。

## 功能

- 在私聊或 AstrBot 白名单群里发送 `\status` 获取当前运行 AstrBot 设备的状态。
- 支持纯文本模式和文转图图片模式。
- 图片模式会展示机器人头像和昵称、CPU、GPU、RAM、硬盘占用与读写速度、活跃进程、设备运行时长、AstrBot 运行时长等信息。
- 默认使用当前机器人 QQ 头像，也支持在插件配置里自定义昵称、上传头像文件或填写头像 URL。
- 支持 `\status image` 与 `\status text` 临时覆盖默认回复模式。

## 指令

- `\status`
- `\status image`
- `\status text`
- `\status help`

另外也兼容 `/status`。

## 配置项

安装后在 AstrBot 面板打开此插件的配置页，可以设置：

- `reply_mode`：默认回复模式，可选 `image` 或 `text`
- `bot_nickname`：图片顶部显示的昵称
- `avatar_url`：自定义头像 URL
- `avatar_file`：自定义上传头像，优先级高于 `avatar_url`
- `process_count`：活跃进程展示数量

## 说明

- 上传头像功能依赖 AstrBot `4.13.0` 及以上版本，因为用到了官方 `file` 类型配置项。
- 图片模式依赖 AstrBot 自带的文转图能力；如果渲染失败，插件会自动回退为纯文本回复。
- GPU 占用优先通过 NVML 读取；如果设备没有提供遥测数据，插件仍会尽量显示 GPU 名称。

## 在 AstrBot 面板里安装

### 方式一：上传压缩包

1. 打开 AstrBot WebUI。
2. 进入 `插件` 页面。
3. 点击右下角 `+`。
4. 选择 `文件上传`。
5. 上传这个插件目录打包得到的 zip，或者把整个目录复制到 `AstrBot/data/plugins/astrbot_plugin_status_panel`。
6. 等待 AstrBot 自动安装 `requirements.txt` 里的依赖。
7. 打开插件卡片，按需配置头像、昵称、默认模式，然后重载插件。

### 方式二：放进本地插件目录

AstrBot 官方插件开发文档说明，本地插件可以直接放在 `AstrBot/data/plugins/<plugin_name>` 下，然后在 WebUI 插件页重载。

示例：

```bash
cd AstrBot/data/plugins
git clone <你的仓库地址> astrbot_plugin_status_panel
```

然后回到 AstrBot WebUI 的 `插件` 页面重载即可。

## 依赖

- `psutil`
- `pynvml`
