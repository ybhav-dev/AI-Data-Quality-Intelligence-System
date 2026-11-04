const modal = document.getElementById('uploadModal');
const fileInput = document.getElementById('datasetFile');
const selectedFile = document.getElementById('selectedFile');

function openUploadModal() {
  if (modal) modal.hidden = false;
}
function closeUploadModal() {
  if (modal) modal.hidden = true;
}
['uploadTrigger', 'bannerUpload', 'tableUpload'].forEach((id) => {
  const button = document.getElementById(id);
  if (button) button.addEventListener('click', openUploadModal);
});
const closeButton = document.getElementById('closeModal');
if (closeButton) closeButton.addEventListener('click', closeUploadModal);
if (modal) modal.addEventListener('click', (event) => {
  if (event.target === modal) closeUploadModal();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeUploadModal();
});

function setMetric(label, value, suffix = '') {
  const card = [...document.querySelectorAll('.metric-card')].find(el => el.querySelector('.metric-label')?.textContent.trim() === label);
  if (card) card.querySelector('.metric-value').innerHTML = `${value}<span class="metric-unit">${suffix}</span>`;
}
function updateDashboard(data) {
  setMetric('Quality score', data.quality_score, '/100');
  setMetric('Missing values', data.missing_values);
  setMetric('Duplicate rows', data.duplicate_rows);
  setMetric('Potential anomalies', data.anomalies);

  const dimMap = {
    Completeness: 'completeness', Validity: 'validity', Uniqueness: 'uniqueness',
    Consistency: 'consistency', Reliability: 'reliability'
  };
  document.querySelectorAll('.dimension-row').forEach(row => {
    const key = dimMap[row.querySelector('.dimension-name span:last-child')?.textContent.trim()];
    if (!key) return;
    const value = data.dimensions[key];
    row.querySelector('.dimension-track span').style.width = `${value}%`;
    row.querySelector('strong').textContent = `${value}%`;
  });

  const issueTotal = Object.values(data.issue_distribution).reduce((a,b)=>a+b,0);
  const legendCounts = document.querySelectorAll('.legend b');
  const legendKeys = ['missing_values', 'duplicates', 'invalid_data', 'consistency_issues', 'anomalies'];
  legendCounts.forEach((el, i) => {
    el.textContent = data.issue_distribution[legendKeys[i]] ?? 0;
  });

  const donut = document.querySelector('.donut');
  if (donut) {
    const values = [
      data.issue_distribution.missing_values || 0,
      data.issue_distribution.duplicates || 0,
      data.issue_distribution.invalid_data || 0,
      data.issue_distribution.consistency_issues || 0,
      data.issue_distribution.anomalies || 0
    ];
    const colors = ['#9A0002', '#c9a99b', '#d6c0b2', '#bda092', '#eaded5'];
    const total = Math.max(values.reduce((a,b)=>a+b,0), 1);
    let cursor = 0;
    const stops = values.map((value, index) => {
      const start = cursor;
      cursor += value / total * 100;
      return `${colors[index]} ${start}% ${cursor}%`;
    });
    donut.style.background = `conic-gradient(${stops.join(', ')})`;
    donut.querySelector('strong').textContent = issueTotal;
  }
  const note = document.querySelector('.quality-panel .empty-note');
  if (note) note.innerHTML = `<span>i</span> Analyzed ${data.rows.toLocaleString()} rows and ${data.columns} columns.`;
  const issueNote = document.querySelector('.issues-panel .empty-note');
  if (issueNote) issueNote.innerHTML = `<span>i</span> ${issueTotal} issue(s) detected in ${data.filename}.`;
  const tableBody = document.querySelector('.recent-panel tbody');
  if (tableBody) {
    tableBody.innerHTML = `<tr>
      <td style="padding:15px 20px;font-size:11px;font-weight:600">${escapeHtml(data.filename)}</td>
      <td style="padding:15px 20px;font-size:11px">${data.rows.toLocaleString()}</td>
      <td style="padding:15px 20px;font-size:11px">${data.columns}</td>
      <td style="padding:15px 20px;font-size:11px"><strong>${data.quality_score}/100</strong></td>
      <td style="padding:15px 20px"><span style="font-size:10px;color:#537b5d;background:#eaf1e9;padding:5px 8px;border-radius:6px">Analyzed</span></td>
      <td></td></tr>`;
  }
  const banner = document.querySelector('.banner-tag');
  if (banner) banner.textContent = 'DATASET ANALYZED SUCCESSFULLY';
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
if (fileInput) fileInput.addEventListener('change', async () => {
  const file = fileInput.files && fileInput.files[0];
  if (!file) return;
  selectedFile.hidden = false;
  selectedFile.textContent = `Uploading ${file.name}...`;
  const formData = new FormData();
  formData.append('dataset', file);
  try {
    const response = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Upload failed.');
    selectedFile.textContent = `Analyzed: ${file.name}`;
    updateDashboard(data);
    setTimeout(closeUploadModal, 900);
  } catch (error) {
    selectedFile.textContent = error.message;
    selectedFile.style.color = '#9A0002';
  }
});
