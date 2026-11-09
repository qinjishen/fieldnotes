(() => {
  const toggle=document.querySelector('#motion-toggle');
  if(toggle){
    const reduced=matchMedia('(prefers-reduced-motion: reduce)');
    let paused=false;
    function apply(){document.querySelector('.orbit-cluster').classList.toggle('motion-paused',paused||reduced.matches);toggle.setAttribute('aria-pressed',String(paused||reduced.matches));toggle.textContent=reduced.matches?'已减少动态':paused?'开启浮动':'暂停浮动';toggle.disabled=reduced.matches;}
    toggle.addEventListener('click',()=>{paused=!paused;apply();});reduced.addEventListener('change',apply);apply();
  }
})();
(async()=>{
  const root=document.querySelector('[data-graph-domain]');if(!root)return;
  let data;
  try{const response=await fetch(root.dataset.graphDomain+'-graph.json');if(!response.ok)throw Error();data=await response.json();}
  catch{document.querySelector('#graph-error').hidden=false;return;}
  const nodes=[...document.querySelectorAll('[data-node]')], lines=[...document.querySelectorAll('.graph-lines line')], rows=[...document.querySelectorAll('[data-list-node]')];
  const search=document.querySelector('#graph-search');const byId=new Map(data.nodes.map(n=>[n.id,n]));
  const normalize=s=>s.toLocaleLowerCase().replace(/[\s\p{P}\p{S}]/gu,'');
  const initial=new URLSearchParams(location.search);
  let selected=nodes[0]?.dataset.node, listView=initial.get('view')==='list';
  let question=data.questions.find(q=>q.id===initial.get('question'));
  let topic=data.topics.find(t=>t.id===initial.get('topic')); 
  search.value=initial.get('q')||'';
  function select(id){
    const n=byId.get(id);if(!n)return;selected=id;
    const connected=new Set([id]);
    data.edges.forEach(e=>{if(e.a===id)connected.add(e.b);if(e.b===id)connected.add(e.a);});
    nodes.forEach(el=>{el.classList.toggle('is-selected',el.dataset.node===id);el.classList.toggle('is-connected',connected.has(el.dataset.node));});
    lines.forEach(el=>el.classList.toggle('is-active',el.dataset.a===id||el.dataset.b===id));
    document.querySelector('#inspect-title').textContent=n.title;document.querySelector('#inspect-summary').textContent=n.summary;
    document.querySelector('#inspect-read').href='cards/'+id+'.html';
    const area=document.querySelector('#inspect-relations');area.replaceChildren();
    for(const r of data.related[id]||[]){const a=document.createElement('a');a.href='cards/'+r.id+'.html';const kind=document.createElement('small');kind.textContent=r.type;const title=document.createElement('strong');title.textContent=r.title;const reason=document.createElement('span');reason.textContent=r.reason;a.append(kind,title,reason);area.append(a);}
    if(!area.children.length)area.textContent='这篇文章目前还没有明确的关联。';
  }
  function sync(){const p=new URLSearchParams();if(search.value.trim())p.set('q',search.value.trim());if(question)p.set('question',question.id);if(topic)p.set('topic',topic.id);if(listView)p.set('view','list');history.replaceState(null,'',location.pathname+(p.size?'?'+p:'')+location.hash);}
  function filter(){
    const words=search.value.split(/\s+/).map(normalize).filter(Boolean);
    const ids=new Set(data.nodes.filter(n=>(!question||question.cards.includes(n.id))&&(!topic||n.topics.includes(topic.id))&&words.every(w=>normalize([n.title,n.summary,n.body,...n.aliases,...n.tags].join(' ')).includes(w))).map(n=>n.id));
    nodes.forEach(el=>el.hidden=!ids.has(el.dataset.node));rows.forEach(el=>el.hidden=!ids.has(el.dataset.listNode));
    let edges=0;lines.forEach(el=>{const visible=ids.has(el.dataset.a)&&ids.has(el.dataset.b);el.style.display=visible?'':'none';if(visible)edges++;});
    document.querySelector('#graph-count').textContent=`${ids.size} 篇文章 · ${edges} 处连接`;
    const scope=document.querySelector('#graph-scope');scope.hidden=!question&&!topic;scope.querySelector('span').textContent=[question?.label,topic?.label].filter(Boolean).join(' · ');
    document.querySelector('#graph-empty').hidden=ids.size>0;
    document.querySelector('.node-inspector').hidden=ids.size===0;
    if(!ids.has(selected)&&ids.size)select([...ids][0]);sync();
  }
  function setView(value){listView=value;document.querySelector('#map-visual').hidden=value;document.querySelector('#map-list').hidden=!value;document.querySelector('#view-list').setAttribute('aria-pressed',String(value));document.querySelector('#view-graph').setAttribute('aria-pressed',String(!value));sync();}
  nodes.forEach(el=>{el.addEventListener('mouseenter',()=>select(el.dataset.node));el.addEventListener('focus',()=>select(el.dataset.node));});
  document.querySelector('#graph-search-form').addEventListener('submit',event=>{event.preventDefault();question=null;filter();});
  search.addEventListener('input',()=>{question=null;filter();});
  document.querySelector('#graph-clear').addEventListener('click',()=>{search.value='';question=null;topic=null;filter();search.focus();});
  document.querySelector('#graph-scope-clear').addEventListener('click',()=>{question=null;topic=null;filter();});
  document.querySelector('#view-list').addEventListener('click',()=>setView(true));document.querySelector('#view-graph').addEventListener('click',()=>setView(false));
  select(selected);filter();setView(listView);
})();
