// Configuración de la URL base según el entorno
const API_URL = process.env.NODE_ENV === 'production'
  ? 'https://api.getathos.com'
  : 'http://localhost:5001';

let policies: any[] = [];

// Obtener políticas desde el backend
async function fetchPolicies() {
  const { jwt_token } = await chrome.storage.local.get('jwt_token');
  if (!jwt_token) return;
  try {
    const res = await fetch(`${API_URL}/api/policies`, {
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      }
    });
    const data = await res.json();
    if (data.success) {
      policies = data.data;
      // Guardar en storage para acceso rápido desde popup si se quiere
      await chrome.storage.local.set({ policies });
    }
  } catch (e) {
    // No hacer nada, puede ser offline
  }
}

// Registrar navegación en el backend
async function registerNavigation(url: string, action: string = 'visitado') {
  const { jwt_token } = await chrome.storage.local.get('jwt_token');
  if (!jwt_token) return;
  const hostname = new URL(url).hostname;
  try {
    await fetch(`${API_URL}/api/navigation_logs`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        domain: hostname,
        url: url,
        action: action,
        timestamp: new Date().toISOString()
      })
    });
  } catch (e) {
    // No hacer nada, puede ser offline
  }
}

// Verificar si una URL debe ser bloqueada
function isBlocked(url: string): boolean {
  const hostname = new URL(url).hostname;
  return policies.some(policy =>
    (hostname === policy.domain || hostname.endsWith('.' + policy.domain)) &&
    policy.action === 'block'
  );
}

// Redirigir a blocked.html
function redirectToBlocked(tabId: number, url: string) {
  chrome.tabs.update(tabId, {
    url: `blocked.html?url=${encodeURIComponent(url)}`
  });
}

// Listener para navegación
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
  if (details.frameId !== 0) return;
  const url = details.url;
  if (!url.startsWith('http')) return;
  if (isBlocked(url)) {
    await registerNavigation(url, 'bloqueado');
    redirectToBlocked(details.tabId, url);
    // Opcional: notificación
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icon128.png',
      title: 'Sitio Bloqueado',
      message: `El acceso a ${new URL(url).hostname} ha sido bloqueado por políticas de la organización.`,
      priority: 2
    });
  } else {
    await registerNavigation(url, 'visitado');
  }
});

// Actualizar políticas al iniciar sesión o cuando cambie el token
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.jwt_token) {
    fetchPolicies();
  }
});

// Al instalar o actualizar la extensión, obtener políticas
chrome.runtime.onInstalled.addListener(() => {
  fetchPolicies();
});

// Refrescar políticas cada 5 minutos
setInterval(fetchPolicies, 5 * 60 * 1000);

// Inicializar políticas al cargar background
fetchPolicies(); 