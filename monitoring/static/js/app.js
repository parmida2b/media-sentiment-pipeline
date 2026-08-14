(() => {
  const root = document.documentElement;
  const themeBtn = document.getElementById('themeBtn');
  const sun = document.getElementById('themeSun');
  const moon = document.getElementById('themeMoon');

  function applyTheme(theme) {
    root.dataset.theme = theme;
    localStorage.setItem('cc', theme);
    if (sun && moon) {
      sun.classList.toggle('hidden', theme === 'dark');
      moon.classList.toggle('hidden', theme !== 'dark');
    }
    window.dispatchEvent(new CustomEvent('controlcenter:themechange', { detail: { theme } }));
  }

  applyTheme(localStorage.getItem('cc') || 'dark');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => applyTheme(root.dataset.theme === 'dark' ? 'light' : 'dark'));
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-toggle-row]');
    if (!button) return;
    const row = document.getElementById(button.dataset.toggleRow);
    if (row) row.classList.toggle('hidden-row');
  });

  document.querySelectorAll('.confirm-delete').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm('حذف شود؟')) event.preventDefault();
    });
  });
  document.querySelectorAll('.confirm-asset-delete').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm('حذف نماد؟')) event.preventDefault();
    });
  });
})();
