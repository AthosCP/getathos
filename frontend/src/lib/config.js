/**
 * Configuración de entornos para Athos
 * 
 * Este archivo gestiona las URLs de API basadas en el entorno.
 * En desarrollo, apunta a localhost.
 * En producción, usa la URL de la API desplegada en Render.
 */

const dev = {
  apiUrl: 'http://localhost:5001',
  siteUrl: 'http://localhost:5173'
};

const prod = {
  apiUrl: 'https://api.getathos.com', // URL de la API en producción
  siteUrl: 'https://getathos.com'     // URL del sitio en producción
};

// Determine if we're in a production environment
const isProd = import.meta.env.PROD || window.location.hostname === 'getathos.com';

// Export the appropriate config based on environment
export default isProd ? prod : dev; 