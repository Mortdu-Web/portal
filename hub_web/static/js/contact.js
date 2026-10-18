// Formulaire de contact : envoi en JSON vers /contact/send.
(() => {
  const form = document.getElementById('contact-form');
  if (!form) return;
  const btn = document.getElementById('submit-btn');
  const status = document.getElementById('form-status');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    btn.disabled = true;
    btn.textContent = 'Envoi en cours…';
    status.textContent = '';
    status.className = '';

    try {
      const res = await fetch(form.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(new FormData(form))),
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);
      status.className = 'is-ok';
      status.textContent = '✅ Message envoyé ! Je vous répondrai sous 48h.';
      form.reset();
    } catch (err) {
      status.className = 'is-error';
      status.textContent = `❌ ${err.message || 'Une erreur est survenue.'} Vous pouvez aussi m'écrire directement à dr05@orange.fr.`;
    } finally {
      btn.disabled = false;
      btn.textContent = 'Envoyer le message';
    }
  });
})();
