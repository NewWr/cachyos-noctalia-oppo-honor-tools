# OPPO Pods

[English](README.en.md) · [返回合集](../../README.md)

Noctalia 状态栏中的耳机连接状态与控制插件。插件 ID `osp54/oppo-pods`，原版本 `1.1.2`，API `24`。它控制已经配对并连接的设备；首次配对、操作系统音频路由仍由 BlueZ/桌面音频系统负责。

## 功能

- 显示左右耳和充电盒电量，以及设备报告的充电/佩戴状态；支持低电量提醒。
- 左键打开控制面板，右键循环切换可用的降噪、通透等模式。
- Free4 扩展：关闭、通透、自适应、智能/轻度/中度/深度降噪；双设备连接、游戏低延迟、空间音效、佩戴检测、个性化听感开关。
- 读取出厂及耳机已有 EQ，创建/修改/删除六频段自定义 EQ。保存会写入耳机；删除当前 EQ 前先切换其他预设。
- 显示型号、固件、当前编码和耳机保存的设备列表；「已保存」不等于当前连接。
- 摘下耳机时暂停实际通过这副耳机播放的 MPRIS 播放器；稳定重新佩戴时，仅恢复由本插件成功暂停且状态未被用户改变的播放。

关闭盒盖后盒电量可能未知；摘下两只耳机时，固件可能拒绝切换降噪。个性化听感使用耳机已有数据，不执行新的听力测试。编码信息只读，不负责开启 LDAC/LHDC 等编码。

「查找耳机」提示音仍是实验功能。控制器要求两只耳机均摘下，收到命令接受后设置 10 秒停止期限；重新佩戴也会发送停止。历史说明没有确认实际鸣响，不能把协议接受视为声音已经验证。

尚未实现：手势/通话按键配置、完整佩戴适配测试、提示音音量、主动连接设备切换、AI 翻译、手机相机控制和固件升级。

## 适用设备与系统

| 项目 | 范围 |
| --- | --- |
| 系统 | Linux + Wayland + Noctalia Luau 插件 API 24；本地整理环境 CachyOS / Noctalia 5.2.1 |
| 完整扩展的历史验证设备 | OPPO Enco Free4 标准版，产品 ID `068C10`，固件 138 |
| 其他型号 | 代码包含部分 OPPO Enco、OnePlus Buds、realme Buds 名称映射；映射不是兼容性认证，扩展操作由已知型号和实际能力字段共同限制 |
| Free4 Dynaudio | `06C010` 与标准版不同，不承诺享有标准版全部扩展 |
| 基础依赖 | Python 3、BlueZ、`bluetoothctl`、Linux RFCOMM 支持；推荐 Python 3.11+ 便于运行本仓库检查 |
| 播放联动 | `busctl`、`pactl`、用户 D-Bus、PipeWire-Pulse 或 PulseAudio、支持 MPRIS 的播放器 |

不需要管理员权限或 API key。Linux 发行版之间的差异主要来自蓝牙、音频和 Noctalia 的配置。本次没有对其他机器重新实测。

## 安装和使用

按[合集安装说明](../../README.md#安装插件)注册来源并启用插件。先在系统蓝牙管理器中配对、连接耳机，再在 Noctalia 设置 → 状态栏 → 小组件中加入 **OPPO Pods**。默认断开时隐藏组件；排错时可以关闭这个选项。

| 设置 | 默认 | 含义 |
| --- | --- | --- |
| `device_mac` | 空 | 自动识别已连接设备；多设备时可在本机插件设置中填写目标地址，勿提交到 Git |
| `pause_on_remove` | `true` | 摘下暂停及重新佩戴恢复，沿用原配置键名 |
| `low_battery_notifications` | `true` | 左右耳达到 20%/10% 时提醒；充电或恢复至 25% 以上后重置 |
| 小组件 `hide_when_disconnected` | `true` | 断开时隐藏 |

佩戴联动通过音频流客户端 PID 匹配播放器，减少对扬声器或其他耳机播放的干扰。抖动会去抖；未知、过期或断连状态不会触发新的暂停。手动播放/暂停/切歌/跳转、输出路由或进程变化会取消自动恢复。暂停记录仅存在于当前监测进程，重启插件不会自行播放。缺少事件监测时可保留摘下暂停，但恢复需手动操作。

## 本地工作原理与隐私

`service.luau` 启动 `scripts/oppo_ctl.py` 常驻监测器；控制器保持一条 RFCOMM 连接，通过私有 Unix socket 接收本地控制命令。它订阅通知，并以轮询补偿；写入需要接受响应和读取状态确认。

运行文件位于 `$XDG_RUNTIME_DIR`（原代码在变量未设置时回退 `/tmp`）：`oppo_pods_state.json`、`oppo_pods_channel.txt`、控制锁和 socket。这些文件可能包含蓝牙地址、设备列表及状态。使用正常设置了 `XDG_RUNTIME_DIR` 的桌面会话，不要将运行文件放进仓库。

上传版本完全移除了远程图片下载签名凭据和联网下载路径。本地图标继续使用；可手工放置本地 PNG 到 `$XDG_CACHE_HOME/noctalia/oppo-pods/<PRODUCT_ID>.png`（默认 `~/.cache`），但个人缓存不应提交。没有缓存时 UI 使用内置回退图示；内置 Enco Air4 Pro 示意图不代表自动准确匹配每个型号。

## 排错与验证

```bash
bluetoothctl devices Connected
noctalia plugins lint plugins/oppo-pods
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/oppo-pods/tests -v
noctalia msg panel-toggle osp54/oppo-pods:panel
```

以上命令从仓库根目录运行。若检测不到设备，确认系统已连接耳机及设备暴露 OPPO 控制服务；检查是否加载了旧来源、是否有另一控制程序占用 RFCOMM。仅连接音频不一定保证控制服务可用。播放联动失败时，确认播放器有 MPRIS 接口，且 `busctl`/`pactl` 能在同一用户会话工作。

仓库中离线测试使用模拟 socket/播放器和匿名化协议样本，不接触真实耳机。历史功能验证和此次打包验证分开记录于[验证报告](../../docs/VERIFICATION.md)。

## 卸载和许可

```bash
noctalia msg plugins disable osp54/oppo-pods
```

在设置中移除 OPPO 状态栏组件。如果仍使用合集其他插件，保留 `device-toolkit` 来源。完全停用本插件后可自行清理本机 OPPO 缓存；不要删除 BlueZ 配对数据来卸载面板。

MIT，保留 `osp54` 的原始版权与归属。参见 [LICENSE](LICENSE) 和合集[来源说明](../../THIRD_PARTY.md)。
