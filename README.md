# Noctalia Device Toolkit

[English](README.en.md) · 简体中文

将 **OPPO Pods、HONOR 硬件、HONOR 充电档位** 三个本地 Noctalia 工具整理在同一个 GitHub 仓库中。它们可以独立启用；HONOR 相关功能只适用于具备对应接口的机器。本项目是社区/本地工具合集，不是 OPPO、HONOR 或 Noctalia 的官方发行版。

## 三个工具

| 工具 | 插件 ID / 源码 | 入口与作用 | 硬件适用范围 |
| --- | --- | --- | --- |
| OPPO Pods | `osp54/oppo-pods` · [源码和说明](plugins/oppo-pods/README.md) | 状态栏耳机小组件；电量、降噪、EQ、设备设置和佩戴播放联动 | 扩展功能历史验证于 OPPO Enco Free4 标准版，产品 ID `068C10`、固件 138；其他型号按协议能力提供部分功能 |
| HONOR 硬件 | `dc/honor-fan` · [源码和说明](plugins/honor-fan/README.md) | Control Center 首页「HONOR 硬件」；双风扇转速、温度、三档键盘背光 | HONOR MagicBook Pro 14，DMI 厂商 `HONOR`、型号 `FMB-P` |
| HONOR 充电档位 | `dc/honor-battery-profile` · [源码和说明](plugins/honor-battery-profile/README.md) | Control Center 首页「充电 40/70」等；可选状态栏组件；切换充电阈值 | HONOR FMB-P，且内核已提供 `huawei-wmi` 充电阈值及 `BAT0` 接口 |

「HONOR 硬件」只声明首页快捷方式，没有独立顶栏小组件。充电工具同时声明首页快捷方式和可选顶栏组件。充电档位是电池阈值，不是 CPU 性能档位或充电瓦数设置。

## 系统与兼容性

本次整理的本地环境：**CachyOS（Arch 系）、Linux 7.2.9-1-cachyos、Noctalia 5.2.1、HONOR FMB-P / M1030**。这些信息是读取本机系统及已安装文件得到的，不包含序列号。

- 需要 Linux、Wayland 和 Noctalia 的 **Luau/TOML 插件系统**。本机 Noctalia 版本为 5.2.1；OPPO 插件声明 API 24，两个 HONOR 插件声明 API 22。合集应使用支持 API 24 且兼容 API 22 的版本。
- 不是 GNOME 扩展、KDE 小部件、Waybar 模块，也不是旧式 QML Noctalia 插件；Windows/macOS 不适用。
- 其他 Linux 发行版理论上可移植，但本包没有宣称在 Ubuntu、Debian、Fedora 或其他 HONOR 型号上完成验证。
- Python 控制器只使用标准库；合集检查脚本需要 Python **3.11+**（使用 `tomllib`）。OPPO 需要 BlueZ/`bluetoothctl`；佩戴播放联动额外需要 `busctl`、`pactl` 和支持 MPRIS 的播放器。
- HONOR 驱动需要匹配当前内核的开发头文件、DKMS、编译工具链；充电后端需要 Bash、systemd、sudo、util-linux 的 `flock`。

## 仓库结构

```text
plugins/
  oppo-pods/                 # 完整耳机插件、图标、翻译和离线回归测试
  honor-fan/                 # 硬件服务、首页快捷方式和面板
  honor-battery-profile/     # 充电服务、快捷方式、可选状态栏组件和面板
backends/
  honor-hardware/            # 两个可选 DKMS 驱动的 C 源码
  honor-battery/             # 系统脚本、开机服务、唤醒钩子、默认配置、权限模板
scripts/                    # 安装、离线检查和公开内容扫描
examples/                   # 无个人信息的 UI 配置片段
docs/                       # 中英文上传、隐私与验证说明
LICENSES/                   # MIT 与 GPL-2.0-only 原文
```

## 安装插件

先安装并启动兼容的 Noctalia，在仓库根目录以桌面普通用户执行：

```bash
bash scripts/install-plugins.sh --dry-run
bash scripts/install-plugins.sh
```

脚本复制到 `$XDG_DATA_HOME/noctalia-device-toolkit/plugins`（默认在 `~/.local/share`），注册名为 `device-toolkit` 的 path source，并启用三个插件。它不重写完整桌面配置；如果目标目录已存在则停止。IPC 必须在正在运行的 Noctalia 所属用户会话中可用。复制成功而注册失败时，脚本会给出后续注册命令。

然后在 Noctalia 设置中：

1. 状态栏 → 小组件：加入 **OPPO Pods**。
2. Control Center / 控制中心 → 首页快捷方式：加入 **HONOR 硬件** 和 **HONOR Battery Profiles / 充电档位**。
3. 如需顶栏显示阈值，再加入充电插件的 `battery-profile` 小组件。

插件 ID 刻意保持原值。若已有社区 OPPO 插件或旧 HONOR path source，在插件来源设置中确认采用本仓库来源，停用/移除同 ID 的旧本地来源；不要只根据同名条目判断实际代码。原社区来源可保留用于回退。

只安装一个工具时，可直接将整个 `plugins` 目录作为 path source，然后只启用需要的 ID：

```bash
noctalia msg plugins source add device-toolkit path "$(pwd)/plugins"
noctalia msg plugins enable osp54/oppo-pods
```

使用此方式时不要移动仓库目录；也不要重复运行安装脚本注册同名来源。

## HONOR 配套后端

**本机已有这些后端，不需要为了本次整理重新安装。** 新机器应先核对 DMI 与 sysfs 接口，具体方法见各插件 README。所有系统安装脚本支持 `--dry-run`，会拒绝覆盖已有文件。

```bash
# 仅当 FMB-P 缺少对应硬件驱动时使用；安装后重启生效。
bash scripts/install-hardware-drivers.sh --dry-run
sudo bash scripts/install-hardware-drivers.sh

# 先预览。将 YOUR_DESKTOP_USER 替换为实际桌面用户名。
bash scripts/install-battery-backend.sh --desktop-user YOUR_DESKTOP_USER --dry-run
sudo bash scripts/install-battery-backend.sh --desktop-user YOUR_DESKTOP_USER
```

充电安装脚本启用下一次开机服务，不立即改变当前阈值。可选桌面授权通过 `honor-charge` 组仅放行三个确切的阈值命令；添加组成员后重新登录。省略 `--desktop-user` 时不安装免密权限，需手动使用 `sudo honor-battery-profile set ...`，面板按钮无法免密写入。

本仓库不包含 BIOS/ACPI 转储、预编译 DSDT 或通用固件修补器。若固件或内核不暴露充电接口，应先完成该机器自身的适配；安装面板不能补出缺失的接口。不要从其他电脑复制 ACPI 表来解决兼容性问题。

## 检查与发布

```bash
bash scripts/check.sh
```

检查包括公开内容扫描、Python/TOML/JSON 与 Shell 语法、OPPO 离线回归测试；安装了 Noctalia 时还运行三个插件的 lint。扫描器不显示可疑密钥值，只报告文件、行号和类型。

本次整理结果与限制见 [中文验证说明](docs/VERIFICATION.md) / [English verification](docs/VERIFICATION.en.md)。上传步骤见 [中文 GitHub 指南](docs/GITHUB_UPLOAD.md) / [English guide](docs/GITHUB_UPLOAD.en.md)。此文件夹可作为一个仓库的根目录，不含原电脑的 Git 历史或远程认证配置。

## 隐私与维护

OPPO 上传版本移除了原代码中的远程耳机图片下载鉴权与签名密钥，保留本地图标及可选本地图片缓存。耳机控制不依赖这个下载服务。测试地址均为虚构样例；没有打包用户设置、蓝牙配对密钥、播放记录、OEM 产品密钥或硬件序列号。

运行时仍会在本机生成含设备地址/状态的缓存；这些数据不属于源码。详见 [隐私说明](docs/PRIVACY.md)。`.gitignore` 无法保护已经提交过的敏感文件；新提交前应重新扫描并查看实际暂存内容。

更新时先禁用相应插件，备份本地安装目录，再复制新源码并重新启用。个人配置和备份应保留在仓库之外。卸载插件只需禁用 ID、移除 `device-toolkit` 来源并在设置中移除对应入口；系统后端的卸载步骤见各工具 README。

## 许可证与来源

插件及仓库整理脚本/文档为 MIT；`backends/honor-hardware/` 中两个内核模块按其原始声明为 **GPL-2.0-only**。保留 OPPO 作者 `osp54`、原插件命名空间和驱动作者声明。`dc` 是原 HONOR 插件公开 ID 的命名空间，不是安装时需要填写的用户名。请查看 [LICENSE](LICENSE) 和 [第三方来源说明](THIRD_PARTY.md)。
