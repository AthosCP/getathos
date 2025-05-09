/**
 * Configuración de entornos para Athos
 * 
 * Este archivo gestiona las URLs de API basadas en el entorno.
 * En desarrollo, apunta a localhost.
 * En producción, usa la URL de la API desplegada en Render.
 */

const dev = {
  API_URL: 'http://localhost:5001'
};

const prod = {
  API_URL: 'https://api.getathos.com'
};

// Determine if we're in a production environment
const isProd = import.meta.env.PROD || window.location.hostname === 'getathos.com';

// Export the configuration based on environment
export const API_URL = isProd ? prod.API_URL : dev.API_URL;

// Configuración de la API
export const API_URL_OLD = 'https://api.getathos.com'; 