/**
 * Configuración de entornos para la Extensión Chrome de Athos
 * 
 * Este archivo gestiona las URLs de API basadas en el entorno.
 * En desarrollo, apunta a localhost.
 * En producción, usa la URL de la API desplegada en Render.
 */

// Environments configuration
const environments = {
  development: {
    API_URL: 'http://localhost:5001',
  },
  production: {
    API_URL: 'https://api.getathos.com',
  }
};

// Set current environment
const ENVIRONMENT = process.env.NODE_ENV === 'production' ? 'production' : 'development';

// Export configuration for current environment
module.exports = environments[ENVIRONMENT]; 