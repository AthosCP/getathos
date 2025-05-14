interface UserInteractionEvent {
  tipo_evento: 'click' | 'copy' | 'paste' | 'download' | 'file_upload';
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

// Listener para clics
document.addEventListener('click', (e) => {
  const target = e.target as Element;
  sendEventToBackground({
    tipo_evento: 'click',
    elemento_target: getElementInfo(target),
    timestamp: new Date().toISOString(),
    url_origen: window.location.href
  });
});

// Listener para copiar
document.addEventListener('copy', () => {
  const selection = window.getSelection();
  chrome.runtime.sendMessage({
    type: 'user_interaction',
    data: {
      tipo_evento: 'copy',
      elemento_target: {
        tag: 'selection',
        text: selection?.toString().substring(0, 100)
      },
      timestamp: new Date().toISOString(),
      url_origen: window.location.href
    }
  });
});

// Listener para pegar
document.addEventListener('paste', (e) => {
  const target = e.target as Element;
  chrome.runtime.sendMessage({
    type: 'user_interaction',
    data: {
      tipo_evento: 'paste',
      elemento_target: getElementInfo(target),
      timestamp: new Date().toISOString(),
      url_origen: window.location.href
    }
  });
});

// Listener para descargas
document.addEventListener('click', (e) => {
  const target = e.target as Element;
  const anchor = target.closest('a');
  if (anchor && anchor.hasAttribute('download')) {
    chrome.runtime.sendMessage({
      type: 'user_interaction',
      data: {
        tipo_evento: 'download',
        elemento_target: getElementInfo(anchor),
        nombre_archivo: anchor.getAttribute('download') || undefined,
        timestamp: new Date().toISOString(),
        url_origen: window.location.href
      }
    });
  }
});

// Listener para carga de archivos
document.addEventListener('change', (e) => {
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
});

// Mensaje de inicialización
console.log('Athos Content Script: Monitoreo de interacciones activo'); 