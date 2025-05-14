// Configuración de la URL base según el entorno
const API_URL = process.env.NODE_ENV === 'production'
  ? 'https://api.getathos.com'
  : 'http://localhost:5001';

const content = document.getElementById('athos-content');

function renderLogin(errorMsg = '') {
  content!.innerHTML = `
    <div class="athos-bg-black athos-login-outer">
      <img src="typo.png" class="athos-typo-new" alt="Athos logo" />
      <div class="athos-login-title">Iniciar sesión</div>
      <div class="athos-login-subtitle">Athos Cybersecurity Platform</div>
      <form id="athos-login-form" class="athos-login-form-new">
        <input class="athos-input-new" type="email" id="athos-email" placeholder="Email" required autocomplete="username" />
        <input class="athos-input-new" type="password" id="athos-password" placeholder="Contraseña" required autocomplete="current-password" />
        ${errorMsg ? `<div class="athos-error-new">${errorMsg}</div>` : ''}
        <button class="athos-btn-new" type="submit">Iniciar Sesión</button>
      </form>
    </div>
  `;
  const form = document.getElementById('athos-login-form') as HTMLFormElement;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const email = (document.getElementById('athos-email') as HTMLInputElement).value;
    const password = (document.getElementById('athos-password') as HTMLInputElement).value;
    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (data.success && data.access_token) {
        await chrome.storage.local.set({ jwt_token: data.access_token });
        renderProtected();
      } else {
        renderLogin(data.error || 'Credenciales inválidas');
      }
    } catch (err) {
      renderLogin('Error de red o servidor');
    }
  };
}

function renderProtected() {
  content!.innerHTML = `
    <div class="athos-bg-black athos-login-outer">
      <img src="typo.png" class="athos-typo-new" alt="Athos logo" />
      <img src="athos.gif" class="athos-gif-new" alt="Animación Athos" />
      <div class="athos-protected-label">Protección activa</div>
      <a href="#" id="athos-logout" class="athos-link-red">Terminar protección</a>
    </div>
  `;
  document.getElementById('athos-logout')!.onclick = async (e) => {
    e.preventDefault();
    // Enviamos evento de logout para registro
    chrome.runtime.sendMessage({
      type: 'user_logout',
      data: {
        url: window.location.href,
        timestamp: new Date().toISOString()
      }
    });
    await chrome.storage.local.remove('jwt_token');
    renderLogin();
  };
}

async function checkAuth() {
  const { jwt_token } = await chrome.storage.local.get('jwt_token');
  if (!jwt_token) {
    renderLogin();
    return;
  }
  // Validar token con backend
  try {
    const res = await fetch(`${API_URL}/api/config`, {
      headers: { 'Authorization': `Bearer ${jwt_token}` }
    });
    const data = await res.json();
    if (data.success) {
      renderProtected();
    } else {
      renderLogin();
    }
  } catch {
    renderLogin();
  }
}

checkAuth();

// Escuchar cambios de sesión desde otras partes de la extensión
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.jwt_token) {
    checkAuth();
  }
});