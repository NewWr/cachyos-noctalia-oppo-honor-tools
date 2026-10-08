# API key 与个人信息审核

[English](SECRET_AUDIT.en.md) · [项目首页](../README.md)

审核日期：2026-10-08。项目：[NewWr/cachyos-noctalia-oppo-honor-tools](https://github.com/NewWr/cachyos-noctalia-oppo-honor-tools)。

审核基线：`main` 提交 `533e4dc`。审核了该版本的 83 个文件、全部两次可访问公开提交（`f7297e9`、`533e4dc`）及其中 81 个不同文件对象，同时检查提交作者/提交者邮箱。获取远端分支和标签后，只发现 `main`，没有其他可访问分支或标签。

**结果：未发现 API key、访问 Token、私钥或个人联系信息泄露。** 没有发现真实蓝牙地址、个人绝对路径、用户配置、设备序列号或 OEM 产品密钥。两次公开提交的作者/提交者均使用 GitHub noreply 邮箱。

检查覆盖私钥标记、GitHub/OpenAI/Anthropic/Slack/云服务凭据、Google API key、GitLab Token、JWT/Bearer 形状、源码及 JSON/YAML 中的凭据赋值、带认证信息的 HTTP URL、邮箱、MAC、固件/运行文件和图片元数据。源码中的凭据相关逻辑也进行了人工复核；报告不会打印可疑凭据值。

上传之前，OPPO 图片下载代码的硬编码签名密钥已从上传副本移除；这段代码未进入上述任何公开提交。测试 MAC 是虚构样例。`osp54`、`dc`、`MagicBook Linux project` 等保留项是原代码的公开归属；产品 ID、协议 UUID、通用系统路径属于功能信息，不是认证密钥。

本次修改另外加强了 `scripts/check-public-content.py` 的凭据模式，并复查新增文档。检测是静态与启发式审核，不等于保证识别所有编码或变形秘密，也不涵盖不可访问的已删除引用及 GitHub 服务端环境变量。它不读取用户本机的私钥或 API 凭据。

以后提交前运行：

```bash
python3 scripts/check-public-content.py
git diff --cached
```

如果以后确认任何凭据已公开，应先撤销/轮换凭据，再处理文件与历史；仅删除最新版本中的值不足以消除旧提交中的泄露。
