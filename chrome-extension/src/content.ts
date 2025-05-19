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

// Función para obtener información del elemento target
function getElementInfo(element: Element): { tag: string; id?: string; class?: string; text?: string } {
  return {
    tag: element.tagName.toLowerCase(),
    id: element.id || undefined,
    class: element.className || undefined,
    text: element.textContent?.trim().substring(0, 100) || undefined
  };
}

// Función para enviar evento al background script
function sendEventToBackground(event: UserInteractionEvent) {
  chrome.runtime.sendMessage({
    type: 'user_interaction',
    data: event
  });
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

// Handlers para los eventos
function clickHandler(e: MouseEvent) {
  if (!isAuthenticated) return;
  const target = e.target as Element;
  sendEventToBackground({
    tipo_evento: 'click',
    elemento_target: getElementInfo(target),
    timestamp: new Date().toISOString(),
    url_origen: window.location.href
  });
}

function copyHandler() {
  if (!isAuthenticated) return;
  const selection = window.getSelection();
  const text = selection?.toString().substring(0, 100);
  chrome.runtime.sendMessage({
    type: 'user_interaction',
    data: {
      tipo_evento: 'copy',
      elemento_target: {
        tag: 'selection',
        text: text
      },
      timestamp: new Date().toISOString(),
      url_origen: window.location.href
    }
  });
}

function pasteHandler(e: ClipboardEvent) {
  if (!isAuthenticated) return;
  const target = e.target as Element;
  let pastedText = '';
  if (e.clipboardData) {
    pastedText = e.clipboardData.getData('text').substring(0, 100);
  }
  chrome.runtime.sendMessage({
    type: 'user_interaction',
    data: {
      tipo_evento: 'paste',
      elemento_target: getElementInfo(target),
      pasted_text: pastedText,
      timestamp: new Date().toISOString(),
      url_origen: window.location.href
    }
  });
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