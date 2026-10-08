# 许可证、来源与修改归属

[English](THIRD_PARTY.en.md)

| 组件 | 原始来源/声明 | 许可处理 |
| --- | --- | --- |
| OPPO Pods | 本地启用的 `osp54/oppo-pods` 1.1.2；原版权 `Copyright (c) 2026 osp54` | 完整保留 `plugins/oppo-pods/LICENSE`、作者和 ID；MIT |
| HONOR UI | 本地启用的 `dc/honor-fan` 1.1.4 与 `dc/honor-battery-profile` 1.0.0；manifest 声明 MIT | 保留原 namespace/author，补齐独立 MIT 文本 |
| HONOR 充电后端 | 本机本地脚本及 service/config/resume hook | 按本地工具归属提供 MIT；不复制个人授权文件 |
| HONOR hwmon / kbdlight | 本机已安装源码版本 1.0 / 1.1；`SPDX-License-Identifier: GPL-2.0`，`MODULE_AUTHOR("MagicBook Linux project")` | 原文件头与作者不变；分发为 GPL-2.0-only，全文在 `LICENSES/GPL-2.0-only.txt` |
| 打包安装脚本、检查器、文档 | 本次整理新增 | MIT，与内核模块的 GPL 范围分开说明 |

原插件内图标/示意素材随原 MIT 插件一起保留；品牌名称用于说明兼容目标，不表示商标授权或官方认证。本合集没有把厂商下载资源的缓存打包进来。

已有源码/说明中的参考链接如下；本次整理没有联网抓取或验证这些站点的新内容：

- [Noctalia 社区 OPPO 插件](https://noctalia.dev/plugins/community/oppo-pods)
- [OPPO Android 参考项目](https://github.com/1812z/OppoPods)
- [OPPO 协议参考项目](https://github.com/Zhaoyi-ya/OppoPodsManager)
- [HONOR MagicBook Linux 项目](https://github.com/drphilth/honor-magicbook-pro-14-ubuntu)

本次修改：移除 OPPO 远程图片签名密钥与下载路径、匿名化测试地址、排除未声明旧 widget/预览图/缓存，新增 README、安装/检查工具与无个人信息的权限模板；充电 helper 增加 FMB-P 写入检查、精确参数个数、非交互 sudo，并将锁放在 root 所有的状态目录内。已运行环境中的文件保持原状，修改仅发生在上传副本。
