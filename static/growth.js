/* A note is always a real link. The graph progressively enhances those links. */
(async () => {
  const field = document.querySelector('#growth-field');
  if (!field || !window.d3) return;
  let data;
  try {
    const response = await fetch('growth-graph.json');
    if (!response.ok) return;
    data = await response.json();
  } catch { return; }
  const anchors = [...field.querySelectorAll('[data-growth-id]')];
  const byId = new Map(data.nodes.map(n => [n.id, n]));
  const nodes = anchors.map((el, i) => ({...byId.get(el.dataset.growthId), el, order: i}));
  const lookup = new Map(nodes.map(n => [n.id, n]));
  const links = data.edges.map(e => ({...e, source: e.a, target: e.b}));
  const svg = d3.select(field.querySelector('svg'));
  const lines = svg.selectAll('line').data(links).join('line');
  const tooltip = document.querySelector('#growth-tooltip');
  const button = document.querySelector('#growth-motion');
  const narrow = matchMedia('(max-width: 900px)');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const storageKey = 'fieldnotes-growth-v1';
  let saved = {}, paused = false;
  try { saved = JSON.parse(sessionStorage.getItem(storageKey) || '{}'); paused = !!saved.paused; } catch {}
  let width = 0, height = 0, selected = null, dragging = null, hover = null;
  let simulation, frame = 0, phase = 0, previous = 0, suppressed = null;
  const stages = ['foundation','application','progress'];
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  const offsets = [0.16,0.76,0.35,0.9,0.08,0.64];
  const quiet = () => paused || reduced.matches || narrow.matches || document.hidden;
  function bound(n) {
    n.x = clamp(n.x, n.minX, n.maxX);
    n.y = clamp(n.y, 136, height - 52);
  }
  function avoidLabels() {
    for (let i=0;i<nodes.length;i++) for (let j=i+1;j<nodes.length;j++) {
      const a=nodes[i], b=nodes[j], dx=b.x-a.x, dy=b.y-a.y;
      if (Math.abs(dx)<221 && Math.abs(dy)<64) {
        const push=(64-Math.abs(dy))*.28*(dy<0?-1:1);
        if (a.fy==null) a.vy-=push;
        if (b.fy==null) b.vy+=push;
      }
    }
  }
  function paint() {
    if (narrow.matches) return;
    nodes.forEach(n => {
      bound(n);
      const close = hover && Math.hypot(n.x-hover.x,n.y-hover.y)<135;
      const still = quiet() || selected===n.id || close || dragging;
      const desired = still ? 0 : Math.sin(phase*.55+n.order*1.7)*3;
      // Freeze at the current offset near the pointer, without a jump.
      if (!still) n.drift = desired;
      else if (quiet()) n.drift = 0;
      n.displayY=n.y+(n.drift||0);
      n.el.style.left=n.x+'px'; n.el.style.top=n.displayY+'px';
    });
    lines.attr('x1',d=>d.source.x).attr('y1',d=>d.source.displayY)
      .attr('x2',d=>d.target.x).attr('y2',d=>d.target.displayY);
    if (selected && !dragging) positionTip(lookup.get(selected));
  }
  function animate(time) {
    frame=0;
    if (quiet()) return;
    if (previous) phase+=Math.min((time-previous)/1000,.05);
    previous=time; paint(); frame=requestAnimationFrame(animate);
  }
  function motion() {
    button.hidden=narrow.matches;
    button.disabled=reduced.matches;
    button.setAttribute('aria-pressed',String(paused||reduced.matches));
    button.textContent=reduced.matches?'动态已减少':paused?'开启动态':'暂停动态';
    if (frame) cancelAnimationFrame(frame); frame=0; previous=0;
    if (!quiet()) frame=requestAnimationFrame(animate);
    paint();
  }
  function positionTip(n) {
    if (!n || tooltip.hidden) return;
    const r=n.el.getBoundingClientRect(), box=tooltip.getBoundingClientRect();
    tooltip.style.left=clamp(r.left,16,innerWidth-box.width-16)+'px';
    const below=r.bottom+12;
    tooltip.style.top=(below+box.height<innerHeight-16?below:Math.max(16,r.top-box.height-12))+'px';
  }
  function select(id) {
    if (narrow.matches || dragging) return;
    selected=id;
    const connected=new Set([id]);
    links.forEach(e=>{if(e.a===id)connected.add(e.b);if(e.b===id)connected.add(e.a);});
    field.classList.toggle('has-selection',!!id);
    nodes.forEach(n=>{
      n.el.classList.toggle('is-selected',n.id===id);
      n.el.classList.toggle('is-related',connected.has(n.id));
      if(n.id===id)n.el.setAttribute('aria-describedby','growth-tooltip');
      else n.el.removeAttribute('aria-describedby');
    });
    lines.classed('is-active',d=>d.a===id||d.b===id);
    tooltip.hidden=!id;
    if(id){const n=lookup.get(id);tooltip.querySelector('strong').textContent=n.title;tooltip.querySelector('p').textContent=n.summary;positionTip(n);}
  }
  function save() {
    const points={};nodes.forEach(n=>{if(Number.isFinite(n.x))points[n.id]={x:n.x/width,y:n.y/height};});
    try{sessionStorage.setItem(storageKey,JSON.stringify({paused,points,scrollY:window.scrollY}));}catch{}
  }
  function layout(restore=false) {
    simulation?.stop();
    select(null);
    field.classList.toggle('is-enhanced',!narrow.matches);
    if(narrow.matches){field.style.height='';anchors.forEach(el=>{el.style.left='';el.style.top='';});motion();return;}
    width=field.clientWidth;
    const counts=stages.map(s=>nodes.filter(n=>n.stage===s).length);
    height=Math.max(580,Math.min(innerHeight-210,760),Math.max(...counts)*78+160);
    field.style.height=height+'px';svg.attr('viewBox',`0 0 ${width} ${height}`);
    const laneWidth=width/3;
    stages.forEach((stage, index)=>{
      const group=nodes.filter(n=>n.stage===stage);
      group.forEach((n,i)=>{
        n.minX=index*laneWidth+20;n.maxX=(index+1)*laneWidth-216;
        n.tx=n.minX+Math.max(0,n.maxX-n.minX)*offsets[i%offsets.length];
        n.ty=group.length===1?height*.48:155+(height-225)*(i+.45)/(group.length+.1);
        const point=restore?saved.points?.[n.id]:null;
        n.x=point?point.x*width:n.tx;n.y=point?point.y*height:n.ty;
        n.vx=0;n.vy=0; n.fx=null;n.fy=null;bound(n);
      });
    });
    simulation=d3.forceSimulation(nodes).force('x',d3.forceX(n=>n.tx).strength(.075))
      .force('y',d3.forceY(n=>n.ty).strength(.065))
      .force('link',d3.forceLink(links).id(n=>n.id).strength(.004).distance(190))
      .force('charge',d3.forceManyBody().strength(-12))
      .force('labels',avoidLabels).velocityDecay(.5).stop();
    if(!restore || !saved.points)for(let i=0;i<90;i++){simulation.tick();nodes.forEach(bound);}
    simulation.on('tick',paint).on('end',save);
    paint();motion();
  }
  nodes.forEach(n=>{
    const el=n.el;
    el.addEventListener('pointerenter',event=>{if(event.pointerType!=='touch')select(n.id);});
    el.addEventListener('pointerleave',()=>{if(document.activeElement!==el&&!dragging)select(null);});
    el.addEventListener('focus',()=>select(n.id));
    el.addEventListener('blur',()=>{if(!dragging)select(null);});
    el.addEventListener('keydown',event=>{if(event.key==='Escape'){select(null);}});
    let press=null;
    el.addEventListener('pointerdown',event=>{
      if(narrow.matches||event.button!==0||event.pointerType==='touch')return;
      press={x:event.clientX,y:event.clientY,ox:n.x,oy:n.y,pointer:event.pointerId};
      el.setPointerCapture(event.pointerId);
    });
    el.addEventListener('pointermove',event=>{
      if(!press)return;
      const dx=event.clientX-press.x,dy=event.clientY-press.y;
      if(!dragging&&Math.hypot(dx,dy)<6)return;
      if(!dragging){select(null);dragging=n;el.setPointerCapture(event.pointerId);el.classList.add('is-dragging');simulation.stop();}
      n.x=press.ox+dx;n.y=press.oy+dy;bound(n);n.fx=n.x;n.fy=n.y;paint();
    });
    function release(event){
      if(!press)return;
      if(dragging===n){
        suppressed={id:n.id,until:performance.now()+350};
        n.fx=null;n.fy=null;dragging=null;el.classList.remove('is-dragging');
        if(el.hasPointerCapture(press.pointer))el.releasePointerCapture(press.pointer);
        if(reduced.matches||paused){simulation.alpha(.15);for(let i=0;i<75;i++)simulation.tick();paint();save();}
        else simulation.alpha(.3).restart();
      }
      press=null;
    }
    el.addEventListener('pointerup',release);el.addEventListener('pointercancel',release);
    el.addEventListener('lostpointercapture',release);
    el.addEventListener('dragstart',event=>event.preventDefault());
    el.addEventListener('click',event=>{
      if(suppressed?.id===n.id&&performance.now()<suppressed.until){event.preventDefault();suppressed=null;return;}
      save();
    });
  });
  field.addEventListener('pointermove',event=>{const r=field.getBoundingClientRect();hover={x:event.clientX-r.left,y:event.clientY-r.top};});
  field.addEventListener('pointerleave',()=>{hover=null;if(!field.contains(document.activeElement))select(null);});
  button.addEventListener('click',()=>{paused=!paused;if(paused)simulation?.stop();motion();save();});
  reduced.addEventListener('change',()=>{if(reduced.matches)simulation?.stop();motion();});
  document.addEventListener('visibilitychange',motion);
  addEventListener('pagehide',()=>{save();simulation?.stop();if(frame)cancelAnimationFrame(frame);frame=0;});
  addEventListener('pageshow',()=>{motion();});
  addEventListener('scroll',()=>{if(selected)positionTip(lookup.get(selected));},{passive:true});
  let resizeTimer;
  new ResizeObserver(()=>{if(Math.abs(field.clientWidth-width)>1){clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>layout(),100);}}).observe(field);
  narrow.addEventListener('change',()=>layout());
  layout(true);
  // Browser back and the explicit homepage link both retain the browsing position.
  if(saved.scrollY)requestAnimationFrame(()=>scrollTo({top:saved.scrollY,behavior:'instant'}));
})();
