(() => {
  const box = document.getElementById('logbox');
  if (!box) return;
  const name = box.dataset.collector;

  async function poll() {
    try {
      const response = await fetch(`/api/logs/${encodeURIComponent(name)}?lines=2000`, {cache: 'no-store'});
      const payload = await response.json();
      box.textContent = payload.text ?? payload.error ?? 'No log yet.';
      box.scrollTop = box.scrollHeight;
    } catch (error) {
      box.textContent = `Log polling error: ${error}`;
    }
  }

  poll();
  window.setInterval(poll, 2500);
})();
