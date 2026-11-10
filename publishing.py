"""Markdown input, Obsidian links and deterministic publication snapshots."""
from pathlib import Path
from urllib.parse import unquote, quote, urlsplit
from datetime import datetime, date
import hashlib, html, json, re, shutil, os
import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin

INPUT = '发布文档'
ASSETS = {'.png','.jpg','.jpeg','.gif','.webp','.avif','.svg','.pdf','.mp4','.webm','.mp3','.wav'}

def slug(text):
    return re.sub(r'[^\w\-\u3400-\u9fff]+', '-', text.strip().lower()).strip('-') or 'section'

def strings(value):
    if value is None: return []
    return [str(v) for v in value] if isinstance(value,list) else [str(value)]

def visible(path, base):
    return not any(part.startswith(('.', '_')) or part=='草稿' for part in path.relative_to(base).parts)

def visible_files(base):
    for directory,dirs,files in os.walk(base):
        dirs[:]=[d for d in dirs if not d.startswith(('.', '_')) and d!='草稿' and not (Path(directory)/d).is_symlink()]
        for name in sorted(files):
            p=Path(directory)/name
            if visible(p,base):yield p

def parse(path):
    raw = path.read_text(encoding='utf-8-sig').replace('\r\n','\n')
    meta, body = {}, raw
    match = re.match(r'\A---\s*\n(.*?)\n---\s*(?:\n|$)', raw, re.S)
    if match:
        meta = yaml.safe_load(match[1]) or {}
        if not isinstance(meta, dict): raise ValueError(f'{path.name}: 文档属性需要是键值列表')
        body = raw[match.end():]
    return meta, body.strip(), raw


STAGES = ('foundation', 'application', 'progress')

def growth_metadata(c):
    """Normalize display metadata for both local notes and published snapshots."""
    stage = str(c.get('stage') or 'foundation')
    if stage not in STAGES:
        raise ValueError(f'{c["title"]}: stage 请填写 foundation、application 或 progress')
    event_date = str(c.get('event_date') or '')
    if event_date:
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', event_date): raise ValueError()
            date.fromisoformat(event_date)
        except ValueError:
            raise ValueError(f'{c["title"]}: event_date 请填写真实发生日期 YYYY-MM-DD')
    # Legacy log templates are identified by their explicit folder, never by body text.
    is_template = str(c.get('kind', '')).lower() in ('template', '模板') or any(part in ('模板', '模版') for part in c['_path'].relative_to(c['_base']).parts)
    c.update(stage=stage, short_title=str(c.get('short_title') or c['title']), event_date=event_date, is_template=is_template)
    if is_template: c['kind'] = '模板'


def editable_original_ids(root):
    """An explicit local handoff lets Obsidian own the original articles."""
    config = Path(root)/INPUT/'.obsidian/fieldnotes.json'
    if not config.exists(): return set()
    data = json.loads(config.read_text())
    ids = data.get('editable_original_ids', [])
    if data.get('schema') != 1 or not isinstance(ids, list) or any(not isinstance(cid,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',cid) for cid in ids):
        raise ValueError('Obsidian 网站编辑配置无效；请保留 .obsidian/fieldnotes.json')
    return set(ids)

class Library:
    def __init__(self, root, out):
        self.root, self.out = Path(root), Path(out)
        self.cards, self.warnings, self.downloads = [], [], {}
        self.editable_originals = editable_original_ids(self.root)
        snapshot_file = self.root/'content/published.json'
        snapshot_cards = json.loads(snapshot_file.read_text()) if not (self.root/INPUT).exists() and snapshot_file.exists() else []
        snapshot_originals = {c['id'] for c in snapshot_cards if c.get('original')}
        self.md = MarkdownIt('commonmark', {'html':False}).enable(['table','strikethrough']).use(footnote_plugin)
        for base, original_source in [(self.root/'content/cards',True),(self.root/INPUT,False)]:
            for path in sorted(visible_files(base)):
                if path.suffix.lower()!='.md' or not visible(path,base): continue
                if path.is_symlink(): raise ValueError(f'请复制文件到发布目录，不要使用符号链接：{path.name}')
                meta, body, raw = parse(path)
                if original_source and str(meta.get('id')) in (self.editable_originals | snapshot_originals): continue
                original = original_source or str(meta.get('id')) in self.editable_originals
                if meta.get('draft') is True or meta.get('publish') is False: continue
                if not body: continue
                cid = str(meta.get('id') or 'n-'+hashlib.sha256(path.relative_to(base).as_posix().encode()).hexdigest()[:12])
                if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',cid): raise ValueError(f'{path.name}: id 只能使用小写字母、数字和短横线')
                title_match = re.search(r'^#\s+(.+)$',body,re.M)
                title = str(meta.get('title') or (title_match[1] if title_match else path.stem))
                tokens = self.md.parse(body)
                excerpt = next((t.content for i,t in enumerate(tokens) if t.type=='inline' and i and tokens[i-1].type=='paragraph_open'), '')
                summary = str(meta.get('summary') or re.sub(r'[\[\]*_`>#]','',excerpt))[:180]
                domain = str(meta.get('domain') or ('训练计划' if '训练计划' in path.relative_to(base).parts else '健身' if any(x in path.relative_to(base).parts for x in ('体能训练','健身')) else '网球教学'))
                domain = {'网球教学':'tennis','网球':'tennis','体能训练':'fitness','体能':'fitness','健身':'fitness','训练计划':'plans','plans':'plans','tennis':'tennis','fitness':'fitness'}.get(domain)
                if not domain: raise ValueError(f'{path.name}: domain 请填写 网球教学、健身 或 训练计划')
                c = dict(meta, id=cid,title=title,summary=summary,body=body,filename=cid+'.md',
                         tags=strings(meta.get('tags')), aliases=strings(meta.get('aliases')), domain=domain,
                         _explicit_summary=bool(meta.get('summary')),kind=str(meta.get('kind','学习笔记')),sources=meta.get('sources',[]) if original else [],
                         related=meta.get('related',[]) if original else [], original=original,
                         updated=str(meta.get('updated') or ('2026-11-01' if original else datetime.fromtimestamp(path.stat().st_mtime).date())),
                         _path=path,_base=base)
                self.cards.append(c)
                self.downloads[cid]=raw
        if not (self.root/INPUT).exists() and (self.root/'content/published.json').exists():
            for c in snapshot_cards:
                c['_base']=self.root/INPUT
                c['_path']=c['_base']/c.pop('_relative')
                self.downloads[c['id']]=c.pop('_raw')
                self.cards.append(c)
            assets=self.root/'content/published-assets'
            if assets.exists(): shutil.copytree(assets,out/'assets',dirs_exist_ok=True)
        for c in self.cards: growth_metadata(c)
        self.by_id={c['id']:c for c in self.cards}
        if len(self.by_id)!=len(self.cards): raise ValueError('文章 id 重复，请为不同文章设置不同 id')
        self.lookup={}
        for c in self.cards:
            p=c['_path']; base=c['_base']
            keys=[c['id'],c['title'],p.stem,p.name,p.relative_to(base).as_posix(),p.relative_to(base).with_suffix('').as_posix(),*c['aliases']]
            for key in keys:
                self.lookup.setdefault(key.casefold(),set()).add(c['id'])
        # Render once to gather all forward links before backlinks are generated.
        for c in self.cards:
            if '_html' not in c: c['_html']=self.render(c)
        for c in self.cards:
            for r in c['related']:
                if r['id'] not in self.by_id: raise ValueError(f'{c["title"]}: 关联文章不存在 {r["id"]}')
        (out/'markdown').mkdir(parents=True,exist_ok=True)
        for c in self.cards: (out/'markdown'/c['filename']).write_text(self.downloads[c['id']],encoding='utf-8')

    def snapshot(self):
        if not (self.root/INPUT).exists(): return
        exported=[]
        # These files are publication snapshots; the vault is the editable source.
        for cid in self.editable_originals:
            dest = self.root/'content/cards'/f'{cid}.md'
            if cid in self.by_id:
                dest.write_text(self.downloads[cid], encoding='utf-8')
            elif dest.exists():
                dest.unlink()
        for c in self.cards:
            if c['original'] and c['id'] not in self.editable_originals: continue
            item={k:v for k,v in c.items() if k not in ('_base','_path')}
            item['_relative']=c['_path'].relative_to(c['_base']).as_posix()
            item['_raw']=self.downloads[c['id']]
            exported.append(item)
        (self.root/'content/published.json').write_text(json.dumps(exported,ensure_ascii=False,default=str),encoding='utf-8')
        dest=self.root/'content/published-assets'
        if dest.exists(): shutil.rmtree(dest)
        if (self.out/'assets').exists(): shutil.copytree(self.out/'assets',dest)

    def resolve_note(self, target, c):
        if not target: return c
        local=(c['_path'].parent/target).resolve()
        for other in self.cards:
            if other['_path'].resolve() in (local,local.with_suffix('.md')): return other
        candidates=self.lookup.get(target.casefold(),set()) or self.lookup.get(re.sub(r'\.md$','',target,flags=re.I).casefold(),set())
        if len(candidates)>1: raise ValueError(f'{c["title"]}: 链接「{target}」有多个同名文档，请写相对路径')
        return self.by_id[next(iter(candidates))] if candidates else None

    def link(self, target, c, image=False):
        target=unquote(target.strip())
        parsed=urlsplit(target)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme in ('http','https') or (parsed.scheme=='mailto' and not image): return target
            raise ValueError(f'{c["title"]}: 不支持的链接协议 {parsed.scheme}')
        path, _, anchor=target.partition('#')
        if image or Path(path).suffix.lower() in ASSETS:
            base=c['_base'].resolve()
            file=(c['_path'].parent/path).resolve()
            if not file.is_relative_to(base) or not file.is_file():
                candidates=[p for p in visible_files(base) if p.name==Path(path).name and p.is_file() and p.resolve().is_relative_to(base)]
                if len(candidates)!=1: raise ValueError(f'{c["title"]}: 找不到附件或同名附件不唯一：{path}')
                file=candidates[0]
            if file.suffix.lower() not in ASSETS: raise ValueError(f'{c["title"]}: 不支持这种附件：{path}')
            name=hashlib.sha256(file.read_bytes()).hexdigest()[:16]+file.suffix.lower()
            (self.out/'assets').mkdir(exist_ok=True)
            shutil.copyfile(file,self.out/'assets'/name)
            return '../assets/'+name
        other=self.resolve_note(path,c)
        if not other:
            self.warnings.append(f'{c["title"]}: 尚未发布的链接「{target}」')
            return None
        if other['id']!=c['id'] and not any(r['id']==other['id'] for r in c['related']):
            c['related'].append({'id':other['id'],'type':'文中引用','reason':'这篇文章在正文中引用了该观点。'})
        if anchor.startswith('^'):
            self.warnings.append(f'{c["title"]}: 块引用暂定位到文章：{target}')
            anchor=''
        return other['id']+'.html'+('#'+quote(slug(anchor)) if anchor else '')

    def render(self,c):
        # Transform wiki syntax only in text tokens; fenced/inline code remains literal.
        def wiki(state,silent):
            start=state.pos
            match=re.match(r'(!?)\[\[([^\]\n]+)\]\]',state.src[start:])
            if not match: return False
            if not silent:
                is_image=bool(match[1]); target,sep,label=match[2].partition('|')
                if is_image and Path(target.split('#')[0]).suffix.lower() not in ASSETS:
                    # A note embed remains a linked article rather than duplicated content.
                    is_image=False
                url=self.link(target,c,is_image)
                label=label if sep and not re.fullmatch(r'\d+(x\d+)?',label) else target.split('#')[0]
                token=state.push('html_inline','',0)
                if not url: token.content='<span class="unresolved-link" title="对应文章尚未发布">'+html.escape(label)+'</span>'
                elif is_image: token.content=f'<img loading="lazy" src="{html.escape(url,quote=True)}" alt="{html.escape(label,quote=True)}">'
                else: token.content=f'<a href="{html.escape(url,quote=True)}">{html.escape(label)}</a>'
            state.pos+=len(match[0]); return True
        md=MarkdownIt('commonmark',{'html':False}).enable(['table','strikethrough']).use(footnote_plugin)
        md.inline.ruler.before('link','wikilink',wiki)
        body=re.sub(r'^#\s+[^\n]+\n*','',c['body'],count=1)
        tokens=md.parse(body)
        headings=[]; used={}
        def walk(items):
            for t in items:
                if t.type in ('link_open','image'):
                    attr='src' if t.type=='image' else 'href'; target=t.attrGet(attr)
                    if target is not None:
                        url=self.link(target,c,t.type=='image')
                        if url: t.attrSet(attr,url)
                        else:
                            t.attrs.pop(attr,None);t.attrSet('class','unresolved-link');t.attrSet('title','对应文章尚未发布')
                if t.children: walk(t.children)
        walk(tokens)
        for i,t in enumerate(tokens):
            if t.type=='heading_open':
                title=tokens[i+1].content; key=slug(title); used[key]=used.get(key,0)+1
                anchor=key+(f'-{used[key]}' if used[key]>1 else '')
                t.attrSet('id',anchor)
                if t.tag in ('h2','h3'): headings.append((anchor,title))
        c['_toc']=headings
        return md.renderer.render(tokens,md.options,{})

def fingerprint(root):
    root=Path(root); h=hashlib.sha256()
    files=[]
    editable = editable_original_ids(root)
    config = root/INPUT/'.obsidian/fieldnotes.json'
    if config.exists(): files.append(config)
    snapshots = {root/'content/cards'/f'{cid}.md' for cid in editable}
    for folder in [INPUT,'content','static','docs','templates']:
        base=root/folder
        files.extend(p for p in visible_files(base) if p.is_file() and p not in snapshots and visible(p,base) and p.name!='published.json' and 'published-assets' not in p.parts)
    files.extend(p for pattern in ['*.py','requirements.txt'] for p in root.glob(pattern))
    for p in sorted(files):
        h.update(p.relative_to(root).as_posix().encode());h.update(b'\0')
        if p.is_relative_to(root/INPUT) and p.suffix.lower()!='.md':
            stat=p.stat();h.update(f'{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ctime_ns}'.encode())
        else:h.update(p.read_bytes())
        h.update(b'\0')
    return h.hexdigest()
