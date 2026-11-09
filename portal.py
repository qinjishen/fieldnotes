"""Dark topic landing and accessible article relationship maps."""
import html, json, math

def graph_data(cards, all_cards):
    ids={c['id'] for c in cards}; edges={}
    for c in cards:
        for r in c['related']:
            if r['id'] not in ids or r['id']==c['id']:continue
            pair=tuple(sorted((c['id'],r['id'])))
            edges.setdefault(pair,[]).append({'from':c['id'],'to':r['id'],'type':r['type'],'reason':r['reason']})
    return {'nodes':[{'id':c['id'],'title':c['title'],'summary':c['summary'],'tags':c['tags'],'body':c['body'],'aliases':c.get('aliases',[]),'domain':c['domain']} for c in cards],
            'edges':[{'a':a,'b':b,'relations':relations} for (a,b),relations in edges.items()],
            'related':{c['id']:[{'id':r['id'],'title':next(o['title'] for o in all_cards if o['id']==r['id']),'reason':r['reason'],'type':r['type']} for r in c['related']] + [{'id':o['id'],'title':o['title'],'reason':r['reason'],'type':'引用本篇'} for o in all_cards for r in o['related'] if r['id']==c['id'] and not any(a['id']==o['id'] for a in c['related'])] for c in cards}}

def render_portal(root,out,cards,profile,base,layout,topics):
    e=lambda x:html.escape(str(x),quote=True)
    counts={d:sum(c['domain']==d for c in cards) for d in ('tennis','fitness','plans')}
    home=f'''<main id="main" class="orbit-home"><section class="orbit-intro"><a class="small-brand" href="index.html"><span class="brand-dot"></span> QINJISHEN / FIELDNOTES</a><div class="intro-main"><p class="eyebrow">学习 · 实践 · 建立联系</p><h1>场边笔记<span>.</span></h1><p class="intro-lead">一个观点，一篇文章。<br>在联系中理解，在训练中检验。</p><p class="intro-description">{e(profile['intro'])}</p><form class="home-search" action="search.html" role="search"><label for="home-query">从一个问题开始</label><div><input type="search" name="q" id="home-query" placeholder="查找问题或文章" autocomplete="off"><button type="submit" aria-label="搜索文章">↗</button></div></form><div class="intro-links"><a href="search.html">全部文章 <span>{len(cards)}</span></a><a href="paths.html">阅读路线 ↗</a></div></div><div class="orbit-signature"><span>{e(profile['name'])} 的学习笔记</span><a href="about.html">关于这些笔记 ↗</a></div></section><section class="orbit-right" aria-label="选择一个主题"><div class="orbit-caption"><span>四个入口，持续生长的笔记。</span><button id="motion-toggle" type="button" aria-pressed="false">暂停浮动</button></div><nav class="orbit-cluster" aria-label="主题入口">
<a class="orbit orbit-tennis" href="tennis.html"><span class="orbit-kicker">01 / TENNIS</span><strong>网球</strong><span>{counts['tennis']} 篇文章 · 探索联系 ↗</span></a>
<a class="orbit orbit-fitness" href="fitness.html"><span class="orbit-kicker">02 / FITNESS</span><strong>健身</strong><span>{str(counts['fitness'])+' 篇文章' if counts['fitness'] else '笔记正在生长'} ↗</span></a>
<a class="orbit orbit-plans" href="plans.html"><span class="orbit-kicker">03 / PRACTICE</span><strong>训练计划</strong><span>周计划 · 阶段安排 ↗</span></a>
<a class="orbit orbit-profile" href="profile.html"><span class="orbit-kicker">04 / ABOUT</span><strong>个人简介</strong><span>认识这里的作者 ↗</span></a></nav><div class="orbit-bottom"><span class="tiny-dot"></span><p>从一个主题出发，找到一篇值得读的文章。</p></div></section></main>'''
    (out/'index.html').write_text(base('首页',home,home=True))
    for domain,label,english in [('tennis','网球','TENNIS'),('fitness','健身','FITNESS')]:
        selected=[c for c in cards if c['domain']==domain]
        data=graph_data(selected,cards)
        qs=json.loads((root/'content/discovery.json').read_text())['questions']
        data['questions']=qs
        data['topics']=topics
        for n in data['nodes']:
            n['topics']=[t['id'] for t in topics if n['id'] in t['cards']]
            n['aliases'] += [s for q in qs if n['id'] in q['cards'] for s in [q['label'],*q['terms']]]
        (out/f'{domain}-graph.json').write_text(json.dumps(data,ensure_ascii=False))
        nav=f'''<header class="map-topbar"><a class="map-brand" href="index.html"><span class="brand-dot"></span>场边笔记</a><nav aria-label="主要导航"><a href="tennis.html" {'aria-current="page"' if domain=='tennis' else ''}>网球</a><a href="fitness.html" {'aria-current="page"' if domain=='fitness' else ''}>健身</a><a href="plans.html">训练计划</a><a href="profile.html">个人简介</a></nav><a class="map-search-link" href="search.html">查找文章 ↗</a></header>'''
        header=f'''<div class="map-heading"><div><p class="eyebrow">{english} / CONNECTED NOTES</p><h1>{label}<span>从一个观点，走向另一个。</span></h1><p>每个节点是一篇独立文章，连线来自文章中明确写下的联系。</p></div><a class="back-overview" href="index.html">← 返回首页</a></div>'''
        if not selected:
            body=f'''{nav}<main id="main" class="map-main">{header}<section class="map-empty"><span class="empty-orb" aria-hidden="true"></span><h2>这里正在等待第一篇笔记。</h2><p>未来会围绕训练原则、练习方法与适用条件，逐篇整理。</p><a href="tennis.html">先探索网球文章 ↗</a></section></main>'''
        else:
            height=max(570,math.ceil(len(selected)/3)*165+90)
            points={c['id']:([160,500,840][i%3]+([0,20,-10][i%3] if (i//3)%2 else 0),75+(i//3)*165+[0,30,5][i%3]) for i,c in enumerate(selected)}
            lines=''.join(f'<line data-a="{edge["a"]}" data-b="{edge["b"]}" x1="{points[edge["a"]][0]}" y1="{points[edge["a"]][1]}" x2="{points[edge["b"]][0]}" y2="{points[edge["b"]][1]}"/>' for edge in data['edges'])
            nodes=''
            for i,c in enumerate(selected):
                x,y=points[c['id']]; color=['sage','sand','blue'][(i//3)%3]
                nodes+=f'<a class="graph-node node-{color}" data-node="{c["id"]}" href="cards/{c["id"]}.html" style="left:{x/10}%;top:{y}px" aria-label="阅读：{e(c["title"])}"><span class="node-disc">{i+1:02}</span><span class="node-title">{e(c["title"])}</span></a>'
            lists=''.join(f'<article class="map-list-row" data-list-node="{c["id"]}"><span>{i+1:02}</span><div><h2><a href="cards/{c["id"]}.html">{e(c["title"])}</a></h2><p>{e(c["summary"])}</p></div><span aria-hidden="true">↗</span></article>' for i,c in enumerate(selected))
            first=selected[0]
            body=f'''{nav}<main id="main" class="map-main" data-graph-domain="{domain}">{header}<div class="map-toolbar"><form id="graph-search-form" role="search"><label for="graph-search" class="sr-only">在{label}文章中查找</label><span aria-hidden="true">⌕</span><input id="graph-search" type="search" placeholder="查找问题或文章" autocomplete="off"><button type="submit">查找</button></form><span id="graph-count" role="status" aria-live="polite">{len(selected)} 篇文章 · {len(data['edges'])} 处连接</span><div class="map-view-switch" aria-label="阅读方式"><button id="view-graph" aria-pressed="true">关系图</button><button id="view-list" aria-pressed="false">文章列表</button></div></div><div id="graph-scope" hidden><span></span><button id="graph-scope-clear" type="button">清除筛选</button></div><div class="map-workspace"><div class="map-left"><div id="map-visual"><div class="map-legend"><span><i class="legend-dot"></i>独立文章</span><span><i class="legend-line"></i>已有联系</span><span class="map-help">停留查看关联，点击阅读</span></div><div class="graph-scroll" tabindex="0" role="region" aria-label="文章关系图，可横向滚动"><div class="graph-stage" style="height:{height}px"><svg class="graph-lines" viewBox="0 0 1000 {height}" preserveAspectRatio="none" aria-hidden="true">{lines}</svg>{nodes}</div></div></div><div id="map-list" hidden>{lists}</div><p id="graph-empty" hidden>没有找到匹配的文章。<button id="graph-clear" type="button">清除搜索</button></p><p id="graph-error" hidden>搜索暂未载入，你仍可点击节点阅读文章。</p><div class="map-footnote"><span>每篇文章都可以独立阅读。</span><a href="paths.html">也可以沿阅读路线探索 ↗</a></div></div><aside class="node-inspector" aria-label="当前文章与关联"><span class="eyebrow">选中的观点</span><h2 id="inspect-title">{e(first['title'])}</h2><p id="inspect-summary">{e(first['summary'])}</p><a class="inspect-read" id="inspect-read" href="cards/{first['id']}.html">阅读这篇文章 ↗</a><div class="inspector-connections"><h3>与它有关</h3><div id="inspect-relations">停留在节点上，查看文章之间的联系。</div></div></aside></div></main>'''
        (out/f'{domain}.html').write_text(base(label+' · 文章关系图',body))
    plan_cards=[c for c in cards if c['domain']=='plans']
    plans='''<header class="page-heading"><span class="eyebrow">PRACTICE / TRAINING PLANS</span><h1>训练计划</h1><p>把想练的内容，写成具体的周计划与阶段安排。</p></header>'''
    if plan_cards:
        plans+=''.join(f'<article class="note-row"><div class="row-meta">{e(" · ".join(c["tags"]))}</div><h2><a href="cards/{c["id"]}.html">{e(c["title"])}</a></h2><p>{e(c["summary"])}</p></article>' for c in plan_cards)
    else:
        plans+='''<div class="plan-empty"><span class="plan-mark" aria-hidden="true">↗</span><h2>第一份计划，正在酝酿。</h2><p>这里将收录网球与健身的具体训练安排。每份计划都可以链接到相关的原子文章，说明练什么，以及为什么这样安排。</p><p class="muted">目前尚未发布训练计划。</p><a href="tennis.html">先从网球知识出发 ↗</a></div>'''
    (out/'plans.html').write_text(layout('训练计划',plans,'plans'))
    profile_body=f'''<header class="page-heading"><span class="eyebrow">ABOUT / THE AUTHOR</span><h1>{e(profile['name'])}</h1><p>场边笔记的整理者。</p></header><article class="prose"><h2>我在这里做什么</h2><p>{e(profile['intro'])}</p><p>{e(profile['note'])}</p><h2>我希望怎样学习</h2><p>把一个观点写清楚，保留来源和适用条件；再把相关的观点连起来，带回训练中继续检验。</p></article><div class="profile-destinations"><a href="tennis.html">探索网球文章 ↗</a><a href="about.html">了解这些笔记的组织方式 ↗</a></div>'''
    (out/'profile.html').write_text(layout('个人简介',profile_body,'profile'))
