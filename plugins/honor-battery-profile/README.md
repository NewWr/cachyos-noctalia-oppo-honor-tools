# HONOR 充电档位

[English](README.en.md) · [返回合集](../../README.md)

Noctalia Control Center 首页的充电快捷项，显示「充电 40/70」等当前阈值。插件 ID `dc/honor-battery-profile`，版本 `1.0.0`，API `22`。也可选配状态栏 `battery-profile` 小组件。

## 功能与三种档位

打开面板可查看电量、充电状态和当前阈值，并选择固件的三个预设：

| 档位 | 开始阈值 | 停止阈值 | 常见使用场景 |
| --- | --- | --- | --- |
| 家用 `home` | 40% | 70% | 长期插电，保留较低电池电量 |
| 办公 `office` | 70% | 90% | 兼顾插电和短时离电 |
| 差旅 `travel` | 95% | 100% | 需要接近满电续航 |

这些是电池充电阈值，不是 40W/70W 等功率，不是 CPU 性能模式。降低停止阈值不会主动把已经较高的电量放至该值；适配器仍可给电脑供电。实际启停由固件处理，仪表读数可能有取整或延迟。

后端会写入配套 `huawei-wmi` 接口，再读取确认。手动选择可保存，睡眠唤醒后恢复保存的档位；**每次重启按默认配置回到 `home`（40/70）**。开机服务调用 `boot`，唤醒钩子调用 `apply`，两者行为不同。

## 适用范围与依赖

本包只允许在 **HONOR FMB-P（MagicBook Pro 14）** 写入，本地型号版本为 `M1030`。整理环境：CachyOS / Linux 7.2.9-1-cachyos / Noctalia 5.2.1。其他型号、发行版、BIOS 版本没有在此次验证中确认。

必须已经具备：

- Noctalia Luau 插件系统，兼容 API 22。
- Linux `huawei_wmi` 驱动及可写的 `/sys/devices/platform/huawei-wmi/charge_control_thresholds`。
- `/sys/class/power_supply/BAT0/charge_control_start_threshold` 与 `charge_control_end_threshold`，供 UI 读取。
- `/usr/local/bin/honor-battery-profile` 系统后端；Bash、sudo、systemd、`flock`。
- 桌面按钮使用可选的精确 sudoers 授权；没有该授权时使用终端显式 `sudo`。

插件 manifest 的 `dependencies=[]` 不代表它可以独立控制硬件；系统后端和 sysfs 是运行前提。接口缺失可能涉及固件、内核或本机 ACPI 适配，本包不包含机器专属 ACPI 表或自动修补程序。

## 安装与权限

先检查 DMI 和接口（只读）：

```bash
cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
cat /sys/devices/platform/huawei-wmi/charge_control_thresholds
cat /sys/class/power_supply/BAT0/charge_control_start_threshold
cat /sys/class/power_supply/BAT0/charge_control_end_threshold
```

本机已经装有后端时不要再次运行安装器。新 FMB-P 在接口正常时，从仓库根目录执行；将占位符替换为桌面账户：

```bash
bash scripts/install-battery-backend.sh --desktop-user YOUR_DESKTOP_USER --dry-run
sudo bash scripts/install-battery-backend.sh --desktop-user YOUR_DESKTOP_USER
```

安装内容：系统命令及菜单、默认配置 `/etc/default/honor-battery-profile`、开机 service、唤醒钩子；可选权限模板。目标已存在时脚本停止，不覆盖既有配置。安装只启用开机服务，当前档位不立即改变。

权限模板面向 `honor-charge` 组，只放行以下三个 root 命令，**没有参数通配符、全局免密 sudo 或本地写死用户名**：

```text
/usr/local/bin/honor-battery-profile set 40/70
/usr/local/bin/honor-battery-profile set 70/90
/usr/local/bin/honor-battery-profile set 95/100
```

添加组成员后重新登录。系统脚本和配置必须归 root 所有并禁止普通用户写入。后端普通用户调用使用 `sudo -n`，避免面板等待终端密码。省略 `--desktop-user` 可以只安装系统后端；此时按钮没有免密权限，手动终端控制需显式 sudo。

随后按[合集说明](../../README.md#安装插件)安装 UI，并在 Control Center 首页加入充电快捷项。

## 命令行、配置与状态文件

```bash
honor-battery-profile status
honor-battery-profile list
sudo honor-battery-profile set home
sudo honor-battery-profile set 70/90
sudo honor-battery-profile set 95/100
sudo honor-battery-profile default
```

`default` 使用 `DEFAULT_PROFILE`，出厂整理配置为 `home`。管理员可编辑 `/etc/default/honor-battery-profile` 改默认档位；`PERSIST_SELECTION=no` 关闭手动选择的保存与读取，开机仍应用默认档位。

状态保存在 `/var/lib/honor-battery-profile/profile`，锁位于 `/var/lib/honor-battery-profile/.lock`。这些是运行数据，不能提交。配置由 Bash source 读取，只应由管理员修改。

## 排错与检查

```bash
noctalia plugins lint plugins/honor-battery-profile
systemctl status honor-battery-profile.service
honor-battery-profile status
noctalia msg panel-toggle dc/honor-battery-profile:panel
```

UI 提示无接口：检查 `BAT0` 节点与 `huawei_wmi`；UI 按钮失败：检查后端安装、用户是否重新登录获得组成员资格，以及 root 文件权限；重启后回到 40/70：这是默认开机策略；唤醒后恢复失败：检查 system-sleep 钩子和 systemd 日志。

手动阈值修改会影响真实电池状态。本次打包仅运行只读命令和静态检查，没有切换本机档位，未对新安装过程执行 root 写入。见[验证说明](../../docs/VERIFICATION.md)。

## 卸载

先禁用 UI 并在设置中移除快捷项/小组件：

```bash
noctalia msg plugins disable dc/honor-battery-profile
```

若后端**由本合集新安装**，可停用开机服务，然后删除对应的五个文件及可选权限规则：

```bash
sudo systemctl disable --now honor-battery-profile.service
sudo rm /etc/systemd/system/honor-battery-profile.service
sudo rm /usr/lib/systemd/system-sleep/honor-battery-profile
sudo rm /usr/local/bin/honor-battery-profile /usr/local/bin/honor-battery-profile-menu
sudo rm /etc/default/honor-battery-profile
# 仅当安装过该可选规则时：
sudo rm /etc/sudoers.d/honor-battery-profile
sudo systemctl daemon-reload
```

如不再需要桌面授权，可使用 `sudo gpasswd -d YOUR_DESKTOP_USER honor-charge` 移除成员。运行状态目录可另行清理；卸载不会自动恢复电池阈值。需要恢复某档位时应在删除后端前显式选择。不要删除由其他项目/管理员维护的同名后端。

## 许可与归属

插件及本地充电脚本为 MIT，原命名空间 `dc` 保留。使用「固件预设」描述功能，不表示 HONOR 官方提供或认证了本插件。
