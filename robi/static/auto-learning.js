(()=>{
 const toggle=document.getElementById('autoLearningToggle');
 const summary=document.getElementById('autoLearningBrief');
 const details=document.getElementById('autoLearningSteps');
 let lastSequence='';
 toggle.addEventListener('change',async()=>{
   toggle.disabled=true;
   try{
     const result=await send('/api/learning/mode',{enabled:toggle.checked});
     toggle.checked=result.enabled;
     details.textContent=result.enabled?'Modalità autonoma attiva. La memoria viene valutata ogni 3 messaggi utente.':'Modalità autonoma disattivata.';
   }catch(error){toggle.checked=!toggle.checked;details.textContent=error.message;}
   finally{toggle.disabled=false;}
 });
 async function refresh(){
   try{
    const response=await fetch('/api/learning/pending',{cache:'no-store'});
    if(!response.ok)return;
    const state=await response.json();
    if(document.activeElement!==toggle)toggle.checked=!!state.enabled;
    const label=state.status==='running'?'Analisi della memoria in corso · '+(state.elapsed_seconds||0)+'s':state.status==='error'?'Memoria AI · Analisi non riuscita':
      state.enabled?'Memoria AI · '+(state.step||'Pronta'):'Memoria AI · Modalità manuale';
    summary.textContent=label;
    if(state.status==='running')details.textContent=(state.step||'ROBI sta analizzando...')+'\nTempo trascorso: '+(state.elapsed_seconds||0)+' secondi';
    else if(state.status==='error')details.textContent='Analisi non completata: '+(state.error||'Ollama non disponibile')+'\nNessun dato è stato salvato da questo ciclo.';
    else{
      const events=state.events||[];
      const signature=JSON.stringify(events);
      if(signature!==lastSequence){
       lastSequence=signature;
       details.textContent=events.length?events.slice(0,8).map(e=>
        (e.outcome==='accepted'?'Salvato':e.outcome==='rejected'?'Ignorato':'Da verificare')
        +' · '+e.fact+'\nFonte: '+e.evidence+'\nMotivo: '+e.reason).join('\n\n')
         :'Nessuna decisione ancora registrata.';
       if(events.some(e=>e.outcome==='accepted')&&typeof window.refreshMemories==='function')
         window.refreshMemories();
      }
    }
   }catch(error){summary.textContent='Memoria AI · Stato non disponibile';}
 }
 setInterval(refresh,3000);
 refresh();
})();
