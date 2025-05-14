# Athos Chrome Extension

Extensión de Chrome para el control y monitoreo de navegación web en organizaciones.

## Datos Capturados

### 1. Navegación
- URL visitada
- Dominio
- Título de la pestaña
- Tiempo en página (actualizado cada 5 minutos)
- Número de pestañas abiertas
- Estado de foco de la pestaña
- IP del usuario
- User Agent

### 2. Interacciones del Usuario
- **Clicks**
  - Elemento clickeado (tag, id, clase)
  - Texto del elemento
  - URL de origen
  - Timestamp

- **Copiar/Pegar**
  - Texto seleccionado/copiado
  - Elemento destino
  - URL de origen
  - Timestamp

- **Descargas**
  - Nombre del archivo
  - Tamaño
  - Tipo MIME
  - URL de origen
  - Timestamp

- **Carga de Archivos**
  - Nombre del archivo
  - Elemento de carga
  - URL de origen
  - Timestamp

### 3. Sesión
- **Login**
  - Email del usuario
  - Timestamp
  - IP
  - User Agent

- **Logout**
  - Tipo (voluntario/forzado)
  - URL de origen
  - Timestamp
  - Tiempo total de sesión

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

## Componentes

### Content Script (`content.ts`)
- Captura eventos del usuario en la página
- Envía mensajes al background script
- No tiene acceso directo al backend
- Eventos capturados:
  - Clicks
  - Copiar/Pegar
  - Descargas
  - Carga de archivos

### Background Script (`background.ts`)
- Maneja la lógica principal
- Comunica con el backend
- Gestiona políticas y bloqueos
- Registra eventos
- Funcionalidades:
  - Control de navegación
  - Cálculo de riesgo
  - Gestión de timers
  - Registro de eventos

### Popup (`popup.ts`)
- Interfaz de usuario
- Login/Logout
- Estado de protección
- Funcionalidades:
  - Autenticación
  - Estado de sesión
  - Cierre de sesión

## Permisos
- `storage`: Token y políticas
- `tabs`: Monitoreo de navegación
- `webNavigation`: Cambios de URL
- `webRequest`: Interceptación de peticiones
- `downloads`: Monitoreo de descargas
- `notifications`: Alertas de bloqueo

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

## Estructura del proyecto

```
chrome-extension/
├── public/
│   ├── manifest.json
│   ├── blocked.html
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
├── src/
│   ├── background.ts
│   ├── popup.html
│   ├── popup.ts
│   └── blocked.ts
├── dist/           # Se genera tras el build
├── popup.css
├── vite.config.ts
├── package.json
└── ...
```

## Flujo de build y desarrollo

1. **El código fuente está en `src/`**
   - El background script principal es `src/background.ts`.
   - El popup y la página de bloqueo (`blocked.html`) están en `src/` y/o `public/`.

2. **El build se realiza con Vite**
   - El archivo de entrada para el background es `src/background.ts` (no uses ni copies un background.js viejo).
   - El archivo de entrada para el popup es `src/popup.html`.
   - El archivo de entrada para la página de bloqueo es `public/blocked.html`.

3. **El manifest debe apuntar a `background.js` generado en `dist/`**
   - Ejemplo:
     ```json
     "background": {
       "service_worker": "background.js",
       "type": "module"
     }
     ```

4. **NO uses ni copies un background.js viejo en la raíz**
   - Si existe un archivo `background.js` en la raíz, bórralo. Solo debe existir el generado por el build.

5. **Para compilar y probar:**
   ```bash
   rm -rf dist
   npm run build
   # Luego instala la extensión desde la carpeta dist/ en Chrome
   ```

6. **Si ves errores de DNR o funciones viejas:**
   - Borra cualquier archivo background.js viejo.
   - Asegúrate de que el build apunte a `src/background.ts`.
   - Haz un build limpio y reinstala la extensión.

## Troubleshooting

- **¿Ves la página de bloqueo nativa de Chrome?**
  - Asegúrate de NO tener reglas DNR ni referencias a `setupBlockingRules` o `updateDynamicRules`.
  - Elimina el permiso `declarativeNetRequest` del manifest.

- **¿No se redirige a blocked.html?**
  - Verifica que el dominio esté en las políticas bloqueadas.
  - Asegúrate de que el background script esté corriendo y que el manifest apunte al archivo correcto.

- **¿El build falla diciendo que falta background.js?**
  - Corrige la entrada en `vite.config.ts` para que apunte a `src/background.ts`.

## Resumen

- El background script debe compilarse SIEMPRE desde `src/background.ts`.
- No debe haber archivos background.js viejos en la raíz.
- El manifest y el build deben estar alineados con la estructura real del proyecto.

---

¿Dudas? Contacta a soporte Athos o revisa este README antes de modificar la estructura del build. 