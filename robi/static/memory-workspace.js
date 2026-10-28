
(()=>{
 const $=id=>document.getElementById(id);
 let memories=[],page=0,points=[],zoom=1,panX=0,panY=0,drag=null,selected=null;
 const pageSize=8;
 const categoryNames={identity:"Identità",preference:"Preferenze",interaction:"Stile"};
 async function refresh(){
  try{
   const response=await fetch('/api/memories',{cache:'no-store'});
   if(!response.ok)throw Error('Impossibile caricare i ricordi');
   memories=(await response.json()).memories||[];
   render();
  }catch(error){$('memoryError').textContent=error.message;}
 }
 function render(){
  const term=$('memorySearch').value.trim().toLocaleLowerCase();
  const category=$('memoryFilter').value;
  const filtered=memories.filter(m=>(category==='all'||m.category===category)&&
    (m.fact.toLocaleLowerCase().includes(term)||String(m.id).includes(term)));
  const pages=Math.max(1,Math.ceil(filtered.length/pageSize));
  page=Math.max(0,Math.min(page,pages-1));
  $('memorySummary').textContent=filtered.length+' di '+memories.length+' ricordi';
  $('memoryPage').textContent='Pagina '+(page+1)+' / '+pages;
  $('memoryPrev').disabled=page===0;
  $('memoryNext').disabled=page>=pages-1;
  const box=$('memoryItems');box.replaceChildren();
  if(!filtered.length){const empty=document.createElement('p');empty.className='muted';empty.textContent='Nessun ricordo corrispondente.';box.append(empty);}
  filtered.slice(page*pageSize,(page+1)*pageSize).forEach(item=>{
    const card=document.createElement('div');card.className='memory-card';
    const head=document.createElement('div');head.className='memory-card-head';
    const tag=document.createElement('span');tag.textContent=categoryNames[item.category]||item.category;
    const date=document.createElement('small');date.textContent='ID '+item.id+' · '+(item.created_at||'');
    head.append(tag,date);
    const fact=document.createElement('p');fact.textContent=item.fact;
    const buttons=document.createElement('div');buttons.className='buttons';
    const edit=document.createElement('button');edit.textContent='Modifica';
    edit.onclick=async()=>{const updated=prompt('Modifica ricordo:',item.fact);
     if(updated===null||updated.trim()===item.fact)return;
     try{await send('/api/memories/update',{id:item.id,category:item.category,fact:updated});await refresh();await refreshMap();}
     catch(error){$('memoryError').textContent=error.message;}};
    const del=document.createElement('button');del.textContent='Elimina';
    del.onclick=async()=>{if(!confirm('Eliminare questo ricordo?'))return;
     try{await send('/api/memories/delete',{id:item.id});await refresh();await refreshMap();}
     catch(error){$('memoryError').textContent=error.message;}};
    buttons.append(edit,del);card.append(head,fact,buttons);box.append(card);
  });
 }
 $('memorySearch').oninput=()=>{page=0;render()};
 $('memoryFilter').onchange=()=>{page=0;render()};
 $('memoryPrev').onclick=()=>{page--;render()};
 $('memoryNext').onclick=()=>{page++;render()};
 window.refreshMemories=async()=>{await refresh();await refreshMap();};
 const canvas=$('memoryMap'),ctx=canvas.getContext('2d');
 function color(category){return category==='identity'?'#8bbcff':category==='preference'?'#91e5c3':'#ffd58f'}
 function project(p){return [canvas.width/2+panX+p.x*canvas.width*.36*zoom,
                               canvas.height/2+panY+p.y*canvas.height*.36*zoom]}
 function draw(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.fillStyle='#101a29';ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle='#263950';ctx.lineWidth=1;
  for(let i=0;i<canvas.width;i+=40){ctx.beginPath();ctx.moveTo(i,0);ctx.lineTo(i,canvas.height);ctx.stroke()}
  for(let i=0;i<canvas.height;i+=40){ctx.beginPath();ctx.moveTo(0,i);ctx.lineTo(canvas.width,i);ctx.stroke()}
  for(const p of points){const [x,y]=project(p);ctx.beginPath();ctx.arc(x,y,p.id===selected?8:5,0,Math.PI*2);
   ctx.fillStyle=color(p.category);ctx.fill();
   if(p.id===selected){ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke()}}
 }
 async function refreshMap(){
  try{
   const response=await fetch('/api/memory/map',{cache:'no-store'});
   if(!response.ok)throw Error('Mappa non disponibile');
   const result=await response.json();points=result.points||[];
   $('mapStatus').textContent=points.length+' vettori visualizzati su '+result.total+' ricordi · PCA 2D ('+(result.model||'nessun modello')+')';
   if(!points.length)$('mapDetail').textContent='Nessun vettore indicizzato. Fai una domanda a ROBI con embeddinggemma attivo per popolare la mappa.';
   draw();
  }catch(error){$('mapStatus').textContent=error.message;}
 }
 canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.5,Math.min(8,zoom*(e.deltaY>0?.85:1.15)));draw()},{passive:false});
 canvas.addEventListener('pointerdown',e=>{drag={x:e.offsetX,y:e.offsetY,startX:panX,startY:panY};canvas.setPointerCapture(e.pointerId)});
 canvas.addEventListener('pointermove',e=>{if(!drag)return;panX=drag.startX+e.offsetX-drag.x;panY=drag.startY+e.offsetY-drag.y;draw()});
 canvas.addEventListener('pointerup',e=>{
  if(!drag)return;
  if(Math.hypot(e.offsetX-drag.x,e.offsetY-drag.y)<6){
   const x=e.offsetX*canvas.width/canvas.clientWidth,y=e.offsetY*canvas.height/canvas.clientHeight;
   const nearest=points.map(p=>({p,d:Math.hypot(project(p)[0]-x,project(p)[1]-y)})).sort((a,b)=>a.d-b.d)[0];
   if(nearest&&nearest.d<18){selected=nearest.p.id;$('mapDetail').textContent=nearest.p.fact;draw();}
  } drag=null;
 });
 $('mapReset').onclick=()=>{zoom=1;panX=panY=0;draw()};
 $('mapRefresh').onclick=refreshMap;
 $('consolidateMemories').onclick=async()=>{
  const status=$('consolidationStatus'),list=$('consolidationItems'),button=$('consolidateMemories');
  button.disabled=true;list.replaceChildren();status.textContent='Analisi della conversazione...';
  try{
   const result=await send('/api/learning/consolidate');
   status.textContent=(result.proposals||[]).length+' proposte. Nessuna modifica avviene senza conferma.';
   for(const p of result.proposals||[]){
    const card=document.createElement('div');card.className='memory-card';
    const title=document.createElement('b');title.textContent=p.action==='update'?'Aggiorna ricordo #'+p.target_id:p.action==='duplicate'?'Duplicato già presente':'Nuovo ricordo';
    const input=document.createElement('input');input.value=p.candidate.fact;input.maxLength=300;input.className='memory-input';
    const rationale=document.createElement('p');rationale.className='mini muted';rationale.textContent=(p.reason||'')+' · Fonte: '+p.candidate.evidence;
    const confirm=document.createElement('button');confirm.textContent=p.action==='update'?'Conferma modifica':'Conferma salvataggio';
    confirm.disabled=p.action==='duplicate';
    confirm.onclick=async()=>{
     try{if(p.action==='update')await send('/api/memories/update',{id:p.target_id,category:p.candidate.category,fact:input.value});
      else await send('/api/memories',{category:p.candidate.category,fact:input.value});
      card.remove();await window.refreshMemories();}
     catch(error){status.textContent=error.message;}
    };
    const skip=document.createElement('button');skip.textContent='Scarta';skip.onclick=()=>card.remove();
    card.append(title,input,rationale,confirm,skip);list.append(card);
   }
  }catch(error){status.textContent=error.message}finally{button.disabled=false}
 };
 refresh();refreshMap();
})();
