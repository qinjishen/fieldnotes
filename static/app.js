(async () => {
  const search = document.querySelector('#search');
  if (!search) return;
  const normalize = value => value.toLocaleLowerCase().replace(/[\s\p{P}\p{S}]/gu, '');
  const domain = document.querySelector('[data-domain].finder')?.dataset.domain || 'tennis';
  const rows = [...document.querySelectorAll('.note-row')];
  const buttons = [...document.querySelectorAll('[data-topic]')];
  const list = document.querySelector('#notes');
  const context = document.querySelector('#query-context');
  let data;
  try {
    const response = await fetch('search-index.json');
    if (!response.ok) throw new Error('Index unavailable');
    data = await response.json();
  } catch {
    document.querySelector('#search-error').hidden = false;
    return;
  }
  const availableTopics = new Set(data.cards.filter(c=>(domain==='search' || c.domain===domain)).flatMap(c=>c.topics));
  buttons.forEach(b=>{ b.hidden=b.dataset.topic!=='all' && !availableTopics.has(b.dataset.topic); });
  const initial = new URLSearchParams(location.search);
  let topic = availableTopics.has(initial.get('topic')) ? initial.get('topic') : 'all';
  let question = data.questions.find(q => q.id === initial.get('question')) || null;
  search.value = initial.get('q') || '';
  const indexed = new Map(data.cards.map(c => [c.id, { ...c, searchable:normalize([c.title,c.summary,c.body,c.sources,...c.aliases].join(' ')), aliasText:normalize(c.aliases.join(' ')) }]));
  function syncUrl() {
    const params = new URLSearchParams();
    if (search.value.trim()) params.set('q', search.value.trim());
    if (topic !== 'all') params.set('topic', topic);
    if (question) params.set('question', question.id);
    history.replaceState(null, '', location.pathname + (params.size ? '?' + params.toString() : '') + location.hash);
  }
  function update() {
    const query = search.value.trim();
    const words = query.split(/\s+/).map(normalize).filter(Boolean);
    const scored = rows.map((row, position) => {
      const c = indexed.get(row.dataset.id);
      const allowed = (topic === 'all' || c.topics.includes(topic)) && (!question || question.cards.includes(c.id));
      const match = words.every(word => c.searchable.includes(word));
      const score = words.reduce((n,w) => n + (normalize(c.title).includes(w) ? 20 : 0) + (c.aliasText.includes(w) ? 10 : 0), 0);
      return {row,show:allowed && match,score,position};
    });
    scored.sort((a,b) => b.score-a.score || a.position-b.position);
    let count = 0;
    for (const {row,show} of scored) { row.hidden = !show; if (show) count++; list.appendChild(row); }
    buttons.forEach(b => { const selected = b.dataset.topic === topic; b.classList.toggle('selected',selected); b.setAttribute('aria-pressed', String(selected)); });
    document.querySelector('#result-count').textContent = `${count} 篇文章`;
    document.querySelector('#list-title').textContent = question ? '与这个问题有关的文章' : query ? '搜索结果' : topic !== 'all' ? data.topics.find(t=>t.id===topic).label : '全部文章';
    document.querySelector('#empty').hidden = count !== 0;
    context.replaceChildren();
    const captions = [];
    if (question) captions.push(question.label);
    if (query) captions.push(`搜索：${query}`);
    context.hidden = !captions.length;
    if (captions.length) {
      const label = document.createElement('span'); label.textContent = captions.join(' · ');
      const clear = document.createElement('button'); clear.textContent = '清除'; clear.setAttribute('aria-label','清除当前问题和搜索'); clear.addEventListener('click',reset);
      context.append(label,clear);
    }
    syncUrl();
  }
  function reset() { search.value=''; topic='all'; question=null; update(); search.focus(); }
  document.querySelector('#clear').addEventListener('click',reset);
  document.querySelector('#search-form').addEventListener('submit',event=>{event.preventDefault(); question=null; update();});
  search.addEventListener('input',()=>{question=null;update();});
  buttons.forEach(button=>button.addEventListener('click',()=>{topic=button.dataset.topic;update();}));
  document.addEventListener('keydown',event=>{
    if (event.key==='/' && !event.metaKey && !event.ctrlKey && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) {event.preventDefault();search.focus();}
  });
  update();
})();
