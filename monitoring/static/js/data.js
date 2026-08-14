(function(){
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const link = (u,label) => u ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(label||u)}</a>` : '—';
  const setText = (id, value) => { const el=document.getElementById(id); if(el) el.textContent=value ?? 0; };
  const stamp = (v) => v ? new Date(v).toLocaleTimeString() : 'live';
  function rowsOrEmpty(rows, cols, render, emptyText='هنوز داده‌ای ثبت نشده است.'){
    return rows && rows.length ? rows.map(render).join('') : `<tr><td colspan="${cols}" class="empty-cell">${esc(emptyText)}</td></tr>`;
  }
  async function getJSON(url){
    const r=await fetch(url,{cache:'no-store'});
    if(!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return r.json();
  }

  async function loadReddit(){
    const d=await getJSON('/api/data/reddit/live?limit=40'); const s=d.stats||{};
    setText('kRedditParents',s.parent_unique ?? 0);
    setText('kRedditRaw',s.raw_json_files ?? 0);
    setText('kRedditComments',s.comments_live_raw_json ?? 0);
    setText('kRedditPending',s.pending_json ?? '—');
    setText('redditGeneratedAt',stamp(d.generated_at_utc));
    setText('redditFetchSummary',`${s.fetch_log_rows||0} fetch events`);
    document.getElementById('redditParentBody').innerHTML=rowsOrEmpty(d.parents,6,x=>`<tr><td><b>${esc(x.post_id||x.platform_content_id)}</b></td><td>${esc(x.subreddit)}</td><td>${esc(x.created_at_utc)}</td><td class="txt" title="${esc(x.title)}">${esc(x.title)}</td><td>${link(x.url,'post')}</td><td>${link(x.json_url,'.json')}</td></tr>`);
    document.getElementById('redditFetchBody').innerHTML=rowsOrEmpty(d.fetches,6,x=>`<tr><td><span class="bdg ${String(x.status||'').includes('saved')?'g':String(x.status||'').includes('skip')?'n':'o'}">${esc(x.status)}</span></td><td>${esc(x.post_id)}</td><td>${esc(x.http_status||'—')}</td><td>${esc(x.finished_at_utc)}</td><td>${link(x.json_url,'.json')}</td><td class="txt" title="${esc(x.raw_json_file)}">${esc(x.raw_json_file||'—')}</td></tr>`);
    document.getElementById('redditCommentBody').innerHTML=rowsOrEmpty(d.comments,6,x=>`<tr><td><b>${esc(x.comment_id)}</b></td><td>${esc(x.post_id)}</td><td>${esc(x.subreddit)}</td><td>${esc(x.comment_created_at_utc)}</td><td>${esc(x.depth)}</td><td class="comment-cell">${esc(x.comment)}</td></tr>`);
  }

  async function loadYouTube(){
    const d=await getJSON('/api/data/youtube/live?limit=40');
    setText('kYoutubeRecords',d.total_records ?? 0);
    setText('youtubeGeneratedAt',stamp(d.generated_at_utc));
    document.getElementById('youtubeBody').innerHTML=rowsOrEmpty(d.rows,7,x=>`<tr><td><b>${esc(x.content_id)}</b></td><td><span class="bdg n">${esc(x.content_type)}</span></td><td>${esc(x.created_at_utc)}</td><td class="txt" title="${esc(x.video_title)}">${esc(x.video_id||'—')}</td><td>${esc(x.query_id||'—')}</td><td>${esc(x.source_container||'—')}</td><td class="comment-cell">${esc(x.text)}</td></tr>`, d.source_exists ? 'هنوز رکورد YouTube ذخیره نشده است.' : 'فایل native YouTube هنوز ساخته نشده است.');
  }

  async function loadX(){
    const d=await getJSON('/api/data/x/live?limit=40');
    setText('kXTweets',d.total_records ?? 0);
    setText('kXMatches',d.total_matches ?? 0);
    setText('xGeneratedAt',d.error ? 'read error' : stamp(d.generated_at_utc));
    const empty=d.error ? `خواندن SQLite با خطا مواجه شد: ${d.error}` : (d.source_exists ? 'هنوز Tweet ذخیره نشده است.' : 'دیتابیس native X هنوز ساخته نشده است.');
    document.getElementById('xBody').innerHTML=rowsOrEmpty(d.rows,8,x=>`<tr><td><b>${esc(x.content_id)}</b></td><td>${esc(x.created_at_utc)}</td><td>${esc(x.query_id||'—')}</td><td>${esc(x.project_week||'—')}</td><td>${esc(x.source_container||'—')}</td><td>${esc(x.country_or_region||'—')}</td><td class="comment-cell">${esc(x.text)}</td><td>${link(x.tweet_url,'tweet')}</td></tr>`, empty);
  }

  async function refresh(){
    const jobs=[loadReddit(),loadYouTube(),loadX()];
    const results=await Promise.allSettled(jobs);
    results.forEach((r,i)=>{ if(r.status==='rejected') console.warn(['Reddit','YouTube','X'][i]+' live data refresh failed',r.reason); });
  }
  refresh(); setInterval(refresh,2000);
})();
