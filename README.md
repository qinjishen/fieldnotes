# 场边笔记

一个观点，一篇文章。在联系中理解，在训练中检验。

网站：<https://qinjishen.github.io/fieldnotes/>

包含个人首页、网球与健身主题、文章关系图、训练计划、全文搜索、阅读路线，以及可以独立阅读和下载的 Markdown 文章。

## 更新网站

推送到 `main` 后，GitHub Actions 自动检查、生成并发布网页。网站文章与生成程序保存在本仓库，生成后的 `dist/` 由部署流程上传。

日常写作仍在原有“网球-网站/发布文档”文件夹完成；本仓库保存已发布内容快照。请不要在这里创建空的 `发布文档` 文件夹，它会切换为本地输入模式，替代导入快照。

- `content/cards/`：原有原子文章。
- `content/published.json`：已发布的导入文章快照。
- `content/discovery.json`：个人介绍、问题入口与主题。
- `static/`：网页样式和交互。
- `.github/workflows/pages.yml`：自动发布配置。

## 本地运行

需要 Python 3.11 或更新版本。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/sync.py prepare
.venv/bin/python -m http.server 8000 --directory dist
```

打开 http://localhost:8000 。所有站内地址采用相对路径，适用于 GitHub Pages 的项目网址。

仓库只包含网站源码、公开文章及其所需附件。原始资料、草稿、本机状态和账号信息不在此仓库中。
