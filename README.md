# Athos Web Control

Extensión de Chrome para el control y monitoreo de navegación web en organizaciones.

## Funcionalidades Principales

### 1. Control de Navegación
- Bloqueo de dominios prohibidos
- Políticas por categoría
- Notificaciones de bloqueo
- Registro de intentos de acceso

### 2. Captura de Eventos

#### Navegación
- URL visitada
- Dominio
- Título de la pestaña
- Tiempo en página
- Número de pestañas abiertas
- Estado de foco de la pestaña
- IP del usuario
- User Agent

#### Interacciones del Usuario
- Clicks
  - Elemento clickeado (tag, id, clase)
  - Texto del elemento
  - URL de origen
  - Timestamp

- Copiar/Pegar
  - Texto seleccionado/copiado
  - Elemento destino
  - URL de origen
  - Timestamp

- Descargas
  - Nombre del archivo
  - Tamaño
  - Tipo MIME
  - URL de origen
  - Timestamp

- Carga de Archivos
  - Nombre del archivo
  - Elemento de carga
  - URL de origen
  - Timestamp

#### Sesión
- Login
  - Email del usuario
  - Timestamp
  - IP
  - User Agent

- Logout
  - Tipo (voluntario/forzado)
  - URL de origen
  - Timestamp
  - Tiempo total de sesión

### 3. Cálculo de Riesgo
- Puntuación basada en:
  - Tipo de interacción
  - Contenido sensible
  - Archivos descargados/subidos
  - Dominios visitados
  - Patrones de comportamiento

## Estructura de Datos

### Navigation Logs
```typescript
interface NavigationEvent {
  domain: string;
  url: string;
  action: string;
  timestamp: string;
  ip_address?: string;
  user_agent: string;
  tab_title: string;
  time_on_page: number;
  open_tabs_count: number;
  tab_focused: boolean;
  event_type: 'navegacion' | 'formulario' | 'descarga' | 'bloqueo';
  event_details: Record<string, any>;
  risk_score: number;
}
```

### User Interactions
```typescript
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
```

## Arquitectura

### Content Script
- Captura eventos del usuario
- Envía mensajes al background script
- No tiene acceso directo al backend

### Background Script
- Maneja la lógica principal
- Comunica con el backend
- Gestiona políticas y bloqueos
- Registra eventos

### Popup
- Interfaz de usuario
- Login/Logout
- Estado de protección

## Permisos Requeridos
- `storage`: Para guardar token y políticas
- `tabs`: Para monitorear navegación
- `webNavigation`: Para detectar cambios de URL
- `webRequest`: Para interceptar peticiones
- `downloads`: Para monitorear descargas
- `notifications`: Para alertas de bloqueo

## Desarrollo

### Requisitos
- Node.js
- TypeScript
- Chrome Extension Manifest V3

### Build
```bash
npm install
npm run build
```

### Testing
1. Cargar la extensión en Chrome
2. Iniciar sesión con credenciales válidas
3. Navegar y verificar logs en el backend

## Próximas Mejoras
1. Dashboard de actividad
2. Alertas en tiempo real
3. Políticas más granulares
4. Análisis de comportamiento
5. Exportación de logs

# Athos - Control de Navegación Web

Plataforma SaaS para el control y seguridad de navegación web, permitiendo a las empresas gestionar y monitorear el acceso a sitios web de sus empleados.

Sitio oficial: [getathos.com](https://getathos.com)

## Características

- 🔒 **Control de Navegación**: Bloqueo de sitios web no deseados
- 📊 **Monitoreo en Tiempo Real**: Seguimiento detallado de actividad web
- 👥 **Multitenant**: Sistema completo de gestión para múltiples clientes
- 🌐 **Extensión Chrome**: Integración directa con el navegador
- 📱 **Responsive**: Interfaz adaptable a cualquier dispositivo

## Estructura del Proyecto

```
athos/
├── backend/           # API Flask (Python)
├── frontend/          # Aplicación Svelte
└── chrome-extension/  # Extensión de Chrome
```

## Requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Supabase (para autenticación y BD)

## Desarrollo Local

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # o `venv\Scripts\activate` en Windows
pip install -r requirements.txt
flask run --debug --port 5001
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Extensión Chrome
```bash
cd chrome-extension
npm install
npm run dev  # Para desarrollo
npm run build  # Para crear build de producción
```

## Despliegue

Este proyecto está configurado para desplegarse automáticamente en [Render](https://render.com) utilizando el archivo `render.yaml`.

### Pasos para desplegar

1. Crea una cuenta en Render.com
2. Conecta tu repositorio de GitHub
3. Crea un nuevo Blueprint utilizando este repositorio
4. Configura las variables de entorno necesarias (ver `render.yaml`)
5. ¡Listo! Render se encargará del resto

## Licencia

Este proyecto está bajo la Licencia MIT.

---

© 2025 Athos - [getathos.com](https://getathos.com)