// Configuración de la URL base según el entorno
export const API_URL = (() => {
  const manifest = chrome.runtime.getManifest();
  const isDevelopment = manifest.version === '0.0.1';
  const baseUrl = isDevelopment 
    ? 'http://localhost:5001'
    : 'https://api.getathos.com';
  
  console.log('API URL configurada:', baseUrl, '(Development:', isDevelopment, ')');
  return baseUrl;
})();

interface Policy {
  domain: string;
  action: PolicyAction;
  category?: string;
  block_reason?: string;
  group_id?: string | null;
  group?: { name: string } | null;
}

interface NavigationEvent {
  domain: string;
  url: string;
  action: string;
  timestamp: string;
  ip_address?: string;
  user_agent: string;
  tab_title: string;
  time_on_page: number;
  open_tabs_count: number;
  tab_focused: boolean;
  event_type: 'navegacion' | 'formulario' | 'descarga' | 'bloqueo';
  event_details: Record<string, any>;
  risk_score: number;
}

interface UserInteractionEvent {
  tipo_evento: 'click' | 'copy' | 'paste' | 'download' | 'file_upload' | 'cut' | 'print';
  elemento_target: {
    tag: string;
    id?: string;
    class?: string;
    text?: string;
  };
  nombre_archivo?: string;
  timestamp: string;
  url_origen: string;
}

let policies: Policy[] = [];
let tabTimers: Map<number, { startTime: number, timer: number }> = new Map();

// Obtener IP pública
async function getPublicIP(): Promise<string | undefined> {
  try {
    const response = await fetch('https://api.ipify.org?format=json');
    const data = await response.json();
    return data.ip;
  } catch (e) {
    console.error('Error fetching IP:', e);
    return undefined;
  }
}

// Obtener cantidad de pestañas abiertas
async function getOpenTabsCount(): Promise<number> {
  const tabs = await chrome.tabs.query({});
  return tabs.length;
}

// Obtener políticas desde el backend
enum PolicyAction {
  Block = 'block',
  Allow = 'allow',
}

async function fetchPolicies(): Promise<void> {
  const { jwt_token } = await chrome.storage.local.get('jwt_token');
  if (!jwt_token) {
    console.log('[Athos] No se encontró token JWT, omitiendo fetch de políticas');
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icon128.png',
      title: 'Athos: Inicio de Sesión Requerido',
      message: 'Por favor, inicia sesión para activar la protección',
      priority: 2
    });
    return;
  }

  try {
    console.log('[Athos] Iniciando verificación de políticas...');
    
    // Verificar si el servidor está disponible
    const serverCheck = await fetch(`${API_URL}/health`, {
      method: 'HEAD',
      headers: {
        'Authorization': `Bearer ${jwt_token}`
      }
    }).catch(() => null);

    if (!serverCheck) {
      throw new Error(`No se puede conectar al servidor en ${API_URL}. Verifica que el servidor esté corriendo.`);
    }

    console.log('[Athos] Servidor disponible, obteniendo políticas...');
    const res = await fetch(`${API_URL}/api/policies`, {
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!res.ok) {
      if (res.status === 401) {
        console.log('[Athos] Token expirado o inválido');
        await chrome.storage.local.remove('jwt_token');
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icon128.png',
          title: 'Athos: Sesión Expirada',
          message: 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.',
          priority: 2
        });
        return;
      }
      // Obtener el mensaje de error completo
      const errorText = await res.text();
      console.error('[Athos] Error completo del servidor:', {
        status: res.status,
        statusText: res.statusText,
        errorText: errorText
      });
      throw new Error(`Error HTTP! status: ${res.status}, details: ${errorText}`);
    }
    
    const data = await res.json();
    if (data.success) {
      policies = data.data;
      await chrome.storage.local.set({ policies });
      console.log('[Athos] Políticas actualizadas exitosamente:', {
        total_policies: policies.length,
        blocked_policies: policies.filter(p => p.action === 'block').length,
        allowed_policies: policies.filter(p => p.action === 'allow').length
      });
    } else {
      console.error('[Athos] API retornó respuesta no exitosa:', {
        error: data.error,
        message: data.message,
        status: res.status,
        details: data.details || 'No hay detalles adicionales'
      });

      // Notificar al usuario si hay un error de base de datos
      if (data.error?.includes('relation') || data.error?.includes('table')) {
        console.error('[Athos] Error de base de datos detectado:', {
          error: data.error,
          hint: data.hint,
          details: data.details
        });
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icon128.png',
          title: 'Athos: Error de Configuración',
          message: 'Error al cargar políticas. Contacta al administrador del sistema.',
          priority: 2
        });
      }
    }
  } catch (e: any) {
    const errorMessage = e?.message || 'Error desconocido';
    console.error('[Athos] Error al obtener políticas:', {
      message: errorMessage,
      stack: e?.stack,
      url: `${API_URL}/api/policies`,
      timestamp: new Date().toISOString()
    });

    // Notificar al usuario sobre el error de conexión
    if (errorMessage.includes('No se puede conectar al servidor')) {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon128.png',
        title: 'Athos: Error de Conexión',
        message: 'No se puede conectar al servidor. Verifica tu conexión o contacta a soporte.',
        priority: 2
      });
    }
  }
}

// Función para calcular el tiempo en página
async function calculateTimeOnPage(tabId: number): Promise<number> {
  const timer = tabTimers.get(tabId);
  if (!timer) return 0;
  return Math.floor((Date.now() - timer.startTime) / 1000);
}

// Obtener ID de la pestaña actual
async function getCurrentTabId(): Promise<number> {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0]?.id || 0;
}

// Verificar si una URL debe ser bloqueada
async function isBlocked(url: string): Promise<boolean> {
  try {
    const hostname = new URL(url).hostname;
    console.log(`[Athos] Verificando URL: ${url} (hostname: ${hostname})`);
    
    // Primero verificamos las políticas locales
    const blockedPolicy = policies.find(policy => {
      const policyDomain = policy.domain.toLowerCase();
      const currentHostname = hostname.toLowerCase();
      const matches = currentHostname === policyDomain || 
                     currentHostname.endsWith('.' + policyDomain);
      
      if (matches && policy.action === PolicyAction.Block) {
        console.log(`[Athos] URL bloqueada por política local: ${policyDomain}`);
        return true;
      }
      return false;
    });

    if (blockedPolicy) {
      console.log(`[Athos] URL bloqueada por política: ${blockedPolicy.domain}`);
      return true;
    }

    // Si no hay políticas locales que bloqueen, consultamos al backend
    const { jwt_token } = await chrome.storage.local.get('jwt_token');
    if (!jwt_token) {
      console.log(`[Athos] No hay token JWT, no se puede consultar al backend`);
      return false;
    }

    console.log(`[Athos] Enviando consulta al backend para verificar URL...`);
    const response = await fetch(`${API_URL}/api/navigation_logs`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url: url,
        action: 'visitado',
        event_type: 'navegacion',
        domain: hostname
      })
    });

    const data = await response.json();
    console.log(`[Athos] Respuesta completa del backend:`, JSON.stringify(data, null, 2));

    if (!data.success) {
      console.error(`[Athos] Error en la respuesta del backend:`, data.error);
      return true; // Por seguridad, bloqueamos si hay error
    }

    // Verificar si la URL está bloqueada por el backend
    if (data.data.blocked === true) {
      console.log(`[Athos] URL bloqueada por el backend:`, {
        reason: data.data.reason,
        details: data.data.details
      });
      return true;
    }

    console.log(`[Athos] URL permitida por el backend`);
    return false;
  } catch (e) {
    console.error('[Athos] Error checking if URL is blocked:', e);
    return true; // Por seguridad, bloqueamos si hay error
  }
}

// Redirigir a blocked.html
function redirectToBlocked(tabId: number, url: string) {
  const blockedUrl = chrome.runtime.getURL(`blocked.html?url=${encodeURIComponent(url)}`);
  console.log(`[Athos] Redirigiendo a página de bloqueo: ${blockedUrl}`);
  chrome.tabs.update(tabId, { url: blockedUrl });
}

// Listener para navegación
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
  if (details.frameId !== 0) return;
  const url = details.url;
  if (!url.startsWith('http')) return;

  try {
    console.log(`[Athos] Verificando navegación a: ${url}`);
    const isUrlBlocked = await isBlocked(url);
    console.log(`[Athos] Resultado de verificación: ${isUrlBlocked ? 'BLOQUEADA' : 'PERMITIDA'}`);

    if (isUrlBlocked) {
      console.log(`[Athos] Redirigiendo a página de bloqueo...`);
      redirectToBlocked(details.tabId, url);
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon128.png',
        title: 'Sitio Bloqueado',
        message: `El acceso a ${new URL(url).hostname} ha sido bloqueado por políticas de la organización.`,
        priority: 2
      });
    }
  } catch (error) {
    console.error('[Athos] Error en el listener de navegación:', error);
  }
});

// Detectar envío de formularios
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    if (details.type === 'main_frame' && details.method === 'POST') {
      const url = details.url;
      registerNavigation(url, 'formulario_enviado', 'formulario', {
        method: details.method,
        form_data: details.requestBody
      });
    }
    return { cancel: false };
  },
  { urls: ['<all_urls>'] },
  ['requestBody']
);

// Detectar descargas
if (chrome.downloads) {
  chrome.downloads.onCreated.addListener(async (downloadItem) => {
    try {
      const url = downloadItem.url;
      await registerNavigation(url, 'descarga_iniciada', 'descarga', {
        filename: downloadItem.filename,
        file_size: downloadItem.fileSize,
        mime_type: downloadItem.mime
      });
    } catch (error) {
      console.error('Error al registrar descarga:', error);
    }
  });
} else {
  console.warn('API de descargas no disponible');
}

// Limpiar timers cuando se cierra una pestaña
chrome.tabs.onRemoved.addListener((tabId) => {
  const timer = tabTimers.get(tabId);
  if (timer) {
    clearTimeout(timer.timer);
    tabTimers.delete(tabId);
  }
});

// Actualizar políticas al iniciar sesión o cuando cambie el token
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.jwt_token) {
    if (changes.jwt_token.newValue) {
      console.log('[Athos] Token JWT actualizado, iniciando fetch de políticas');
      fetchPolicies();
    } else {
      console.log('[Athos] Token JWT eliminado, limpiando políticas');
      policies = [];
    }
  }
});

// Inicializar el service worker
chrome.runtime.onInstalled.addListener(async () => {
    console.log('[Athos] Service Worker instalado');
    const { jwt_token } = await chrome.storage.local.get('jwt_token');
    if (jwt_token) {
        console.log('[Athos] Token JWT encontrado, iniciando fetch de políticas');
        await fetchPolicies();
    } else {
        console.log('[Athos] No hay sesión activa, esperando inicio de sesión');
    }
});

// Verificar que el service worker está activo
chrome.runtime.onStartup.addListener(async () => {
    console.log('[Athos] Service Worker iniciado');
    const { jwt_token } = await chrome.storage.local.get('jwt_token');
    if (jwt_token) {
        console.log('[Athos] Token JWT encontrado, iniciando fetch de políticas');
        await fetchPolicies();
    } else {
        console.log('[Athos] No hay sesión activa, esperando inicio de sesión');
    }
});

// Refrescar políticas cada 5 minutos
setInterval(fetchPolicies, 5 * 60 * 1000);

// Inicializar políticas al cargar background
fetchPolicies();

// Manejar mensajes del content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('[Athos] Mensaje recibido del content script:', message);
    
    if (message.type === 'user_interaction') {
        const eventDetails = {
            texto: message.texto,
            tipo_evento: message.tipo_evento,
            nombre_archivo: message.nombre_archivo,
            elemento_target: message.elemento_target
        };
        
        console.log('[Athos] Detalles del evento procesados:', eventDetails);
        
        registerNavigation({
            url: message.url_origen,
            action: 'visitado',
            eventType: 'navegacion',
            eventDetails: eventDetails,
            timestamp: message.timestamp,
            hasToken: true
        });
    } else if (message.type === 'user_logout') {
        console.log('[Athos] Usuario ha cerrado sesión');
        chrome.storage.local.remove(['jwt_token', 'policies'], () => {
            console.log('[Athos] Datos de sesión limpiados');
        });
    }
});

// Función para obtener el token JWT
async function getToken(): Promise<string | null> {
    try {
        const { jwt_token } = await chrome.storage.local.get('jwt_token');
        return jwt_token || null;
    } catch (error) {
        console.error('[Athos] Error al obtener token:', error);
        return null;
    }
}

async function registerNavigation(data: {
    url: string;
    action: string;
    eventType: string;
    eventDetails: any;
    timestamp?: string;
    hasToken?: boolean;
}) {
    try {
        console.log('[Athos] Intentando registrar navegación:', data);
        
        if (!data.hasToken) {
            console.log('[Athos] No hay token, omitiendo registro');
            return;
        }

        const token = await getToken();
        if (!token) {
            console.log('[Athos] No se encontró token JWT');
            return;
        }

        const eventData = {
            url: data.url,
            action: data.action,
            event_type: data.eventType,
            event_details: data.eventDetails,
            timestamp: data.timestamp || new Date().toISOString(),
            ip_address: null,
            user_agent: navigator.userAgent,
            tab_title: null,
            time_on_page: 0,
            open_tabs_count: 0,
            tab_focused: true,
            risk_score: 10
        };

        console.log('[Athos] Enviando evento a la API:', {
            endpoint: `${API_URL}/api/navigation_logs`,
            eventType: data.eventType,
            eventDetails: data.eventDetails,
            timestamp: eventData.timestamp
        });

        const response = await fetch(`${API_URL}/api/navigation_logs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(eventData)
        });

        console.log('[Athos] Respuesta de la API:', {
            status: response.status,
            ok: response.ok,
            statusText: response.statusText
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('[Athos] Error detallado:', {
                status: response.status,
                statusText: response.statusText,
                errorText: errorText
            });
            throw new Error(`Error al registrar navegación: ${response.status} - ${response.statusText}`);
        }

        const responseData = await response.json();
        console.log('[Athos] Datos de respuesta:', responseData);

    } catch (error) {
        console.error('[Athos] Error al registrar navegación:', error);
    }
}

// Calcular puntaje de riesgo
function calculateRiskScore(eventType: string, details: Record<string, any>): number {
  let score = 0;
  
  // Lógica básica de puntuación
  switch (eventType) {
    case 'formulario':
      score += 20;
      break;
    case 'descarga':
      score += 30;
      break;
    case 'bloqueo':
      score += 50;
      break;
    case 'interaccion_usuario':
      // Ajustar puntaje según tipo de interacción
      switch (details.tipo_evento) {
        case 'copy':
        case 'paste':
          score += 25; // Interacciones con contenido sensible
          break;
        case 'download':
        case 'file_upload':
          score += 35; // Interacciones con archivos
          break;
        case 'click':
          score += 15; // Interacciones básicas
          break;
      }
      break;
    default:
      score += 10;
  }

  // Ajustar según detalles específicos
  if (details.sensitive_fields) {
    score += 15;
  }
  if (details.file_type && ['exe', 'zip', 'rar'].includes(details.file_type)) {
    score += 25;
  }
  if (details.nombre_archivo) {
    const extension = details.nombre_archivo.split('.').pop()?.toLowerCase();
    if (extension && ['exe', 'zip', 'rar', 'pdf', 'doc', 'docx'].includes(extension)) {
      score += 20;
    }
  }

  return Math.min(score, 100);
} 