# astrbot_plugin_status_panel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: AstrBot](https://img.shields.io/badge/AstrBot-Plugin-4ea1ff)](https://github.com/TranswarpDrive/astrbot_plugin_status_panel)
[![Adapter: OneBot v11](https://img.shields.io/badge/Adapter-OneBot%20v11-2dbb7f)](https://docs.astrbot.app/platform/aiocqhttp.html)

一个适用于 **AstrBot** 的设备状态面板插件，面向 **NapCat / OneBot v11** 的 QQ 机器人。

Bot 加载这个插件后，你可以在 **AstrBot 白名单群** 或 **私聊** 中发送 `\status`，让机器人返回当前运行 AstrBot 的那台设备的实时状态。插件支持：

- 纯文本回复
- 文转图图片回复
- 机器人头像和昵称自定义
- 自动读取 CPU / GPU / RAM / 磁盘 / 活跃进程 / 运行时长等信息

如果你更喜欢可视化效果，插件会调用 **AstrBot 自带的 text-to-image / html_render 能力**，生成一张更适合在 QQ 中查看的状态卡片。

## 功能特性

- 支持 **QQ 私聊** 和 **AstrBot 白名单群聊**
- 兼容 **NapCat + OneBot v11**
- 指令简单：`\status`
- 支持默认模式设置，也支持每次调用时临时切换文本或图片模式
- 图片中可展示：
  - 机器人头像
  - 机器人昵称
  - CPU 名称与占用率
  - GPU 名称与占用率
  - RAM 占用与总量
  - 硬盘占用与读写速度
  - 当前活跃进程
  - 设备已运行时长
  - AstrBot 已运行时长
- 默认使用当前 QQ 机器人的头像
- 支持在 AstrBot 插件配置页面中：
  - 修改昵称
  - 上传头像图片
  - 粘贴头像 URL

## 指令说明

插件注册的是 `status` 指令，支持以下用法：

```text
\status
\status image
\status text
\status help
```

同时兼容：

```text
/status
```

说明：

- `\status`
  按插件配置中的默认模式回复
- `\status image`
  临时强制使用图片模式
- `\status text`
  临时强制使用纯文本模式
- `\status help`
  查看帮助说明

## 返回内容

### 文本模式

文本模式会按行返回当前设备状态，适合：

- 文转图服务暂时不可用时
- 希望快速查看信息时
- 在服务器资源较紧张时使用

返回内容包括：

- 主机名
- 系统信息
- Python 版本
- CPU 占用
- RAM 占用
- 磁盘占用
- 磁盘读写速度
- GPU 列表
- 设备运行时长
- AstrBot 运行时长
- Top 活跃进程

### 图片模式

图片模式会渲染一张状态面板，适合在 QQ 聊天中直接查看。布局上会包含：

- 顶部机器人头像和昵称
- 4 个核心指标卡片：CPU / GPU / RAM / Disk
- 运行环境摘要
- GPU 详情
- 活跃进程列表

如果 AstrBot 的文转图能力调用失败，插件会自动回退到 **文本模式**，不会直接报错中断。

## 配置项

AstrBot 会读取插件目录下的 `_conf_schema.json` 并在 WebUI 中生成配置页面。

当前支持的配置项如下：

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `reply_mode` | `string` | `image` | 默认回复模式，可选 `image` / `text` |
| `bot_nickname` | `string` | `astrbot` | 图片顶部显示的机器人昵称 |
| `avatar_url` | `string` | 空 | 自定义头像 URL |
| `avatar_file` | `file` | 空 | 上传头像图片，优先级高于 `avatar_url` |
| `process_count` | `int` | `6` | 图片和文本中显示的活跃进程数量 |

头像优先级如下：

1. `avatar_file`
2. `avatar_url`
3. 当前 QQ 账号头像

## 安装方法

### 方法一：在 AstrBot 面板上传 ZIP

这是最适合大多数用户的方式。

1. 打开 AstrBot WebUI
2. 进入 `插件`
3. 点击右下角 `+`
4. 选择 `文件上传`
5. 上传本仓库打包好的插件 ZIP，或上传你自己打包的插件目录
6. 等待 AstrBot 自动安装依赖
7. 打开插件配置页，设置昵称、头像、默认模式
8. 重载插件

### 方法二：手动放入本地插件目录

将仓库克隆到 AstrBot 的插件目录中：

```bash
cd AstrBot/data/plugins
git clone https://github.com/TranswarpDrive/astrbot_plugin_status_panel.git
```

然后在 AstrBot WebUI 的 `插件` 页面中重载插件即可。

## AstrBot 面板中的推荐配置流程

安装完成后，建议按这个顺序设置：

1. 打开插件配置页
2. 将 `reply_mode` 设为你喜欢的默认模式
3. 设置 `bot_nickname`
4. 如需自定义头像：
   - 直接上传图片到 `avatar_file`
   - 或填写 `avatar_url`
5. 保存配置
6. 重载插件
7. 在 QQ 私聊或白名单群发送 `\status`

## 依赖说明

本插件使用以下 Python 依赖：

- `psutil`
- `pynvml`

对应的 `requirements.txt` 已包含：

```text
psutil>=5.9.8
pynvml>=12.0.0
```

如果 AstrBot 自动安装依赖失败，可以在面板中手动安装。

## GPU 检测说明

插件优先使用 **NVML** 读取 GPU 占用信息，因此在 NVIDIA 显卡环境下通常可以得到较完整的使用率和显存信息。

如果遇到以下情况：

- 没有 NVIDIA 显卡
- `pynvml` 不可用
- 宿主机没有暴露完整 GPU 遥测

插件会自动退化为：

- 仅显示 GPU 名称
- 或不显示 GPU 使用率

这不会影响插件基本使用。

## 兼容性说明

当前插件主要面向：

- AstrBot `>=4.13,<5`
- OneBot v11 适配器
- NapCat

为什么最低版本要求是 `4.13`：

- 因为插件使用了 AstrBot 的 `file` 类型配置项
- 这样才能在面板里直接上传头像图片

## 仓库结构

```text
astrbot_plugin_status_panel/
├─ main.py
├─ metadata.yaml
├─ requirements.txt
├─ _conf_schema.json
├─ LICENSE
├─ README.md
└─ templates/
   └─ status_panel.html
```

## 开发说明

### 本地修改后如何生效

AstrBot 支持热重载插件。修改代码后：

1. 打开 AstrBot WebUI
2. 进入 `插件`
3. 找到本插件
4. 点击重载插件

### 主要文件说明

- `main.py`
  插件主逻辑，包含状态采集、命令处理、图片渲染调用
- `templates/status_panel.html`
  图片模式使用的 HTML 模板
- `_conf_schema.json`
  AstrBot 面板配置 schema
- `metadata.yaml`
  插件元信息

## 已知说明

- 如果 AstrBot 的文转图服务不可用，图片模式会回退为文本模式
- 某些系统环境下磁盘读写速度为短时间采样值，可能会有波动
- 不同平台下 GPU 数据完整度可能不同

## 适合谁用

这个插件比较适合以下场景：

- 你想在 QQ 中快速查看运行 AstrBot 的服务器状态
- 你有多个 bot，需要随时确认某台机器负载是否正常
- 你希望给群管理或自己留一个轻量级监控入口
- 你更喜欢在聊天窗口里看一张整洁的状态图，而不是登录服务器

## License

本项目使用 [MIT License](./LICENSE) 开源。
