# HONOR 硬件

[English](README.en.md) · [返回合集](../../README.md)

Control Center 首页的 **HONOR 硬件** 快捷项。插件 ID `dc/honor-fan`，版本 `1.1.4`，API `22`。名称中的 `fan` 是历史 ID；当前工具包含温度与键盘背光，不提供手动风扇控制。

## 功能与入口

- 左键打开面板：两路风扇 RPM、CPU 封装和核心最高温度，以及存在的 NVMe、Wi-Fi、ACPI 温度。
- 键盘背光：关闭、低亮、高亮三个按钮，通过 Noctalia 原生 `keyboard-backlight-set` 控制；显示当前档位，并约每两秒同步。
- 右键快捷项打开 Control Center 的显示 / Monitor 分类，用于系统屏幕亮度调节。
- 本插件不声明顶栏 widget；旧的未声明 `widget.luau` 未进入此上传包。

风扇策略仍由固件管理。面板只读传感器；可选键盘灯驱动会写入该机型专用 EC 寄存器，不能移植为所有 HONOR 机型通用驱动。

## 支持范围

目标是 **HONOR MagicBook Pro 14（DMI `HONOR` / `FMB-P`）**；本地型号版本 `M1030`。本次整理环境为 CachyOS、内核 7.2.9-1-cachyos、Noctalia 5.2.1。

| 接口 / 依赖 | 用途 |
| --- | --- |
| `/sys/class/hwmon/*/name` = `honor_fmbp`，`fan1_input`/`fan2_input` | 两路风扇转速，通常由本仓库的 `honor-fmbp-hwmon` 驱动提供 |
| `coretemp` | Intel CPU 温度；不能假设 AMD 或其他探头命名适用 |
| `nvme`、`iwlwifi*`、`acpitz*` | 可选温度来源，缺少对应探头就没有该项 |
| `/sys/class/leds/huawei::kbd_backlight/`，`max_brightness=2` | 三档背光接口 |
| Noctalia API 22 兼容性与背光 IPC | 面板、状态同步和原生背光控制 |
| `lm_sensors` | 插件声明的依赖及手工诊断；服务本身通过 Shell 读取 sysfs |

兼容 Linux Wayland + Noctalia 原生 Luau 插件系统；没有在其他发行版或型号上验证。sysfs 节点应可读；背光权限由 Noctalia 原生机制/系统策略决定，面板本身不会直接请求 sudo。

## 安装

先按[合集说明](../../README.md#安装插件)安装插件，在 Control Center 首页快捷方式中加入 **HONOR 硬件**。

确认机器和已存在接口：

```bash
cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
sensors honor_fmbp-isa-0000 coretemp-isa-0000
cat /sys/class/leds/huawei::kbd_backlight/max_brightness
```

本机已有驱动时直接复用。新 FMB-P 缺少驱动时，仓库附带两个源码：

- `backends/honor-hardware/honor-fmbp-hwmon-1.0`：只读 EC 风扇转速，经 DMI 限制注册 `honor_fmbp`。
- `backends/honor-hardware/honor-fmbp-kbdlight-1.1`：三档 LED 驱动；加载时设置低亮档。默认 reactive 模式，面板仅修改亮度，不切换 steady/reactive。

从仓库根目录：

```bash
bash scripts/install-hardware-drivers.sh --dry-run
sudo bash scripts/install-hardware-drivers.sh
```

先安装 DKMS、make 和**匹配当前内核**的头文件/工具链；Clang 内核还需要对应 LLVM 工具。脚本构建两个模块、配置下一次开机加载，不即时加载。若源目录、开机配置或同名键盘 LED 已存在，它会停止，避免重复提供接口。仅缺少其中一个模块时，应分别手动管理 DKMS，而不是运行全套安装脚本。

启用 Secure Boot 的机器需要自己的模块签名与信任配置；本仓库不分发签名私钥。原驱动保留 DMI 检测，安装器也检查 `HONOR` / `FMB-P`；不要删除这些条件来强行装到其他型号。

## 排错与检查

```bash
noctalia plugins lint plugins/honor-fan
noctalia msg panel-toggle dc/honor-fan:panel
dkms status
```

面板无数据：检查 `honor_fmbp`、`coretemp` 等 hwmon 节点及驱动；风扇停转时 `0 RPM` 正常，但没有数据时也应检查接口，不能单凭零值判断硬件已识别。背光按钮不可用：检查准确的 LED 名称和 `max_brightness=2`。背光切换失败：检查 Noctalia 原生命令及系统权限；不要修改 sysfs 为所有用户可写来绕过权限。

插件服务与面板分别读取传感器和背光状态；一次打包的 lint/构建不等于在其他电脑验证硬件行为。详见[验证说明](../../docs/VERIFICATION.md)。

## 卸载

```bash
noctalia msg plugins disable dc/honor-fan
```

在设置中移除首页快捷项即可停用 UI。若这两个驱动**由本仓库新安装**且其他功能不依赖它们，可再删除本合集创建的 `/etc/modules-load.d/honor-device-toolkit.conf`，并卸载：

```bash
sudo dkms remove honor-fmbp-hwmon/1.0 --all
sudo dkms remove honor-fmbp-kbdlight/1.1 --all
```

重启后模块不再加载；确认卸载成功后可删除这两个对应的 `/usr/src` 源目录。不要删除其他安装器的模块加载配置或已有驱动。

## 许可

Noctalia 插件为 MIT；两个内核驱动保留原始 GPL-2.0-only 头与 `MagicBook Linux project` 作者声明。见[来源说明](../../THIRD_PARTY.md)。
