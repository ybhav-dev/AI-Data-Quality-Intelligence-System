(() => {
 const form=document.getElementById('cleaningForm'), btn=document.getElementById('previewCleaning'), panel=document.getElementById('cleaningPreview');
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 if(form&&btn&&panel){
  btn.addEventListener('click',async()=>{
   if(!form.querySelector('input[name="operations"]:checked')){alert('Select at least one cleaning operation.');return;}
   btn.disabled=true;btn.textContent='Preparing preview…';
   try{
    const res=await fetch('/cleaning/preview',{method:'POST',body:new FormData(form)}),data=await res.json();
    if(!res.ok)throw new Error(data.error||'Could not create preview.');
    [['cbRows',data.rows_before],['caRows',data.rows_after],['cbMissing',data.missing_before],['caMissing',data.missing_after],['cbDup',data.duplicates_before],['caDup',data.duplicates_after]].forEach(([id,val])=>document.getElementById(id).textContent=val);
    document.getElementById('previewOps').textContent=`${(data.selected||[]).length} selected`;
    const cols=data.columns||[],rows=data.preview||[];
    document.getElementById('cleaningPreviewTable').innerHTML=`<thead><tr>${cols.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${esc(r[c])}</td>`).join('')}</tr>`).join('')}</tbody>`;
    panel.hidden=false;panel.scrollIntoView({behavior:'smooth',block:'start'});
   }catch(e){alert(e.message)}finally{btn.disabled=false;btn.textContent='Preview changes'}
  });
 }
 const table=document.getElementById('interactiveDataTable');
 if(!table)return;
 const search=document.getElementById('tableSearch'),sortCol=document.getElementById('tableSortColumn'),sortDir=document.getElementById('tableSortDirection');
 const pageInfo=document.getElementById('tablePageInfo'),profile=document.getElementById('columnProfile');
 const chartSelect=document.getElementById('columnChartSelect');
 let page=1,pages=1,columns=[],timer=null,activeProfile=''; const selectedRows=new Set();
 async function load(){
  const params=new URLSearchParams({page,q:search.value,sort:sortCol.value,direction:sortDir.value,page_size:25});
  const res=await fetch('/cleaning/table?'+params),data=await res.json();
  if(!res.ok){pageInfo.textContent=data.error||'Could not load data';return;}
  columns=data.columns||[];pages=data.pages||1;
  if(chartSelect){const current=chartSelect.value;chartSelect.innerHTML='<option value="">Choose a column…</option>'+columns.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');if(current&&columns.includes(current))chartSelect.value=current;}
  document.getElementById('tableCount').textContent=`${data.total} records`;
  pageInfo.textContent=`Page ${page} of ${pages} · ${data.total} matching rows`;
  document.getElementById('tablePrev').disabled=page<=1;document.getElementById('tableNext').disabled=page>=pages;
  table.innerHTML=`<thead><tr><th class="select-col">✓</th><th>#</th>${columns.map(c=>`<th data-column="${esc(c)}" title="Click to profile">${esc(c)} <span class="sort-mark">↕</span></th>`).join('')}</tr></thead><tbody>${(data.rows||[]).map(r=>`<tr><td><input type="checkbox" class="row-select" data-row="${r._row_index}" ${selectedRows.has(Number(r._row_index))?'checked':''} aria-label="Select row ${Number(r._row_index)+1}"></td><td class="row-index">${Number(r._row_index)+1}</td>${columns.map(c=>`<td class="editable-cell" data-row="${r._row_index}" data-column="${esc(c)}" title="Double-click to edit">${esc(r[c])}</td>`).join('')}</tr>`).join('')}</tbody>`;
  updateSelectionUI();
 }
 function updateSelectionUI(){
  document.getElementById('selectedRowsCount').textContent=`${selectedRows.size} rows selected`;
  const boxes=[...table.querySelectorAll('.row-select')];
  const pageBox=document.getElementById('selectPageRows');
  if(pageBox){pageBox.checked=boxes.length>0&&boxes.every(b=>b.checked);pageBox.indeterminate=boxes.some(b=>b.checked)&&!pageBox.checked;}
 }
 function drawColumnChart(d){
  const area=document.getElementById('columnChartArea'); if(!area)return;
  const histogram=d.histogram||[];
  const entries=histogram.length?histogram:Object.entries(d.top_values||{}).slice(0,8).map(([label,count])=>({label,count}));
  if(!entries.length){area.innerHTML='<span>No values available to chart.</span>';return;}
  const max=Math.max(1,...entries.map(x=>Number(x.count)||0));
  const title=histogram.length?'Numeric distribution (histogram)':'Top categorical values';
  area.innerHTML=`<div class="column-chart-title">${esc(d.column)} · ${title}</div><div class="column-bars">${entries.map(item=>{const label=item.label??'';const count=item.count??0;return `<div class="column-bar-row"><span class="column-bar-label" title="${esc(label)}">${esc(label||'(blank)')}</span><div class="column-bar-track"><i style="width:${Math.max(2,(Number(count)/max)*100)}%"></i></div><b>${count}</b></div>`}).join('')}</div>`;
 }
 async function showProfile(col){
  if(!col)return; activeProfile=col;if(chartSelect)chartSelect.value=col;
  const res=await fetch('/cleaning/profile/'+encodeURIComponent(col)),d=await res.json();
  if(!res.ok){profile.textContent=d.error||'Profile unavailable';return;}
  const fmt=v=>v===null||v===undefined?'—':Number(v).toLocaleString(undefined,{maximumFractionDigits:2});
  let stats=d.stats?`<span>Min <b>${fmt(d.stats.min)}</b></span><span>Median <b>${fmt(d.stats.median)}</b></span><span>Mean <b>${fmt(d.stats.mean)}</b></span><span>Max <b>${fmt(d.stats.max)}</b></span>`:'';
  const top=Object.entries(d.top_values||{}).slice(0,5).map(([v,n])=>`${esc(v)} (${n})`).join(' · ')||'No values';
  drawColumnChart(d);
  profile.innerHTML=`<div class="profile-title"><strong>${esc(d.column)}</strong><span>${esc(d.dtype)}</span></div><div class="profile-metrics"><span>Rows <b>${d.total}</b></span><span>Missing <b>${d.missing}</b></span><span>Unique <b>${d.unique}</b></span>${stats}</div><div class="profile-top"><small>Most common values</small><p>${top}</p></div>`;
 }
 table.addEventListener('click',e=>{const th=e.target.closest('th[data-column]');if(th)showProfile(th.dataset.column)});
 if(chartSelect)chartSelect.addEventListener('change',()=>showProfile(chartSelect.value));
 table.addEventListener('dblclick',async e=>{
  const td=e.target.closest('td.editable-cell');if(!td)return;
  const old=td.textContent, row=Number(td.dataset.row),column=td.dataset.column;
  const value=prompt(`Edit ${column} · row ${row+1}`,old);if(value===null||value===old)return;
  td.classList.add('cell-saving');
  try{const res=await fetch('/cleaning/edit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row,column,value})}),d=await res.json();if(!res.ok)throw new Error(d.error||'Edit failed');await load();showProfile(column);}
  catch(err){alert(err.message);td.textContent=old;}finally{td.classList.remove('cell-saving')}
 });
 table.addEventListener('change',e=>{const box=e.target.closest('.row-select');if(box){const id=Number(box.dataset.row);box.checked?selectedRows.add(id):selectedRows.delete(id);updateSelectionUI();}});
 const pageSelect=document.getElementById('selectPageRows');
 pageSelect.addEventListener('change',()=>{table.querySelectorAll('.row-select').forEach(b=>{const id=Number(b.dataset.row);b.checked=pageSelect.checked;pageSelect.checked?selectedRows.add(id):selectedRows.delete(id)});updateSelectionUI();});
 document.getElementById('exportSelectedRows').addEventListener('click',async()=>{
  if(!selectedRows.size){alert('Select at least one row.');return;}
  try{const res=await fetch('/cleaning/export-selected',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows:[...selectedRows]})});
   if(!res.ok){const d=await res.json();throw new Error(d.error||'Export failed');}
   const blob=await res.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='dataqual_selected_rows.csv';a.click();URL.revokeObjectURL(url);
  }catch(e){alert(e.message)}
 });
 search.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>{page=1;load()},250)});
 [sortCol,sortDir].forEach(el=>el.addEventListener('change',()=>{page=1;load()}));
 document.getElementById('tablePrev').addEventListener('click',()=>{if(page>1){page--;load()}});
 document.getElementById('tableNext').addEventListener('click',()=>{if(page<pages){page++;load()}});
 document.getElementById('undoCellEdit').addEventListener('click',async()=>{const res=await fetch('/cleaning/undo',{method:'POST'}),d=await res.json();if(!res.ok){alert(d.error||'Nothing to undo');return}load()});
 document.getElementById('resetTableEdits').addEventListener('click',async()=>{if(!confirm('Discard all cell edits and return to the original upload?'))return;const res=await fetch('/cleaning/reset',{method:'POST'}),d=await res.json();if(!res.ok){alert(d.error||'Reset failed');return}page=1;load()});
 load().then(()=>{if(columns.length)showProfile(columns[0]);});
})();