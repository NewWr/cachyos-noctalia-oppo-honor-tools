# 上传到同一个 GitHub 仓库

[English](GITHUB_UPLOAD.en.md) · [返回 README](../README.md)

目标仓库：[NewWr/Cachyos--magicbook--](https://github.com/NewWr/Cachyos--magicbook--)。本文件夹本身就是仓库根目录，三个插件都在 `plugins/` 下；不要把整个电脑的 Noctalia 配置目录一起上传。

## 方式一：Git 命令行

1. 在 GitHub 创建空仓库。需要公开分享时选择 Public；如果想先审核，选择 Private。暂时不要由 GitHub 自动生成 README、许可证或 `.gitignore`，本文件夹已经包含它们。
2. 在本地进入本文件夹。运行检查后初始化新的 Git 历史：

```bash
bash scripts/check.sh
git init -b main
# 使用你希望公开显示的身份；邮箱可选 GitHub 提供的 noreply 邮箱。
git config --local user.name "YOUR_PUBLIC_NAME"
git config --local user.email "YOUR_GITHUB_NOREPLY_EMAIL"
git add .
git status --short
git diff --cached --stat
git diff --cached
```

3. 阅读暂存差异，确认只有此包中的源码、文档和许可证；再提交并上传。替换 `YOUR_ACCOUNT`，不要把 token 放进 URL：

```bash
git commit -m "Add OPPO Pods and HONOR Noctalia tools"
git remote add origin https://github.com/NewWr/Cachyos--magicbook--.git
git push -u origin main
```

认证通过 Git 凭据管理器或已有的 GitHub CLI/SSH 配置完成；无需在仓库中创建 key 文件。提交作者姓名/邮箱会成为公开 Git 历史，请先使用自己希望公开的身份。首次发布应使用本包的新历史，不导入原工作目录的历史、日志或 `.git/config`。

## 方式二：GitHub 网页上传

在空仓库的 Upload files 页面，将**此文件夹内部的内容**上传到仓库根目录。需要保留三个 `plugins/` 子目录、`backends/`、`scripts/`、`docs/`、许可证和隐藏的 `.gitignore` / `.gitattributes`。压缩包只适合解压获取文件或作为 Release 附件；只上传一个 ZIP 不会呈现可浏览的源码仓库。

浏览器/文件选择器若遗漏隐藏文件，手动创建对应文件。网页上传前同样先运行扫描；网页不会因为本地 `.gitignore` 自动替你过滤被拖入的个人文件。

## 仓库首页与可选发布

- `README.md` 为中文首页，`README.en.md` 为英文；三个插件也各有中英文 README。
- 合集为混合许可：UI/脚本 MIT，两个内核驱动 GPL-2.0-only。不要让 GitHub 生成一个替代全部原许可证的文件。
- 可选仓库描述：`OPPO Pods and HONOR FMB-P hardware / battery tools for Noctalia`。
- 可选 topics：`noctalia`、`linux`、`honor`、`oppo`、`bluetooth`、`battery`。
- 首次上传后检查文件树和文档链接；可将同一干净 ZIP 作为 Release 附件。

## 后续修改

每次提交前重新运行 `bash scripts/check.sh` 并检查暂存差异。`.gitignore` 不能排除已被跟踪的文件；如果误提交凭据，应撤销/轮换凭据并清理历史，仅删除当前文件不足以消除旧提交中的内容。

本仓库使用上述地址。后续更新应在现有克隆中提交并推送，不要重复初始化或添加同名 remote。
