from pathlib import Path
import json, re, html, shutil

ROOT = Path(__file__).resolve().parent
import os
from publishing import Library
OUT = Path(os.environ.get('FIELDNOTES_OUTPUT', str(ROOT / 'dist')))
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'cards').mkdir(exist_ok=True)
SOURCES = json.loads((ROOT / 'content/sources.json').read_text())
SOURCE_MAP = {s['id']: s for s in SOURCES}
library = Library(ROOT, OUT)
CARDS = library.cards
BY_ID = {c['id']: c for c in CARDS}
for c in CARDS:
    assert all(s['id'] in SOURCE_MAP and s['locator'] for s in c['sources'])

def e(s): return html.escape(str(s), quote=True)
def inline(s):
    s = e(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return s

def markdown(body):
    parts = []
    for block in body.strip().split('\n\n'):
        lines = block.splitlines()
        if block.startswith('# '): continue
        if block.startswith('## '): parts.append('<h2>' + inline(block[3:]) + '</h2>')
        elif block.startswith('> '): parts.append('<blockquote>' + inline(block[2:]) + '</blockquote>')
        elif all(x.startswith('- ') for x in lines): parts.append('<ul>' + ''.join('<li>' + inline(x[2:]) + '</li>' for x in lines) + '</ul>')
        else: parts.append('<p>' + inline(block) + '</p>')
    return '\n'.join(parts)

def href(cid, prefix=''): return prefix + 'cards/' + cid + '.html'
def tags(c): return ''.join('<span class="tag">' + e(t) + '</span>' for t in c['tags'])
def card_link(cid, reason='', prefix='', rel=''):
    c = BY_ID[cid]
    return f'<a class="relation" href="{href(cid,prefix)}"><span class="relation-type">{e(rel or c["id"].upper())}</span><strong>{e(c["title"])}</strong><span>{e(reason or c["summary"])}</span><b aria-hidden="true">↗</b></a>'

paths = [
    ('01','我想拍清楚，也看明白自己的动作','先校准判断，再准备足够清晰、能够比较的画面。',['o001','o002','o003','o004'],'读完可做：为下一次录像写下一个问题，并列出画面必须保留的信息。'),
    ('02','为什么训练能做，比赛却做不出来','先描述能做到的条件，再写一个带检查办法的过渡任务。',['o005','o003','o008'],'读完可做：写出在哪种条件下能完成、加入什么后变化，以及下一次怎样复查。'),
    ('03','打完比赛，下一次究竟练什么','分开检查选择与执行，向前追查，在同类机会中核对，再定任务。',['o006','o007','o009','o008'],'读完可做：从若干回合中选出一个候选问题，保留依据，并提出一个可检验的解释。')]
path_html = '<div class="page-heading"><span class="eyebrow">READING PATHS</span><h1>带着问题，<em>连起来读。</em></h1><p>卡片可以独立阅读；路线把它们组织成一次完整的思考。</p></div>'
for num,title,desc,ids,outcome in paths:
    path_html += f'<section class="path-section"><div class="path-intro"><span class="large-num">{num}</span><h2>{title}</h2><p>{desc}</p><div class="outcome">{outcome}</div></div><div class="path-steps">'+''.join(card_link(cid,prefix='',rel=f'第 {i+1} 步') for i,cid in enumerate(ids))+'</div></section>'

source_html = '<div class="page-heading"><span class="eyebrow">THE SOURCE SHELF</span><h1>观点有来处，<em>也有边界。</em></h1><p>书架保留教材结构；卡片按问题重新组织。一本书可以支持多张卡片，一张卡片也可以连接多个来源。</p></div>'
for s in SOURCES:
    linked = [c for c in CARDS if any(r['id']==s['id'] for r in c['sources'])]
    ext = f'<a class="text-link" target="_blank" rel="noopener noreferrer" href="{e(s["url"])}">查看原来源 ↗</a>' if s['url'] else '<span class="muted">本地写作资料 · 网站展示整理结果</span>'
    source_html += f'<section class="source-entry" id="{s["id"]}"><div><span class="eyebrow">{e(s["status"])}</span><h2>{e(s["title"])}</h2><p>{e(s["author"])}</p><p class="muted">{e(s["detail"])}</p>{ext}</div><div><p>{e(s["note"])}</p><h3>使用这一来源的卡片 · {len(linked)}</h3>'+''.join(f'<a class="source-card" href="{href(c["id"])}"><span>{c["id"].upper()}</span>{e(c["title"])} ↗</a>' for c in linked)+'</div></section>'

about = '''<div class="page-heading"><span class="eyebrow">ABOUT THE NOTE SYSTEM</span><h1>小文章，<em>可以长成一张网。</em></h1><p>从现有的“网球观察与检验”开始，试着把可独立解释的观点写成卡片，再组织成可走通的阅读路线。</p></div><div class="about-layout"><article class="prose"><h2>一张卡片，要讲清什么</h2><p>标题直接表达一个观点或问题。正文解释它为什么有用，给出一个具体例子或使用办法，再写明适用条件。读者即使直接打开这一篇，也应能理解主张。</p><p>“原子”不等于越短越好。删掉条件会误导读者时，条件就应该和观点留在一起。完整练习的目的、组织与检查办法，也不应为了拆分而变得无法执行。</p><h2>三层内容，各有用途</h2><ul><li><strong>来源资料：</strong>按书名、版本和章节保留原始脉络，记录核对范围。</li><li><strong>观点卡片：</strong>用自己的话讲清一个问题，可由多个来源共同支持；条件不同的意见分别说明。</li><li><strong>阅读路线：</strong>按读者要解决的问题串联卡片，也可以重新组合成长文章。</li></ul><h2>连接要说明理由</h2><p>本组使用“前提、下一步、应用、边界、对照”等关系，旁边写一句为什么值得继续读。反向引用自动列出哪些卡片用到了本篇，帮助读者发现它在不同问题中的位置。</p><h2>从教材扩充时怎么做</h2><p>先挑一个真实问题，读相应章节，记录作者的主张与条件，再看现有卡片是否已经覆盖。相同观点可以补来源，新的问题再建卡。每次加入一小组，也回头检查旧卡是否需要修订。</p><p>后续的体能训练资料可以沿用这套结构。运动人群、训练阶段、负荷与适用条件，应随主张一起保留；本批尚未建立体能训练卡片。</p><h2>这次样板的范围</h2><p>这 9 张卡片集中处理观察方法、练习条件与比赛复盘。它们来自第 1、2、9 篇及配套资料的进一步拆分。原来的九篇并没有被逐篇替换。</p><p>“技术框架、平衡、动力链、关节角度、拍面、击球区与甜区”等专题，只取了本组确有需要的测量边界，其余仍待逐项核对和整理。本次也没有把整本教材全部转成卡片。</p><h2>保持文章可以继续修改</h2><p>每张卡片都有稳定编号、独立地址和可下载的 Markdown。正文与网站来自同一份卡片内容。当前版本用于阅读与结构验证；编辑在本地文件中完成。</p></article><aside class="template"><span class="eyebrow">CARD ANATOMY</span><h2>一张卡片的骨架</h2><ol><li><strong>观点式标题</strong><span>这篇究竟想说明什么？</span></li><li><strong>核心解释</strong><span>为什么成立，或为什么值得做？</span></li><li><strong>具体使用</strong><span>例子、观察问题或练习办法。</span></li><li><strong>条件与边界</strong><span>适用于谁，在哪种情境下？</span></li><li><strong>来源位置</strong><span>哪本书、哪一章；哪些是自己的整理？</span></li><li><strong>有理由的连接</strong><span>接着读哪篇，为什么？</span></li></ol><a class="primary" href="cards/o001.html">看一张完整卡片 ↗</a></aside></div>'''
from redesign import render
render(ROOT, CARDS, SOURCES, lambda c: c['_html'], {'paths': path_html, 'sources': source_html, 'about': about}, OUT)
shutil.copytree(ROOT/'static', OUT, dirs_exist_ok=True)
(OUT/'build-info.json').write_text(json.dumps({'articles':len(CARDS)},ensure_ascii=False))
if os.environ.get('FIELDNOTES_PREVIEW') != '1': library.snapshot()
print(json.dumps({'articles':len(CARDS), 'warnings': library.warnings}, ensure_ascii=False))
