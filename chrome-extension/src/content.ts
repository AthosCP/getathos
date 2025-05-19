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
function sendEventToBackground(eventData: any) {
    console.log("[Athos] Enviando evento al background:", eventData);
    try {
        chrome.runtime.sendMessage({
            type: 'user_interaction',
            ...eventData
        }, (response) => {
            if (chrome.runtime.lastError) {
                console.warn("[Athos] Error al enviar mensaje:", chrome.runtime.lastError.message);
                // Intentar reconectar si el contexto es inválido
                if (chrome.runtime.lastError.message.includes("Extension context invalidated")) {
                    console.log("[Athos] Intentando reconectar...");
                    setTimeout(() => {
                        sendEventToBackground(eventData);
                    }, 1000); // Reintentar después de 1 segundo
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
            }, 1000); // Reintentar después de 1 segundo
        }
    }
}

// Variable para controlar el estado de autenticación
let isAuthenticated = false;

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
  window.removeEventListener('beforeprint', printHandler);
}

// Manejador de clicks
function clickHandler(event: MouseEvent) {
    const target = event.target as HTMLElement;
    const elementInfo = getElementInfo(target);
    
    const eventData: UserInteractionEvent = {
        tipo_evento: 'click',
        elemento_target: elementInfo,
        timestamp: new Date().toISOString(),
        url_origen: window.location.href,
        texto: target.textContent?.trim().substring(0, 100) || null
    };
    
    console.log('[Athos] Evento de click capturado:', eventData);
    sendEventToBackground(eventData);
}

// Manejador de copia
function copyHandler(event: ClipboardEvent) {
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

function changeHandler(e: Event) {
  if (!isAuthenticated) return;
  const target = e.target as HTMLInputElement;
  if (target.type === 'file') {
    const files = Array.from(target.files || []);
    files.forEach(file => {
      chrome.runtime.sendMessage({
        type: 'user_interaction',
        data: {
          tipo_evento: 'file_upload',
          elemento_target: getElementInfo(target),
          nombre_archivo: file.name,
          timestamp: new Date().toISOString(),
          url_origen: window.location.href
        }
      });
    });
  }
}

function cutHandler() {
  if (!isAuthenticated) return;
  const selection = window.getSelection();
  const text = selection?.toString().substring(0, 100);
  chrome.runtime.sendMessage({
    type: 'user_interaction',
    data: {
      tipo_evento: 'cut',
      elemento_target: {
        tag: 'selection',
        text: text
      },
      timestamp: new Date().toISOString(),
      url_origen: window.location.href
    }
  });
}

function printHandler() {
  if (!isAuthenticated) return;
  chrome.runtime.sendMessage({
    type: 'user_interaction',
    data: {
      tipo_evento: 'print',
      elemento_target: { tag: 'window' },
      timestamp: new Date().toISOString(),
      url_origen: window.location.href
    }
  });
}

// Agregar listeners
function addAllListeners() {
  document.addEventListener('click', clickHandler);
  document.addEventListener('copy', copyHandler);
  document.addEventListener('paste', pasteHandler);
  document.addEventListener('change', changeHandler);
  document.addEventListener('cut', cutHandler);
  window.addEventListener('beforeprint', printHandler);
}

// Inicialización
async function initialize() {
  await checkAuth();
  if (isAuthenticated) {
    addAllListeners();
  }
}

// Escuchar cambios en el storage
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.jwt_token) {
    checkAuth().then(() => {
      if (isAuthenticated) {
        addAllListeners();
      }
    });
  }
});

// Iniciar
initialize();

// Mensaje de inicialización
console.log('Athos Content Script: Monitoreo de interacciones activo'); 