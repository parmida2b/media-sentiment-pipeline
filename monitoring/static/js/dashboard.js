(() => {
  const byId = (id) => document.getElementById(id);
  const put = (id, value) => { const el = byId(id); if (el) el.textContent = value ?? 0; };
  const statusText = (p) => p?.running ? 'RUNNING' : String(p?.last_status || 'unknown').toUpperCase();

  function updateProcessCard(name, p) {
    const card = document.querySelector(`[data-process-card="${name}"]`);
    if (!card) return;
    const badge = card.querySelector('[data-process-status]');
    const pid = card.querySelector('[data-process-pid]');
    const exit = card.querySelector('[data-process-exit]');
    if (badge) {
      badge.textContent = statusText(p);
      badge.classList.remove('g','r','n');
      badge.classList.add(p?.running ? 'g' : (p?.last_status === 'failed' ? 'r' : 'n'));
    }
    if (pid) pid.textContent = p?.pid ?? '—';
    if (exit) exit.textContent = p?.exit_code ?? '—';
  }

  async function refreshDashboard() {
    try {
      const res = await fetch('/api/dashboard', {cache: 'no-store'});
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      const c = d.counts || {};
      const r = d.reddit || {};
      const rc = r.counts || {};

      put('dashTotalSocial', c.total_social || 0);
      put('dashRedditParents', rc.parent_unique ?? c.reddit_parent_posts ?? 0);
      put('dashRedditRaw', rc.raw_json_files ?? c.reddit_raw_json_files ?? 0);
      put('dashRedditComments', rc.comments_live ?? c.reddit_live_comments ?? 0);
      put('dashRedditPending', rc.pending_json ?? c.reddit_pending_json ?? 0);
      put('dashYoutube', c.youtube_records || 0);
      put('dashX', c.x_tweets || 0);
      put('dashFinance', c.finance_raw || 0);


      Object.entries(d.processes || {}).forEach(([name, p]) => updateProcessCard(name, p));
    } catch (err) {
      console.warn('Dashboard live refresh failed', err);
    }
  }

  refreshDashboard();
  setInterval(refreshDashboard, 2000);
})();
