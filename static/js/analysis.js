(() => {
  const body = document.getElementById('issueTableBody');
  if (!body) return;
  const rows = [...body.querySelectorAll('tr[data-type]')];
  const tabs = [...document.querySelectorAll('.issue-tab')];
  const cards = [...document.querySelectorAll('.analysis-count-card')];
  const search = document.getElementById('issueSearch');
  const countLabel = document.getElementById('visibleIssueCount');
  let activeFilter = 'All';

  function applyFilters() {
    const query = (search?.value || '').trim().toLowerCase();
    let visible = 0;
    rows.forEach(row => {
      const typeMatch = activeFilter === 'All' || row.dataset.type === activeFilter;
      const textMatch = !query || row.textContent.toLowerCase().includes(query);
      const show = typeMatch && textMatch;
      row.hidden = !show;
      if (show) visible++;
    });
    if (countLabel) countLabel.textContent = `${visible} records`;
  }
  function setFilter(filter) {
    activeFilter = filter;
    tabs.forEach(tab => tab.classList.toggle('active', tab.dataset.filter === filter));
    cards.forEach(card => card.classList.toggle('active', card.dataset.filter === filter));
    applyFilters();
  }
  tabs.forEach(tab => tab.addEventListener('click', () => setFilter(tab.dataset.filter)));
  cards.forEach(card => card.addEventListener('click', () => setFilter(card.dataset.filter)));
  if (search) search.addEventListener('input', applyFilters);
  applyFilters();

  // Interactive numeric histograms and categorical frequency charts.
  // Dataset-level numeric correlation heatmap.
  const correlationNode = document.getElementById('correlationData');
  const correlationChart = document.getElementById('correlationHeatmap');
  if (correlationNode && correlationChart && window.Plotly) {
    try {
      const corr = JSON.parse(correlationNode.textContent || '{}');
      if (corr.columns?.length && corr.values?.length) {
        Plotly.newPlot(correlationChart, [{
          z: corr.values, x: corr.columns, y: corr.columns, type: 'heatmap',
          zmin: -1, zmax: 1, zmid: 0,
          colorscale: [[0,'#a40005'],[0.5,'#fbf7f3'],[1,'#6d9b82']],
          colorbar: {title: 'r', thickness: 12},
          hovertemplate: '%{y} × %{x}<br>Correlation: %{z:.3f}<extra></extra>'
        }], {
          paper_bgcolor: 'white', plot_bgcolor: 'white',
          font: {family: 'Inter, Arial, sans-serif', color: '#51443f', size: 11},
          margin: {l: 110, r: 30, t: 18, b: 100},
          xaxis: {tickangle: -35, automargin: true}, yaxis: {autorange: 'reversed', automargin: true}
        }, {responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d','select2d']});
      }
    } catch (_) { correlationChart.textContent = 'Unable to render correlation heatmap.'; }
  }

  const profileNode = document.getElementById('columnProfilesData');
  const profileSelect = document.getElementById('profileColumn');
  const profileChart = document.getElementById('columnProfileChart');
  const profileSummary = document.getElementById('profileSummary');
  if (profileNode && profileSelect && profileChart && window.Plotly) {
    let profiles = [];
    try { profiles = JSON.parse(profileNode.textContent || '[]'); } catch (_) {}
    const renderProfile = () => {
      const profile = profiles[Number(profileSelect.value)];
      if (!profile) return;
      let trace, layout;
      if (profile.kind === 'numeric') {
        trace = [{x: profile.values, type: 'histogram', nbinsx: 24,
          marker: {color: '#a40005'}, hovertemplate: 'Value range: %{x}<br>Count: %{y}<extra></extra>'}];
        layout = {title: {text: `Distribution of ${profile.column}`, font: {size: 14}},
          xaxis: {title: profile.column, gridcolor: '#f1e8e2'},
          yaxis: {title: 'Frequency', gridcolor: '#f1e8e2'},
          bargap: 0.08};
        profileSummary.textContent = `n=${profile.count} · mean ${profile.mean} · median ${profile.median} · range ${profile.min}–${profile.max}`;
      } else {
        trace = [{x: profile.labels, y: profile.values, type: 'bar',
          marker: {color: '#a40005'}, hovertemplate: '%{x}<br>Count: %{y}<extra></extra>'}];
        layout = {title: {text: `Top values in ${profile.column}`, font: {size: 14}},
          xaxis: {title: profile.column, tickangle: -25, automargin: true},
          yaxis: {title: 'Records', gridcolor: '#f1e8e2'}};
        profileSummary.textContent = `${profile.count} non-empty values · ${profile.unique} distinct · showing top ${profile.labels.length}`;
      }
      Object.assign(layout, {paper_bgcolor: 'white', plot_bgcolor: 'white',
        font: {family: 'Inter, Arial, sans-serif', color: '#51443f', size: 11},
        margin: {l: 48, r: 20, t: 42, b: 70}, autosize: true});
      Plotly.react(profileChart, trace, layout, {responsive: true, displaylogo: false,
        modeBarButtonsToRemove: ['lasso2d','select2d']});
    };
    profileSelect.addEventListener('change', renderProfile);
    renderProfile();
  }

  // Custom validation rule builder
  const ruleColumn=document.getElementById('ruleColumn'), ruleType=document.getElementById('ruleType');
  const ruleList=document.getElementById('ruleList'), ruleResults=document.getElementById('ruleResults');
  if(ruleColumn&&ruleType&&ruleList&&ruleResults){
    const rules=[]; const escRule=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const syncFields=()=>{const t=ruleType.value;document.getElementById('ruleValueWrap').hidden=['not_null','unique','email'].includes(t)||t==='min'||t==='max'||t==='between';document.getElementById('ruleMinWrap').hidden=!['min','between'].includes(t);document.getElementById('ruleMaxWrap').hidden=!['max','between'].includes(t);};
    const renderRules=()=>{ruleList.innerHTML=rules.length?rules.map((r,i)=>`<div class="rule-chip"><span><b>${escRule(r.column)}</b> · ${escRule(r.label)}${r.value!==undefined?` · ${escRule(r.value)}`:''}</span><button type="button" data-remove-rule="${i}" aria-label="Remove rule">×</button></div>`).join(''):'<p class="muted">No rules added yet.</p>';};
    ruleType.addEventListener('change',syncFields);syncFields();
    document.getElementById('addRule').addEventListener('click',()=>{
      if(rules.length>=30){alert('Maximum 30 rules.');return;}
      const t=ruleType.value,r={column:ruleColumn.value,type:t,label:ruleType.options[ruleType.selectedIndex].text};
      if(['min','max'].includes(t)){r.value=document.getElementById('ruleValue').value;if(r.value.trim()===''){alert('Enter a numeric value.');return;}}
      if(t==='between'){r.min=document.getElementById('ruleMin').value;r.max=document.getElementById('ruleMax').value;if(r.min===''||r.max===''||Number(r.min)>Number(r.max)){alert('Enter a valid minimum and maximum.');return;}}
      if(t==='regex'){r.value=document.getElementById('ruleValue').value;if(!r.value){alert('Enter a regex pattern.');return;}}
      rules.push(r);renderRules();ruleResults.innerHTML='';
    });
    ruleList.addEventListener('click',e=>{const b=e.target.closest('[data-remove-rule]');if(b){rules.splice(Number(b.dataset.removeRule),1);renderRules();}});
    document.getElementById('runRules').addEventListener('click',async()=>{
      if(!rules.length){alert('Add at least one rule first.');return;}
      const btn=document.getElementById('runRules');btn.disabled=true;btn.textContent='Validating…';
      try{
        const res=await fetch('/analysis/validate-rules',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rules})}),data=await res.json();
        if(!res.ok)throw new Error(data.error||'Validation failed');
        const fails=data.results.reduce((n,r)=>n+(r.failed||0),0);
        ruleResults.innerHTML=`<div class="rule-result-summary"><strong>${data.total_rules} rules checked</strong><span>${fails} rule violations (counts may overlap)</span></div>`+
          data.results.map(r=>`<div class="rule-result ${r.error?'rule-error':r.failed?'rule-fail':'rule-pass'}"><div><b>${escRule(r.column)} · ${escRule(r.type)}</b><span>${r.error?escRule(r.error):`${r.failed} violations`}</span></div>${r.examples?.length?`<small>${r.examples.map(x=>`Row ${x.row}: ${escRule(x.value)}`).join(' · ')}</small>`:''}</div>`).join('');
      }catch(e){ruleResults.innerHTML=`<p class="rule-error">${escRule(e.message)}</p>`;}finally{btn.disabled=false;btn.textContent='Run validation';}
    });
  }
})();
