// Configuración de la URL base según el entorno
const API_URL = process.env.NODE_ENV === 'production'
  ? 'https://api.getathos.com'
  : 'http://localhost:5001';

const content = document.getElementById('athos-content');

function renderLogin(errorMsg = '') {
  content!.innerHTML = `
    <div class="athos-card">
      <form id="athos-login-form">
        <input class="athos-input" type="email" id="athos-email" placeholder="Correo electrónico" required autocomplete="username" />
        <input class="athos-input" type="password" id="athos-password" placeholder="Contraseña" required autocomplete="current-password" />
        ${errorMsg ? `<div class="athos-error">${errorMsg}</div>` : ''}
        <button class="athos-btn" type="submit">Iniciar protección</button>
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
    <div class="athos-card">
      <div class="athos-status">Protección activa</div>
      <div class="athos-counter" id="athos-threats">0</div>
      <div class="athos-label">Amenazas bloqueadas hoy</div>
      <div class="athos-logout" id="athos-logout">Terminar protección</div>
    </div>
  `;
  document.getElementById('athos-logout')!.onclick = async () => {
    await chrome.storage.local.remove('jwt_token');
    renderLogin();
  };
  // Aquí podrías actualizar el contador de amenazas si en el futuro hay endpoint
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