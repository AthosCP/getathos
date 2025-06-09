interface UserInteractionEvent {
  tipo_evento: 'click' | 'copy' | 'paste' | 'download' | 'file_upload' | 'cut' | 'print';
  elemento_target: {
    tag: string;
    id?: string;
    class?: string;
    text?: string;
    value?: string;
    href?: string;
  };
  nombre_archivo?: string;
  timestamp: string;
  url_origen: string;
  texto?: string;
}

// Función para obtener información del elemento
function getElementInfo(element: HTMLElement): { tag: string; id?: string; class?: string; text?: string } {
    const info = {
        tag: element.tagName.toLowerCase(),
        id: element.id || undefined,
        class: element.className || undefined,
        text: element.textContent?.trim().substring(0, 100) || undefined
    };
    console.log('[Athos] Información del elemento:', info);
    return info;
}

// Función para enviar evento al background
function sendEventToBackground(eventData: UserInteractionEvent) {
    console.log("[Athos] Enviando evento al background:", eventData);
    try {
        chrome.runtime.sendMessage({
            type: 'user_interaction',
            data: eventData
        }, (response) => {
            if (chrome.runtime.lastError) {
                console.warn("[Athos] Error al enviar mensaje:", chrome.runtime.lastError.message);
                // Intentar reconectar si el contexto es inválido
                if (chrome.runtime.lastError.message.includes("Extension context invalidated")) {
                    console.log("[Athos] Intentando reconectar...");
                    setTimeout(() => {
                        sendEventToBackground(eventData);
                    }, 1000);
                }
                return;
            }
            console.log("[Athos] Respuesta del background:", response);
        });
    } catch (error) {
        console.error("[Athos] Error al enviar evento:", error);
        // Intentar reconectar si el contexto es inválido
        if (error instanceof Error && error.message.includes("Extension context invalidated")) {
            console.log("[Athos] Intentando reconectar...");
            setTimeout(() => {
                sendEventToBackground(eventData);
            }, 1000);
        }
    }
}

// Variables de control
let isAuthenticated = false;
let isActive = true;
let debounceTimer: number;

// Función para verificar autenticación
async function checkAuth() {
    const { jwt_token } = await chrome.storage.local.get('jwt_token');
    isAuthenticated = !!jwt_token;
    if (!isAuthenticated) {
        removeAllListeners();
    }
}

// Función para remover todos los listeners
function removeAllListeners() {
    document.removeEventListener('click', clickHandler);
    document.removeEventListener('copy', copyHandler);
    document.removeEventListener('paste', pasteHandler);
    document.removeEventListener('change', changeHandler);
    document.removeEventListener('cut', cutHandler);
    document.removeEventListener('keydown', handleKeyDown);
    document.removeEventListener('click', downloadHandler);
    window.removeEventListener('beforeprint', printHandler);
}

// Manejador de clicks
function clickHandler(event: MouseEvent) {
    if (!isActive || !isAuthenticated) return;
    const target = event.target as HTMLElement;
    const elementInfo = getElementInfo(target);
    
    const eventData: UserInteractionEvent = {
        tipo_evento: 'click',
        elemento_target: elementInfo,
        timestamp: new Date().toISOString(),
        url_origen: window.location.href,
        texto: target.textContent?.trim().substring(0, 100) || undefined
    };
    
    console.log('[Athos] Evento de click capturado:', eventData);
    sendEventToBackground(eventData);
}

// Manejador de copia
function copyHandler(event: ClipboardEvent) {
    if (!isActive || !isAuthenticated) return;
    const selection = window.getSelection();
    const selectedText = selection?.toString() || '';
    
    const eventData: UserInteractionEvent = {
        tipo_evento: 'copy',
        elemento_target: {
            tag: 'selection',
            text: selectedText.substring(0, 100)
        },
        timestamp: new Date().toISOString(),
        url_origen: window.location.href,
        texto: selectedText.substring(0, 100)
    };
    
    console.log('[Athos] Evento de copia capturado:', eventData);
    sendEventToBackground(eventData);
}

// Manejador de pegado
function pasteHandler(event: ClipboardEvent) {
    if (!isActive || !isAuthenticated) return;
    const pastedText = event.clipboardData?.getData('text') || '';
    const target = event.target as HTMLElement;
    
    const eventData: UserInteractionEvent = {
        tipo_evento: 'paste',
        elemento_target: getElementInfo(target),
        timestamp: new Date().toISOString(),
        url_origen: window.location.href,
        texto: pastedText.substring(0, 100)
    };
    
    console.log('[Athos] Evento de pegado capturado:', eventData);
    sendEventToBackground(eventData);
}

// Manejador de cambios (file upload)
function changeHandler(event: Event) {
    if (!isActive || !isAuthenticated) return;
    const target = event.target as HTMLInputElement;
    
    if (target.type === 'file') {
        const files = Array.from(target.files || []);
        files.forEach(file => {
            const eventData: UserInteractionEvent = {
                tipo_evento: 'file_upload',
                elemento_target: getElementInfo(target),
                nombre_archivo: file.name,
                timestamp: new Date().toISOString(),
                url_origen: window.location.href
            };
            
            console.log('[Athos] Evento de file upload capturado:', eventData);
            sendEventToBackground(eventData);
        });
    }
}

// Manejador de corte
function cutHandler(event: ClipboardEvent) {
    if (!isActive || !isAuthenticated) return;
    const selection = window.getSelection();
    const selectedText = selection?.toString() || '';
    
    const eventData: UserInteractionEvent = {
        tipo_evento: 'cut',
        elemento_target: {
            tag: 'selection',
            text: selectedText.substring(0, 100)
        },
        timestamp: new Date().toISOString(),
        url_origen: window.location.href,
        texto: selectedText.substring(0, 100)
    };
    
    console.log('[Athos] Evento de corte capturado:', eventData);
    sendEventToBackground(eventData);
}

// Manejador de impresión
function printHandler() {
    if (!isActive || !isAuthenticated) return;
    
    const eventData: UserInteractionEvent = {
        tipo_evento: 'print',
        elemento_target: { tag: 'window' },
        timestamp: new Date().toISOString(),
        url_origen: window.location.href
    };
    
    console.log('[Athos] Evento de impresión capturado:', eventData);
    sendEventToBackground(eventData);
}

// Manejador de descargas
function downloadHandler(event: MouseEvent) {
    if (!isActive || !isAuthenticated) return;
    const target = event.target as HTMLElement;
    
    // Verificar si es un enlace de descarga
    let downloadElement: HTMLAnchorElement | null = null;
    
    // Buscar elemento <a> con atributo download o que termine en extensión de archivo
    if (target.tagName.toLowerCase() === 'a') {
        downloadElement = target as HTMLAnchorElement;
    } else {
        // Buscar elemento padre que sea un enlace
        downloadElement = target.closest('a');
    }
    
    if (downloadElement) {
        const href = downloadElement.href;
        const downloadAttr = downloadElement.getAttribute('download');
        
        // Verificar si es una descarga (tiene atributo download o URL parece ser un archivo)
        const isDownload = downloadAttr !== null || 
                          /\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|jpg|jpeg|png|gif|mp4|mp3|txt|csv)$/i.test(href);
        
        if (isDownload) {
            // Extraer nombre del archivo
            let fileName = downloadAttr || '';
            if (!fileName) {
                // Extraer nombre del archivo de la URL
                const urlParts = href.split('/');
                fileName = urlParts[urlParts.length - 1] || 'archivo_desconocido';
                // Remover parámetros de query si existen
                fileName = fileName.split('?')[0];
            }
            
            const eventData: UserInteractionEvent = {
                tipo_evento: 'download',
                elemento_target: {
                    tag: downloadElement.tagName.toLowerCase(),
                    id: downloadElement.id || undefined,
                    class: downloadElement.className || undefined,
                    text: downloadElement.textContent?.trim().substring(0, 100) || undefined,
                    href: href
                },
                nombre_archivo: fileName,
                timestamp: new Date().toISOString(),
                url_origen: window.location.href
            };
            
            console.log('[Athos] Evento de descarga capturado:', eventData);
            sendEventToBackground(eventData);
        }
    }
}

// Función para manejar eventos de teclado
function handleKeyDown(event: KeyboardEvent) {
    if (!isActive || !isAuthenticated) return;
    
    // Detectar combinaciones de teclas importantes
    if (event.ctrlKey || event.metaKey) {
        let eventType: 'copy' | 'paste' | 'cut' | null = null;
        
        switch (event.key.toLowerCase()) {
            case 'c':
                eventType = 'copy';
                break;
            case 'v':
                eventType = 'paste';
                break;
            case 'x':
                eventType = 'cut';
                break;
            case 'p':
                // Ctrl+P para imprimir
                const printEventData: UserInteractionEvent = {
                    tipo_evento: 'print',
                    elemento_target: { tag: 'window' },
                    timestamp: new Date().toISOString(),
                    url_origen: window.location.href
                };
                console.log('[Athos] Evento de impresión (Ctrl+P) capturado:', printEventData);
                sendEventToBackground(printEventData);
                break;
        }
        
        if (eventType) {
            console.log(`[Athos] Combinación de teclas ${eventType} detectada:`, event.key);
        }
    }
}

// Función para agregar todos los listeners
function addAllListeners() {
    document.addEventListener('click', clickHandler);
    document.addEventListener('copy', copyHandler);
    document.addEventListener('paste', pasteHandler);
    document.addEventListener('change', changeHandler);
    document.addEventListener('cut', cutHandler);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('beforeprint', printHandler);
    
    // Listener específico para descargas en enlaces
    document.addEventListener('click', downloadHandler);
}

// Inicialización
async function initialize() {
    await checkAuth();
    if (isAuthenticated) {
        addAllListeners();
        console.log('[Athos] Active Protection: Monitoreo de riesgo activado');
    } else {
        console.log('[Athos] Active Protection: Usuario no autenticado, esperando autenticación');
    }
}

// Escuchar cambios en el storage
chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && changes.jwt_token) {
        checkAuth().then(() => {
            if (isAuthenticated) {
                addAllListeners();
                console.log('[Athos] Usuario autenticado, activando protección');
            } else {
                console.log('[Athos] Usuario desautenticado, removiendo protección');
            }
        });
    }
});

// Escuchar mensajes del background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'session_ended') {
        console.log('[Athos] Sesión finalizada, desactivando protección');
        isActive = false;
        removeAllListeners();
        // Limpiar cualquier estado pendiente
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }
        sendResponse({ success: true });
    }
});

// Interceptar descargas en enlaces y blobs
document.addEventListener('click', async function(e) {
  if (!isActive || !isAuthenticated) return;
  const target = e.target as HTMLElement;
  let link: HTMLAnchorElement | null = null;

  if (target.tagName.toLowerCase() === 'a') {
    link = target as HTMLAnchorElement;
  } else {
    link = target.closest('a');
  }

  if (link && (link.hasAttribute('download') || /\.(pdf|docx?|xlsx?|zip|rar|jpg|jpeg|png|gif|mp4|mp3|txt|csv)$/i.test(link.href))) {
    // Extraer nombre del archivo
    let fileName = link.getAttribute('download') || '';
    if (!fileName) {
      const urlParts = link.href.split('/');
      fileName = urlParts[urlParts.length - 1] || 'archivo_desconocido';
      fileName = fileName.split('?')[0];
    }
    // Consultar al backend antes de permitir la descarga
    const { jwt_token } = await chrome.storage.local.get('jwt_token');
    if (!jwt_token) return;
    const res = await fetch('http://localhost:5001/api/check-download', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwt_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url: link.href,
        filename: fileName,
        filesize: 0,
        mimetype: ''
      })
    });
    const data = await res.json();
    if (!data.allowed) {
      e.preventDefault();
      e.stopPropagation();
      // Redirigir a la pantalla de bloqueo personalizada
      window.location.href = chrome.runtime.getURL('blocked.html?url=' + encodeURIComponent(link.href));
      return false;
    }
  }
}, true);

// Interceptar descargas de blobs y descargas generadas por JavaScript
(function() {
  // Guardar referencias originales
  const originalCreateObjectURL = URL.createObjectURL;
  const originalWindowOpen = window.open;

  // Interceptar createObjectURL para blobs
  URL.createObjectURL = function(blob: Blob) {
    // Intentar obtener el nombre del archivo si existe
    let fileName = 'archivo_blob';
    if (blob && (blob as any).name) {
      fileName = (blob as any).name;
    }
    // Consultar al backend antes de permitir la descarga
    chrome.storage.local.get('jwt_token', async ({ jwt_token }) => {
      if (!jwt_token) return;
      const res = await fetch('http://localhost:5001/api/check-download', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${jwt_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: window.location.href,
          filename: fileName,
          filesize: blob.size,
          mimetype: blob.type
        })
      });
      const data = await res.json();
      if (!data.allowed) {
        // Redirigir a la pantalla de bloqueo personalizada
        window.location.href = chrome.runtime.getURL('blocked.html?url=' + encodeURIComponent(window.location.href));
        return '';
      }
    });
    return originalCreateObjectURL.apply(this, arguments as any);
  };

  // Interceptar window.open para descargas directas
  window.open = function(...args) {
    const url = args[0];
    if (typeof url === 'string' && /\.(pdf|docx?|xlsx?|zip|rar|jpg|jpeg|png|gif|mp4|mp3|txt|csv)$/i.test(url)) {
      chrome.storage.local.get('jwt_token', async ({ jwt_token }) => {
        if (!jwt_token) return;
        const res = await fetch('http://localhost:5001/api/check-download', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${jwt_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            url: url,
            filename: url.split('/').pop() || 'archivo_desconocido',
            filesize: 0,
            mimetype: ''
          })
        });
        const data = await res.json();
        if (!data.allowed) {
          window.location.href = chrome.runtime.getURL('blocked.html?url=' + encodeURIComponent(url));
          return null;
        }
      });
    }
    return originalWindowOpen.apply(this, args);
  };
})();

// Iniciar el script
initialize();