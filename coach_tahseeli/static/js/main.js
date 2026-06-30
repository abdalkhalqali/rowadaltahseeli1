// ===== رواد التحصيلي — JavaScript الرئيسي =====

document.addEventListener('DOMContentLoaded', () => {
  initAnimations();
  initFlashMessages();
  initNavHighlight();
});

// ===== Auto-dismiss Flash Messages =====
function initFlashMessages() {
  const alerts = document.querySelectorAll('.alert');
  if (!alerts.length) return;
  setTimeout(() => {
    alerts.forEach(a => {
      a.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      a.style.opacity = '0';
      a.style.transform = 'translateY(-10px)';
      setTimeout(() => a.remove(), 500);
    });
  }, 4500);
}

// ===== Intersection Observer Animations =====
function initAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.animate-in').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(24px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
  });
}

// ===== Navbar Active Link =====
function initNavHighlight() {
  const current = location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.href.includes(current) && current !== '/') {
      a.classList.add('active');
    }
  });
}

// ===== API Helper =====
async function apiPost(url, data) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return r.json();
}

// ===== Score Circle Animate =====
function animateScore(el, target) {
  let current = 0;
  const step = target / 60;
  const interval = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = Math.round(current) + '%';
    if (current >= target) clearInterval(interval);
  }, 20);
}

// ===== Progress bars animate =====
function animateProgressBars() {
  document.querySelectorAll('[data-progress]').forEach(bar => {
    const target = bar.getAttribute('data-progress');
    setTimeout(() => { bar.style.width = target + '%'; }, 200);
  });
}

// ===== Loading spinner =====
function showLoading(text = 'جاري التحميل...') {
  const el = document.createElement('div');
  el.className = 'loading-overlay';
  el.id = 'globalLoader';
  el.innerHTML = `<div class="spinner"></div><p style="color:var(--text-muted)">${text}</p>`;
  document.body.appendChild(el);
}

function hideLoading() {
  const el = document.getElementById('globalLoader');
  if (el) el.remove();
}

// ===== Confirm Dialog =====
function confirmAction(msg, callback) {
  if (confirm(msg)) callback();
}

// ===== Format Time =====
function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// ===== AI Chat Widget (simple) =====
function initAIChat(subject = 'general') {
  const chatBtn = document.getElementById('chatBtn');
  if (!chatBtn) return;

  chatBtn.addEventListener('click', () => {
    const panel = document.getElementById('chatPanel');
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
  });

  const sendBtn = document.getElementById('chatSend');
  const input   = document.getElementById('chatInput');
  const msgs    = document.getElementById('chatMessages');

  if (!sendBtn) return;

  sendBtn.addEventListener('click', async () => {
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';

    msgs.innerHTML += `<div style="text-align:right;margin-bottom:8px">
      <span style="background:var(--gold-glow);border-radius:10px;padding:8px 12px;
                   display:inline-block;font-size:0.88rem;color:var(--text-primary)">${msg}</span></div>`;

    const thinkingDiv = document.createElement('div');
    thinkingDiv.innerHTML = `<div class="spinner" style="width:24px;height:24px;margin:8px 0"></div>`;
    msgs.appendChild(thinkingDiv);
    msgs.scrollTop = msgs.scrollHeight;

    try {
      const data = await apiPost('/ai/chat', { message: msg, subject });
      thinkingDiv.remove();
      msgs.innerHTML += `<div style="margin-bottom:8px">
        <span style="background:var(--bg-elevated);border-radius:10px;padding:8px 12px;
                     display:inline-block;font-size:0.88rem;color:var(--text-secondary)">${data.reply}</span></div>`;
    } catch(e) {
      thinkingDiv.remove();
      msgs.innerHTML += `<div style="color:var(--danger);font-size:0.82rem">حدث خطأ في الاتصال</div>`;
    }
    msgs.scrollTop = msgs.scrollHeight;
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendBtn.click(); }
  });
}
