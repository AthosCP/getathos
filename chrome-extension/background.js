// --- NUEVO: Sincronización de dominios prohibidos ---
async function syncProhibidos() {
  const { jwt_token } = await chrome.storage.local.get('jwt_token');
  if (!jwt_token) return;
  try {
    const response = await fetch(`${API_URL}/api/prohibidos`, {
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      }
    });
    if (!response.ok) return;
    const data = await response.json();
    if (data.success && data.data) {
      await chrome.storage.local.set({
        prohibidos: data.data,
        prohibidos_last_sync: Date.now()
      });
      console.log('[SYNC] Lista de prohibidos actualizada');
    }
  } catch (e) {
    console.error('[SYNC] Error al sincronizar prohibidos:', e);
  }
}

// Sincronizar al login y cada hora
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.jwt_token) {
    syncProhibidos();
  }
});
chrome.runtime.onInstalled.addListener(() => {
  syncProhibidos();
  setInterval(syncProhibidos, 60 * 60 * 1000); // Cada hora
});
setInterval(syncProhibidos, 60 * 60 * 1000); // Refresco extra por si acaso

// Función para verificar si una URL está bloqueada
async function checkUrl(url) {
  try {
    const { jwt_token, prohibidos, prohibidos_last_sync } = await chrome.storage.local.get(['jwt_token', 'prohibidos', 'prohibidos_last_sync']);
    if (!jwt_token) {
      console.log('No hay token disponible');
      return false;
    }
    // Refrescar lista si han pasado más de 1 hora
    if (!prohibidos || !prohibidos_last_sync || (Date.now() - prohibidos_last_sync > 60 * 60 * 1000)) {
      await syncProhibidos();
    }
    const domain = new URL(url).hostname.replace(/^www\./, '');
    let foundCategory = null;
    if (prohibidos) {
      for (const [category, domains] of Object.entries(prohibidos)) {
        if (domains.some(d => domain === d || domain.endsWith('.' + d))) {
          foundCategory = category;
          break;
        }
      }
    }
    if (foundCategory) {
      // Registrar el intento en el backend
      try {
        await fetch(`${API_URL}/api/navigation_logs`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${jwt_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            domain,
            url,
            action: 'bloqueado',
            timestamp: new Date().toISOString(),
            policy_info: { block_reason: 'prohibited_list', category: foundCategory }
          })
        });
      } catch (e) {
        console.error('[SYNC] Error registrando intento bloqueado:', e);
      }
      return true;
    }
    return false;
  } catch (error) {
    console.error('Error checking URL:', error);
    return false;
  }
}

// Registrar navegación
async function logNavigation(url, action = 'visitado') {
  try {
    const { jwt_token } = await chrome.storage.local.get('jwt_token')
    if (!jwt_token) {
      console.log("No hay token, no se puede registrar navegación")
      return
    }

    const domain = new URL(url).hostname
    
    // Enviar log al backend
    const response = await fetch(`${API_URL}/api/navigation_logs`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        domain,
        url,
        action,
        timestamp: new Date().toISOString()
      })
    })

    if (!response.ok) {
      console.error("Error al registrar navegación:", response.status)
      return
    }

    console.log(`Navegación registrada: ${domain} (${action})`)
  } catch (error) {
    console.error("Error registrando navegación:", error)
  }
}

// Manifest V3 ya no admite webRequest.onBeforeRequest con blocking
// Usamos declarativeNetRequest para el bloqueo dinámico
async function setupBlockingRules() {
  try {
    const { jwt_token } = await chrome.storage.local.get('jwt_token')
    if (!jwt_token) {
      console.log("No hay token para obtener reglas")
      return
    }

    // Obtener las políticas de bloqueo
    const response = await fetch(`${API_URL}/api/policies`, {
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      console.error("Error al obtener políticas para reglas:", response.status)
      return
    }

    const data = await response.json()
    if (!data.success) {
      console.error("Error en datos de políticas:", data.error)
      return
    }

    // Extraer dominios bloqueados
    const blockedDomains = data.data
      .filter(p => p.action === 'block')
      .map(p => p.domain)

    console.log("Configurando reglas para bloquear dominios:", blockedDomains)

    // Crear reglas de bloqueo
    const rules = blockedDomains.map((domain, index) => ({
      id: index + 1,
      priority: 1,
      action: { type: 'block' },
      condition: {
        urlFilter: `*://*.${domain}/*`,
        resourceTypes: ['main_frame']
      }
    }))

    // Eliminar reglas anteriores y aplicar nuevas
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: Array.from({ length: 100 }, (_, i) => i + 1), // Eliminar hasta 100 reglas existentes
      addRules: rules
    })

    console.log("Reglas de bloqueo actualizadas")
  } catch (error) {
    console.error("Error configurando reglas de bloqueo:", error)
  }
}

// Función para incrementar el contador de sitios bloqueados
async function incrementBlockCount() {
  try {
    const { blockedCount = 0 } = await chrome.storage.local.get('blockedCount')
    await chrome.storage.local.set({ blockedCount: blockedCount + 1 })
    console.log("Contador de bloqueos incrementado:", blockedCount + 1)
  } catch (error) {
    console.error("Error incrementando contador:", error)
  }
}

// Verificar URL antes de la solicitud (compatibilidad)
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
  if (details.frameId === 0) { // Solo frame principal
    console.log("Navegando a:", details.url)
    const isBlocked = await checkUrl(details.url)
    if (isBlocked) {
      console.log("URL bloqueada:", details.url)
      
      // Incrementar contador de bloqueos
      await incrementBlockCount()
      
      // Mostrar notificación de bloqueo
      const domain = new URL(details.url).hostname
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon128.png',
        title: 'Sitio Bloqueado',
        message: `El acceso a ${domain} ha sido bloqueado por políticas de la empresa.`,
        priority: 2
      });
      
      // No podemos bloquear directamente, pero podemos redirigir
      chrome.tabs.update(details.tabId, { 
        url: `blocked.html?url=${encodeURIComponent(details.url)}` 
      })
    }
  }
})

// Actualizar reglas cuando cambia el token
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'local' && changes.jwt_token) {
    console.log("Token actualizado, reconfigurando reglas de bloqueo")
    setupBlockingRules()
  }
})

// Configurar reglas al instalar/actualizar la extensión
chrome.runtime.onInstalled.addListener(() => {
  console.log("Extensión instalada/actualizada")
  setupBlockingRules()
})

// Actualizar reglas periódicamente
setInterval(setupBlockingRules, 60000) // Cada minuto 

// Escuchar eventos de navegación completada (para registrar visitas exitosas)
chrome.webNavigation.onCompleted.addListener(details => {
  if (details.frameId === 0) { // Solo frame principal
    logNavigation(details.url, 'visitado')
  }
}, { url: [{ schemes: ['http', 'https'] }] })

// También registrar cuando se actualiza una pestaña
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && tab.url.startsWith('http')) {
    console.log("Registrando navegación desde onUpdated:", tab.url)
    logNavigation(tab.url, 'visitado')
  }
}) 