// Obtener la URL bloqueada de los parámetros
const urlParams = new URLSearchParams(window.location.search);
const blockedUrl = urlParams.get('url');

// Mostrar la URL bloqueada
const blockedUrlElement = document.getElementById('blockedUrl');
if (blockedUrlElement && blockedUrl) {
  blockedUrlElement.textContent = blockedUrl;
} 