#!/usr/bin/env python3
"""Hand published notes to the existing local Obsidian vault without duplicating IDs."""
from pathlib import Path
from datetime import datetime
import json, os, re, shutil, sys, tempfile
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from publishing import Library, INPUT, parse, visible_files

def setup(root=ROOT):
    root=Path(root);vault=root/INPUT
    if not vault.is_dir():raise ValueError('请在含有现有“发布文档”笔记库的维护副本中运行；不要在 GitHub 快照副本中运行。')
    with tempfile.TemporaryDirectory() as out:
        lib=Library(root,Path(out))
    backup=root/'.publish-state'/('obsidian-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True)
    def save_existing(path):
        if path.exists():
            dest=backup/path.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    config=vault/'.obsidian';config.mkdir(exist_ok=True)
    original_ids=sorted(c['id'] for c in lib.cards if c['original'])
    entries=[]
    for c in lib.cards:
        source=c['_path'];meta,body,raw=parse(source)
        if c['original'] and source.is_relative_to(root/'content/cards'):
            name=re.sub(r'[/\\:\x00]', '-', c['title'])+'.md'
            dest=vault/'网球教学/知识卡片'/name
            if dest.exists():raise ValueError(f'已有同名文件，未覆盖：{dest.name}')
        else:dest=source
        meta['id']=c['id']
        aliases=meta.get('aliases',[])
        if isinstance(aliases,str):aliases=[aliases]
        if c['id'] not in aliases:aliases.append(c['id'])
        meta['aliases']=aliases
        if c.get('is_template'):meta['kind']='模板'
        # Keep the exact body, including headings and spacing.
        body_raw=re.sub(r'\A---\s*\n.*?\n---\s*(?:\n|$)','',raw,count=1,flags=re.S)
        text='---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False,width=1000)+'---\n'+body_raw
        if not dest.exists() or dest.read_text()!=text:
            save_existing(dest);dest.parent.mkdir(parents=True,exist_ok=True)
            stat=source.stat();dest.write_text(text);os.utime(dest,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        entries.append((c,dest.relative_to(vault).as_posix()))
    # Explicitly switch originals only after every file has been copied successfully.
    fieldnotes=config/'fieldnotes.json';save_existing(fieldnotes)
    fieldnotes.write_text(json.dumps({'schema':1,'editable_original_ids':original_ids},ensure_ascii=False,indent=2))
    for folder in ['草稿','附件','健身','训练计划','_写作模板']:(vault/folder).mkdir(exist_ok=True)
    for source in (root/'templates/obsidian').glob('*.md'):
        dest=vault/'_写作模板'/source.name
        if not dest.exists():shutil.copy2(source,dest)
    app=config/'app.json';save_existing(app);settings=json.loads(app.read_text()) if app.exists() else {}
    settings.update(livePreview=True,defaultViewMode='source',newFileLocation='folder',newFileFolderPath='草稿',attachmentFolderPath='附件',alwaysUpdateLinks=True)
    app.write_text(json.dumps(settings,ensure_ascii=False,indent=2))
    template_config=config/'templates.json';save_existing(template_config)
    settings=json.loads(template_config.read_text()) if template_config.exists() else {}
    settings['folder']='_写作模板';template_config.write_text(json.dumps(settings,ensure_ascii=False,indent=2))
    core=config/'core-plugins.json';save_existing(core)
    plugins=json.loads(core.read_text()) if core.exists() else {}
    if isinstance(plugins,dict):plugins['templates']=True
    elif 'templates' not in plugins:plugins.append('templates')
    core.write_text(json.dumps(plugins,ensure_ascii=False,indent=2))
    lines=['---','publish: false','---','# 场边笔记 · 开始写作','','这里保存网站文章的可编辑 Markdown。Obsidian 的实时预览让你直接编辑格式化文字；HTML 由发布流程生成。','','## 修改已有文章','','点击下方标题进入正文，直接修改。保存后，现有任务会在每天上午 9 点检查并同步到两个网站。不是保存后立即上线。','','## 新写一篇','','1. 按 `Cmd+N` 新建笔记，先命名。新笔记默认放在“草稿”。','2. 按 `Cmd+P`，选择“模板：插入模板 / Templates: Insert template”，选知识卡片、训练日志、比赛复盘或阶段进展。','3. 写正文；`id` 已自动生成，之后改标题或移动文件都保留这个 id。','4. 准备发布时，把 `draft` 改为 `false`，再从“草稿”移到“网球教学”“健身”或“训练计划”。','5. 训练和比赛日期填写实际发生日；不确定就留空。','','## 网站上的文章','']
    for label,stage in [('积累','foundation'),('应用','application'),('进展','progress')]:
        lines+=['### '+label,'']
        selected=[(c,p) for c,p in entries if not c.get('is_template') and c.get('stage','foundation')==stage]
        lines += [f'- [[{p[:-3]}|{c["title"]}]]' for c,p in selected] or ['暂时没有记录。']
        lines.append('')
    lines+=['### 已公开的日志模板','']
    lines += [f'- [[{p[:-3]}|{c["title"]}]]' for c,p in entries if c.get('is_template')]
    lines += ['','## 预览、引用和发布','','- `Cmd+E` 切换阅读与编辑；编辑模式选择“实时预览”。','- 用 `[[文章标题]]` 引用另一篇笔记；保留原有 `id`、`sources` 与 `related` 属性。','- 粘贴的图片默认放到“附件”，发布时只上传实际引用的文件。','- 本项目旁的“打开本地预览.command”可查看网页效果；窗口保持开启时，保存约 3 秒后生成，浏览器刷新即可查看。','- Mac 需要开机、Codex 需要运行并能联网，定时同步才会执行。','- `_写作模板`、本页和“草稿”不会作为文章上线。原有九篇卡片的 `content/cards` 现在是发布快照，日常编辑以本笔记库为准。','- 个人简介、首页栏目、来源书架和阅读路线是网站生成页面，不是独立笔记；仍由网站配置维护。','','[查看公开网站](https://qinjishen.github.io/fieldnotes/) · [查看 Sites 网站](https://tennis-fieldnotes-20261101.qinjishenqin.chatgpt.site)','']
    start=vault/'_开始写作.md';save_existing(start);start.write_text('\n'.join(lines))
    with tempfile.TemporaryDirectory() as out:
        migrated=Library(root,Path(out))
        assert set(migrated.by_id)==set(lib.by_id),'文章数量或网址发生变化'
        for cid,old in lib.by_id.items():
            new=migrated.by_id[cid]
            assert new['body']==old['body'],f'正文变化：{cid}'
            assert new['related']==old['related'],f'关联变化：{cid}'
            assert new['sources']==old['sources'],f'来源变化：{cid}'
    return {'articles':len(entries),'originals':len(original_ids),'vault':str(vault),'start':str(start),'backup':str(backup)}

if __name__=='__main__':
    print(json.dumps(setup(),ensure_ascii=False))
