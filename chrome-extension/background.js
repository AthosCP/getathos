import { Storage } from "@plasmohq/storage"

const storage = new Storage()
const API_URL = "http://localhost:5001"

// Función para verificar si una URL está bloqueada
async function checkUrl(url) {
  try {
    // Usar chrome.storage.local para consistencia con popup.js
    const { jwt_token } = await chrome.storage.local.get('jwt_token')
    if (!jwt_token) {
      console.log("No hay token disponible")
      return false
    }

    const domain = new URL(url).hostname
    console.log("Verificando dominio:", domain)

    const response = await fetch(`${API_URL}/api/policies`, {
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      console.error("Error en la respuesta:", response.status, response.statusText)
      return false
    }

    const data = await response.json()
    console.log("Políticas recibidas:", data)

    if (!data.success) {
      console.error("Error en los datos:", data.error)
      return false
    }

    // Buscar políticas que coincidan con el dominio
    const policies = data.data
    // Mejorar la lógica de matching para evitar falsos positivos
    const matchingPolicy = policies.find(p => {
      // Verificar dominio exacto o subdominio
      const domainMatches = domain === p.domain || domain.endsWith('.' + p.domain);
      // Verificar acción de bloqueo
      return domainMatches && p.action === 'block';
    });

    if (matchingPolicy) {
      console.log("Política encontrada:", matchingPolicy)
      // Registrar el bloqueo
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
            timestamp: new Date().toISOString()
          })
        })
      } catch (error) {
        console.error("Error al registrar bloqueo:", error)
      }
      return true
    }

    return false
  } catch (error) {
    console.error("Error checking URL:", error)
    return false
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
        message: `El acceso a ${domain} ha sido bloqueado por políticas de la organización.`,
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