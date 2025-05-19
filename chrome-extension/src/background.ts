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
    console.log('No JWT token found, skipping policy fetch');
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

    console.log('Fetching policies from:', `${API_URL}/api/policies`);
    const res = await fetch(`${API_URL}/api/policies`, {
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!res.ok) {
      if (res.status === 401) {
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
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    
    const data = await res.json();
    if (data.success) {
      policies = data.data;
      await chrome.storage.local.set({ policies });
      console.log('Policies updated successfully');
    } else {
      console.error('API returned unsuccessful response:', data);
    }
  } catch (e: any) {
    const errorMessage = e?.message || 'Unknown error';
    console.error('Error fetching policies:', {
      message: errorMessage,
      stack: e?.stack,
      url: `${API_URL}/api/policies`
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
function isBlocked(url: string): boolean {
  try {
    const hostname = new URL(url).hostname;
    
    // Primero verificamos si hay una política específica de grupo que bloquee
    const groupBlockPolicy = policies.find(policy =>
      (hostname === policy.domain || hostname.endsWith('.' + policy.domain)) &&
      policy.action === PolicyAction.Block &&
      policy.group_id !== null
    );
    
    if (groupBlockPolicy) {
      return true;
    }
    
    // Si no hay política de grupo que bloquee, verificamos las políticas generales
    return policies.some(policy =>
      (hostname === policy.domain || hostname.endsWith('.' + policy.domain)) &&
      policy.action === PolicyAction.Block &&
      policy.group_id === null
    );
  } catch (e) {
    console.error('Error checking if URL is blocked:', e);
    return false;
  }
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
    await registerNavigation(url, 'bloqueado', 'bloqueo', {
      reason: 'policy_violation',
      policy_details: policies.find(p => 
        new URL(url).hostname === p.domain || 
        new URL(url).hostname.endsWith('.' + p.domain)
      )
    });
    redirectToBlocked(details.tabId, url);
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icon128.png',
      title: 'Sitio Bloqueado',
      message: `El acceso a ${new URL(url).hostname} ha sido bloqueado por políticas de la organización.`,
      priority: 2
    });
  } else {
    const logResponse = await registerNavigation(url, 'visitado');
    if (
      logResponse &&
      logResponse.data &&
      logResponse.data[0] &&
      logResponse.data[0].action === 'bloqueado' &&
      logResponse.data[0].policy_info &&
      Array.isArray(logResponse.data[0].policy_info.block_reason) &&
      logResponse.data[0].policy_info.block_reason.includes('prohibited_list')
    ) {
      redirectToBlocked(details.tabId, url);
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon128.png',
        title: 'Sitio Bloqueado',
        message: `El acceso a ${new URL(url).hostname} ha sido bloqueado por lista prohibida.`,
        priority: 2
      });
    }
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
    fetchPolicies();
  }
});

// Inicializar el service worker
chrome.runtime.onInstalled.addListener(() => {
  console.log('Service Worker instalado');
  fetchPolicies();
});

// Verificar que el service worker está activo
chrome.runtime.onStartup.addListener(() => {
  console.log('Service Worker iniciado');
  fetchPolicies();
});

// Refrescar políticas cada 5 minutos
setInterval(fetchPolicies, 5 * 60 * 1000);

// Inicializar políticas al cargar background
fetchPolicies();

// Escuchar mensajes del content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'user_interaction') {
    const event = message.data;
    registerNavigation(
      event.url_origen,
      'interaccion',
      event.tipo_evento,
      {
        elemento_target: event.elemento_target,
        texto: event.texto,
        nombre_archivo: event.nombre_archivo
      }
    ).catch(error => {
      console.error('Error al registrar interacción:', error);
    });
  } else if (message.type === 'user_logout') {
    const { url, timestamp } = message.data;
    registerNavigation(
      url,
      'logout_voluntario',
      'navegacion',
      {
        tipo_evento: 'logout',
        timestamp: timestamp,
        detalles: 'Logout iniciado por el usuario'
      }
    );
  }
});

async function registerNavigation(
  url: string, 
  action: string = 'visitado',
  eventType: NavigationEvent['event_type'] = 'navegacion',
  eventDetails: Record<string, any> = {}
): Promise<any> {
  const { jwt_token } = await chrome.storage.local.get('jwt_token');
  
  console.log('Intentando registrar navegación:', {
    url,
    action,
    eventType,
    hasToken: !!jwt_token,
    apiUrl: API_URL
  });

  if (!jwt_token) {
    console.error('No JWT token found for navigation registration');
    return;
  }

  try {
    const tab = await chrome.tabs.get(await getCurrentTabId());
    const hostname = new URL(url).hostname;
    const timeOnPage = await calculateTimeOnPage(tab.id || 0);

    console.log('Preparando evento de navegación:', {
      hostname,
      timeOnPage,
      tabTitle: tab.title,
      tabActive: tab.active
    });

    const navigationEvent: NavigationEvent = {
      domain: hostname,
      url: url,
      action: action,
      timestamp: new Date().toISOString(),
      ip_address: await getPublicIP(),
      user_agent: navigator.userAgent,
      tab_title: tab.title || '',
      time_on_page: timeOnPage,
      open_tabs_count: await getOpenTabsCount(),
      tab_focused: tab.active,
      event_type: eventType,
      event_details: {
        ...eventDetails,
        time_on_page_details: {
          is_periodic_update: action === 'tiempo_en_pagina',
          session_start: tabTimers.get(tab.id || 0)?.startTime
        }
      },
      risk_score: calculateRiskScore(eventType, eventDetails)
    };

    console.log('Enviando evento a la API:', {
      endpoint: `${API_URL}/api/navigation_logs`,
      eventType: navigationEvent.event_type,
      timestamp: navigationEvent.timestamp
    });

    const response = await fetch(`${API_URL}/api/navigation_logs`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(navigationEvent)
    });

    console.log('Respuesta de la API:', {
      status: response.status,
      ok: response.ok
    });

    const data = await response.json();
    console.log('Datos de respuesta:', data);
    return data;

  } catch (error: unknown) {
    console.error('Error detallado al registrar navegación:', {
      error,
      message: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined,
      url,
      action,
      eventType
    });
    return undefined;
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