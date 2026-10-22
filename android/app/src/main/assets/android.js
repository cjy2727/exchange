// Android-only transport. The desktop UI keeps its existing HTTP behavior.
(() => {
  const pending = new Map();
  let nextId = 0;
  window.exchangeReply = (id, data, error) => {
    const request = pending.get(id);
    if (!request) return;
    clearTimeout(request.timer); pending.delete(id);
    if (error) request.reject(new Error(error)); else request.resolve(data);
  };
  window.exchangeNativeRequest = (path, body) => new Promise((resolve, reject) => {
    const id = String(++nextId);
    const timer = setTimeout(() => { pending.delete(id); reject(new Error('응답 시간이 초과되었습니다. 다시 시도해 주세요.')); }, 45000);
    pending.set(id, {resolve, reject, timer});
    window.ExchangeAndroid.request(id, path, JSON.stringify(body === undefined ? null : body));
  });
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('.download').addEventListener('click', async event => {
      event.preventDefault();
      try { await window.exchangeNativeRequest('/api/export'); }
      catch (error) { document.getElementById('notice').textContent = error.message; }
    });
    document.querySelector('.source').addEventListener('click', event => {
      event.preventDefault();
      window.location.href = event.currentTarget.href;
    });
  });
})();
