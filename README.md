# 场边笔记

把知识带进训练，把经历写成笔记。

网站：<https://qinjishen.github.io/fieldnotes/>

首页以“积累 → 应用 → 进展”三组笔记展示长期成长。短标题常显，支持悬停关联、节点拖动与独立文章阅读；手机采用纵向排列。保留网球与健身主题、训练计划、全文搜索、阅读路线和 Markdown 下载。

## 更新网站

推送到 `main` 后，GitHub Actions 自动检查、生成并发布网页。网站文章与生成程序保存在本仓库，生成后的 `dist/` 由部署流程上传。

日常写作仍在原有“网球-网站/发布文档”文件夹完成；本仓库保存已发布内容快照。请不要在这里创建空的 `发布文档` 文件夹，它会切换为本地输入模式，替代导入快照。

- `content/cards/`：原有卡片的已发布 Markdown 快照；日常在 Obsidian 的“发布文档”笔记库编辑。
- `content/published.json`：全部已发布文章快照（含原有卡片和实际引用的附件信息）。
- `content/discovery.json`：个人介绍、问题入口与主题。
- `static/`：网页样式和交互。
- `.github/workflows/pages.yml`：自动发布配置。

## Obsidian 写作

现有十一篇文章已集中到“发布文档”笔记库。打开其中的 `_开始写作.md`；使用实时预览编辑，按 Cmd+P 插入四种写作模板。保留每天北京时间上午 9 点的自动同步。

详见 [Obsidian 写作与发布](docs/Obsidian写作与发布.md)。

## 提示词与笔记模板

- [网站设计约定](docs/网站设计约定.md)：配色、布局、交互、内容边界和检查要求。
- [可复用修改提示词](docs/修改网站提示词.md)：修改页面、扩展内容、整理真实记录与排查异常。
- [模板使用说明](templates/使用说明.md)：首页分类、短标题、真实日期与引用的填写方法。
- [知识卡片](templates/知识卡片模板.md)、[训练日志](templates/训练日志模板.md)、[比赛复盘](templates/比赛复盘模板.md)、[阶段进展](templates/阶段进展模板.md)。

以后修改网站时，可以直接让执行者先读取设计约定，再引用对应提示词。模板默认是草稿，填完真实内容后再发布。

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
