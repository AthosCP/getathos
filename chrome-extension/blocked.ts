// Obtener la URL bloqueada de los parámetros
const urlParams = new URLSearchParams(window.location.search);
const blockedUrl = urlParams.get('url');

// Mostrar la URL bloqueada
const urlElement = document.getElementById('blockedUrl');
if (urlElement && blockedUrl) {
  urlElement.textContent = blockedUrl;
} 