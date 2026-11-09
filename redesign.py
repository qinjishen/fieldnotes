"""Render the personal overview and the problem-led reading interface."""
import html
import json
import re

def render(root, cards, sources, markdown, supporting, out):
    discovery = json.loads((root / 'content/discovery.json').read_text())
    questions, topics, profile = discovery['questions'], discovery['topics'], discovery['profile']
    cards = sorted(cards, key=lambda c: (not c['original'], c['updated']), reverse=True)
    tennis_cards = [c for c in cards if c['domain']=='tennis']
    fitness_cards = [c for c in cards if c['domain']=='fitness']
    for tag in sorted({tag for c in cards if not c['original'] for tag in c['tags']}):
        import hashlib
        topics.append({'id':'tag-'+hashlib.sha256(tag.encode()).hexdigest()[:8], 'label':tag, 'cards':[c['id'] for c in cards if tag in c['tags']]})
    by_id = {c['id']: c for c in cards}
    source_map = {s['id']: s for s in sources}
    for group in questions + topics:
        assert all(cid in by_id for cid in group['cards'])
    e = lambda value: html.escape(str(value), quote=True)
    href = lambda cid, prefix='': prefix + 'cards/' + cid + '.html'

    def base(title, body, prefix='', home=False, desc='关于网球教学与体能训练的学习笔记。按问题找到文章，沿着观点继续阅读。'):
        return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} · 场边笔记</title><meta name="description" content="{e(desc)}"><meta name="theme-color" content="#151a1c"><link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{prefix}style.css"><script defer src="{prefix}app.js"></script><script defer src="{prefix}portal.js"></script></head><body class="{'home-page' if home else 'knowledge-page'}"><a class="skip" href="#main">跳到正文</a>{body}</body></html>'''

    def side(active='tennis', prefix=''):
        main = [('tennis','tennis.html','网球'),('fitness','fitness.html','健身'),('plans','plans.html','训练计划'),('profile','profile.html','个人简介')]
        sub = [('paths','paths.html','按问题阅读'),('sources','sources.html','来源书架'),('about','about.html','关于这些笔记')]
        links = lambda items: ''.join(f'<a href="{prefix}{url}" {"aria-current=page" if key==active else ""}>{label}</a>' for key,url,label in items)
        topic_links = ''.join(f'<a class="sub-link" href="{prefix}{active}.html?topic={t["id"]}">{t["label"]}</a>' for t in topics if any(c['domain']==active and c['id'] in t['cards'] for c in cards)) if active in ('tennis','fitness') else ''
        main_nav=''.join(links([item])+(topic_links if item[0]==active else '') for item in main)
        return f'''<aside class="site-nav"><a class="site-name" href="{prefix}index.html">场边笔记<span>{e(profile['name'])} 的学习笔记</span></a><a class="nav-search" href="{prefix}search.html#find"><span>查找文章</span><span aria-hidden="true">⌕</span></a><nav aria-label="知识库导航"><span class="nav-label">知识领域</span>{main_nav}<span class="nav-label">更多入口</span>{links(sub)}</nav><a class="back-home" href="{prefix}index.html">← 回到个人首页</a></aside>'''

    def layout(title, body, active='tennis', prefix='', aside='', desc=None):
        right = f'<aside class="context-nav">{aside}</aside>' if aside else ''
        domain_label={'tennis':'网球','fitness':'健身','plans':'训练计划','profile':'个人简介'}
        trail=f'<a href="{prefix}{active}.html">{domain_label[active]}</a>' if active in domain_label else ''
        if active=='search': trail='<span>全部文章</span>'
        if active not in ('fitness','tennis','search','plans','profile'): trail += '<span>/</span><span>'+e(title)+'</span>'
        content = f'''<div class="knowledge-shell">{side(active,prefix)}<main id="main" class="knowledge-main"><div class="breadcrumbs"><a href="{prefix}index.html">首页</a><span>/</span>{trail}</div>{body}<footer><a href="{prefix}index.html">场边笔记</a><span>持续整理 · 2026.11</span></footer></main>{right}</div>'''
        return base(title,content,prefix,desc=desc or '从问题进入知识库，阅读独立观点、来源和相关笔记。')

    def entry(cid, prefix='', description=True):
        c = by_id[cid]
        return f'<a class="entry" href="{href(cid,prefix)}"><h3>{e(c["title"])}<span aria-hidden="true">↗</span></h3>{"<p>"+e(c["summary"])+"</p>" if description else ""}</a>'

    def relation(cid, reason, prefix='', kind=''):
        return f'<a class="related-row" href="{href(cid,prefix)}"><span class="relation-kind">{e(kind)}</span><div><h3>{e(by_id[cid]["title"])}</h3><p>{e(reason)}</p></div><span aria-hidden="true">↗</span></a>'

    rows, index = [], []
    for c in cards:
        qs = [q for q in questions if c['id'] in q['cards']]
        ts = [t for t in topics if c['id'] in t['cards']]
        rows.append(f'''<article class="note-row" data-id="{c['id']}" data-domain="{c['domain']}"><div class="row-meta"><span>{e(' · '.join(t['label'] for t in ts[:2]))}</span><span class="note-id">{e(c['id'].upper())}</span></div><h2><a href="{href(c['id'])}">{e(c['title'])}</a></h2><p>{e(c['summary'])}</p></article>''')
        index.append({'id':c['id'],'domain':c['domain'],'title':c['title'],'summary':c['summary'],'body':c['body'],'sources':' '.join(source_map[s['id']]['title'] for s in c['sources']),'aliases':c.get('aliases',[])+[term for q in qs for term in [q['label'],*q['terms']]],'topics':[t['id'] for t in ts]})
    topic_buttons = f'<button class="topic-button selected" data-topic="all" aria-pressed="true">全部文章 <span>{len(cards)}</span></button>' + ''.join(f'<button class="topic-button" data-topic="{t["id"]}" aria-pressed="false">{e(t["label"])}</button>' for t in topics)
    questions_html = ''.join(f'<a class="question-link" href="tennis.html?question={q["id"]}">{q["label"]}<span aria-hidden="true">↗</span></a>' for q in questions)
    tennis = f'''<header class="page-heading"><span class="eyebrow">TENNIS / KNOWLEDGE NOTES</span><h1>网球教学</h1><p>找到你遇到的问题，读懂一个观点，再回到球场上检验。</p></header><section class="finder" id="find" aria-label="查找文章"><form id="search-form" role="search"><label for="search">搜索问题、观点或来源</label><div class="search-box"><span aria-hidden="true">⌕</span><input id="search" type="search" name="q" placeholder="试试：训练会，比赛不会" autocomplete="off"><button type="submit">查找</button></div></form><details class="question-picker"><summary>从常见问题开始</summary><div>{questions_html}</div></details></section><section class="article-list" aria-labelledby="list-title"><div class="list-top"><h2 id="list-title">全部文章</h2><span id="result-count" role="status" aria-live="polite">{len(cards)} 篇文章</span></div><div class="topics" aria-label="按主题筛选">{topic_buttons}</div><div id="query-context" hidden></div><div id="notes">{''.join(rows)}</div><div id="empty" hidden><h3>暂时没有匹配的文章</h3><p>试试较短的关键词，或切换主题。</p><button id="clear" class="text-button">清除搜索与筛选 ↗</button></div><p id="search-error" hidden>搜索暂时未能载入。你仍可浏览下方全部文章，或刷新后重试。</p></section>'''
    tennis_aside = f'<span class="nav-label">从一个问题进入</span>{questions_html}<div class="context-bottom"><span class="nav-label">当前整理范围</span><p>观察与检验<br>9 篇原子文章</p><a href="sources.html">查看依据与来源 ↗</a></div>'
    for domain,label,selected in [('tennis','网球教学',tennis_cards),('fitness','体能训练',fitness_cards),('search','全部文章',cards)]:
        if not selected and domain=='fitness': continue
        body=tennis.replace(''.join(rows), ''.join(row for row,c in zip(rows,cards) if domain=='search' or c['domain']==domain))
        body=body.replace(f'{len(cards)} 篇文章',f'{len(selected)} 篇文章').replace(f'<span>{len(cards)}</span>',f'<span>{len(selected)}</span>')
        body=body.replace('<section class="finder"','<section data-domain="'+domain+'" class="finder"')
        if domain=='search':
            body=body.replace('网球教学','全部文章').replace('TENNIS / KNOWLEDGE NOTES','ALL NOTES')
        if domain=='fitness':
            body=body.replace('网球教学','体能训练').replace('TENNIS / KNOWLEDGE NOTES','CONDITIONING / KNOWLEDGE NOTES').replace('再回到球场上检验','在训练中检验').replace('试试：训练会，比赛不会','搜索体能训练的文章')
            body=re.sub(r'<details class="question-picker">.*?</details>','',body)
        aside=tennis_aside.replace('观察与检验<br>9 篇原子文章',f'{len(selected)} 篇文章') if domain=='tennis' else '<span class="nav-label">体能训练</span><p>按主题找到文章，沿着文中的链接继续阅读。</p>'
        if domain=='search': aside=''
        (out/f'{domain}.html').write_text(layout(label,body,domain,aside=aside))
    (out/'search-index.json').write_text(json.dumps({'cards':index,'questions':questions,'topics':topics},ensure_ascii=False))

    for c in cards:
        body_html = markdown(c)
        headings = c['_toc']
        def add_anchor(m):
            anchor = f'section-{len(headings)+1}'
            headings.append((anchor,m[1]))
            return f'<h2 id="{anchor}">{m[1]}</h2>'

        citations = []
        for s in c['sources']:
            citations.append(f'<li><a href="../sources.html#{s["id"]}">{e(source_map[s["id"]]["title"])}</a><span>{e(s["locator"])}</span><p>{e(s["scope"])}</p></li>')
        forward = ''.join(relation(r['id'],r['reason'],'../',r['type']) for r in c['related'])
        backlinks = [(other,r) for other in cards for r in other['related'] if r['id']==c['id']]
        reverse = ''.join(relation(other['id'],r['reason'],'../','引用本篇') for other,r in backlinks)
        relevant_questions = ''.join(f'<a href="../tennis.html?question={q["id"]}">{e(q["label"])} ↗</a>' for q in questions if c['id'] in q['cards'])
        toc = '<span class="nav-label">这篇文章</span>' + ''.join(f'<a class="toc-link" href="#{a}">{e(t)}</a>' for a,t in headings) + '<a class="toc-link" href="#sources">依据与来源</a><a class="toc-link" href="#related">继续阅读</a>'
        toc += f'<div class="context-bottom"><span class="nav-label">相关问题</span>{relevant_questions}</div>'
        standfirst = '<p class="standfirst">'+e(c['summary'])+'</p>' if c['_explicit_summary'] else ''
        body = f'''<article class="reading"><header class="article-heading"><span class="eyebrow">{e(c['id'].upper())} / {e(' · '.join(c['tags']))}</span><h1>{e(c['title'])}</h1>{standfirst}<div class="article-meta"><span>{e(c['kind'])}</span><span>{e(c['updated'])}</span><a href="../markdown/{c['filename']}" download>下载 Markdown ↓</a></div></header><div class="prose">{body_html}</div><section class="source-notes" id="sources"><details><summary>依据与来源 <span>{len(c['sources'])}</span></summary><ul>{''.join(citations)}</ul><p>{('本批卡片中的情境是说明方法的假设示例，不对应队内实测记录。' if c['original'] else '来源说明请见正文。')}</p></details></section><section id="related" class="related-section"><h2>继续阅读</h2>{forward}</section><details class="backlinks"><summary>哪些文章引用了它 <span>{len(backlinks)}</span></summary>{reverse}</details><div class="reading-end"><a href="../{c['domain']}.html">← 返回主题</a><a href="#main">回到文首 ↑</a></div></article>'''
        if not citations:
            body=re.sub(r'<section class="source-notes".*?</section>','',body)
            toc=toc.replace('<a class="toc-link" href="#sources">依据与来源</a>','')
        (out/'cards'/f'{c["id"]}.html').write_text(layout(c['title'],body,active=c['domain'],prefix='../',aside=toc,desc=c['summary']))

    for key,title in [('paths','按问题阅读'),('sources','来源书架'),('about','关于这些笔记')]:
        body = supporting[key]
        body = body.replace('带着问题，<em>连起来读。</em>','按问题阅读').replace('观点有来处，<em>也有边界。</em>','来源书架').replace('小文章，<em>可以长成一张网。</em>','关于这些笔记')
        (out/f'{key}.html').write_text(layout(title,body,key))
    from portal import render_portal
    render_portal(root,out,cards,profile,base,layout,topics)
    print(f'Rendered {len(cards)} articles and connected topic maps.')
