// Shared frontend helpers.


// Sidebar help guide: available from every workspace page.
(() => {
  const guideMarkup = `
    <div class="help-guide-backdrop" data-help-close>
      <section class="help-guide-dialog" role="dialog" aria-modal="true" aria-labelledby="helpGuideTitle" tabindex="-1">
        <header class="help-guide-header">
          <div><span class="help-guide-kicker">DATAQUAL QUICK GUIDE</span><h2 id="helpGuideTitle">Make your data reliable.</h2><p>Use this guide to move through your data-quality workflow.</p></div>
          <button class="help-guide-close" type="button" aria-label="Close guide" data-help-close>&times;</button>
        </header>
        <div class="help-guide-content">
          <article class="help-guide-step"><span class="help-guide-number">01</span><div><h3>Upload a dataset</h3><p>Start from <strong>Upload Dataset</strong> or the dashboard button. Choose a CSV or Excel file and let DataQual analyze its structure and quality.</p></div></article>
          <article class="help-guide-step"><span class="help-guide-number">02</span><div><h3>Review data analysis</h3><p>Check the quality score, missing values, duplicates, invalid data, consistency issues and anomalies. Use issue filters to inspect affected records.</p></div></article>
          <article class="help-guide-step"><span class="help-guide-number">03</span><div><h3>Explore columns</h3><p>In the interactive table, select a column header to view its profile and distribution. Search, sort and double-click cells to edit values.</p></div></article>
          <article class="help-guide-step"><span class="help-guide-number">04</span><div><h3>Apply recommendations</h3><p>Review suggested fixes and select only the changes you want. Preview them before applying; uncertain outliers should be reviewed manually.</p></div></article>
          <article class="help-guide-step"><span class="help-guide-number">05</span><div><h3>Clean and export</h3><p>Choose cleaning operations such as handling missing values, trimming whitespace or removing duplicates. Preview first, apply, then export the working CSV. Your original upload stays unchanged.</p></div></article>
          <div class="help-guide-tip"><strong>Tip</strong><span>Use <em>Reset edits</em> to return the table to the original uploaded dataset, or <em>Undo edit</em> to reverse the latest table edit.</span></div>
        </div>
        <footer class="help-guide-footer"><a class="button button-primary" href="/">Go to overview</a><button class="button button-outline" type="button" data-help-close>Close guide</button></footer>
      </section>
    </div>`;

  function openGuide() {
    if (document.querySelector('.help-guide-backdrop')) return;
    document.body.insertAdjacentHTML('beforeend', guideMarkup);
    const backdrop = document.querySelector('.help-guide-backdrop');
    const dialog = backdrop.querySelector('.help-guide-dialog');
    document.body.classList.add('help-guide-open');
    dialog.focus();
    const close = () => {
      backdrop.remove();
      document.body.classList.remove('help-guide-open');
      document.removeEventListener('keydown', onKeyDown);
    };
    const onKeyDown = (event) => { if (event.key === 'Escape') close(); };
    backdrop.addEventListener('click', (event) => {
      if (event.target.closest('[data-help-close]') || event.target === backdrop) close();
    });
    document.addEventListener('keydown', onKeyDown);
  }

  document.addEventListener('click', (event) => {
    const card = event.target.closest('.help-card');
    if (card) { event.preventDefault(); openGuide(); }
  });
  document.addEventListener('keydown', (event) => {
    const card = event.target.closest && event.target.closest('.help-card');
    if (card && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); openGuide(); }
  });
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.help-card').forEach((card) => {
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label', 'Open DataQual quick guide');
      card.style.cursor = 'pointer';
    });
  });
})();
