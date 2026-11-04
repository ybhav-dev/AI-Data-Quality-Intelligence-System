(() => {
  const form = document.getElementById('recommendationForm');
  const previewButton = document.getElementById('previewFixes');
  const panel = document.getElementById('previewPanel');
  if (!form || !previewButton || !panel) return;
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  previewButton.addEventListener('click', async () => {
    const selected = [...form.querySelectorAll('input[name="recommendations"]:checked')];
    if (!selected.length) { alert('Select at least one recommendation to preview.'); return; }
    previewButton.disabled = true; previewButton.textContent = 'Preparing preview…';
    try {
      const response = await fetch('/recommendations/preview', {method:'POST', body:new FormData(form)});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Preview failed.');
      document.getElementById('previewSelection').textContent = `${data.selected_count} selected`;
      document.getElementById('rowsBefore').textContent = data.before_rows;
      document.getElementById('rowsAfter').textContent = data.after_rows;
      document.getElementById('missingBefore').textContent = data.before_missing;
      document.getElementById('missingAfter').textContent = data.after_missing;
      const table = document.getElementById('previewTable');
      const cols = data.columns || [];
      const rows = data.preview || [];
      table.innerHTML = `<thead><tr>${cols.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${cols.map(c=>`<td>${esc(row[c])}</td>`).join('')}</tr>`).join('')}</tbody>`;
      panel.hidden = false; panel.scrollIntoView({behavior:'smooth',block:'start'});
    } catch (error) { alert(error.message); }
    finally { previewButton.disabled = false; previewButton.textContent = 'Preview selected fixes'; }
  });
})();
