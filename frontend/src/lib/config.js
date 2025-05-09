/**
 * Configuración de entornos para Athos
 * 
 * Este archivo gestiona las URLs de API basadas en el entorno.
 * En desarrollo, apunta a localhost.
 * En producción, usa la URL de la API desplegada.
 */

const dev = {
  API_URL: 'http://localhost:5001'
};

const prod = {
  API_URL: 'https://api.getathos.com'  // URL de producción
};

// Detectar entorno de producción
const isProd = import.meta.env.PROD;

// Exportar la URL adecuada
export const API_URL = isProd ? prod.API_URL : dev.API_URL;

// Configuración de la API
export const API_URL_OLD = 'https://api.getathos.com'; 