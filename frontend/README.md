# Athos Cybersecurity Platform

Plataforma integral de ciberseguridad para empresas, que incluye:
- **Frontend**: Aplicación web en SvelteKit
- **Backend**: API en Flask (Python)
- **Extensión de Chrome**: Control y monitoreo de navegación
- **Integración con Supabase**: Autenticación, base de datos y almacenamiento

---

## Estructura del proyecto

```
Athos/
├── backend/                # API Flask
├── frontend/               # App SvelteKit (este README)
├── chrome-extension/       # Extensión de Chrome (código fuente)
│   └── dist/               # Build final de la extensión
├── admin-panel/            # (opcional, panel antiguo o experimental)
```

---

## Instalación y desarrollo local

### 1. Backend (Flask)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
- El backend corre en `http://localhost:5001`
- Variables de entorno necesarias: `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET_KEY`

### 2. Frontend (SvelteKit)
```bash
cd frontend
npm install
npm run dev
```
- El frontend corre en `http://localhost:5173` o `:4173`
- Variables de entorno necesarias en `.env` (claves de Supabase):
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`

---

## Build y Deploy

### Frontend en Render
- El root del servicio debe ser la carpeta `frontend/`
- Comando de build: `npm install && npm run build`
- Comando de start: `npm run preview`
- El archivo `vite.config.js` NO debe excluir `@supabase/supabase-js` del bundle

### Backend en Render
- Comando de start: `python app.py` (el backend detecta el puerto de Render automáticamente)
- CORS configurado para aceptar peticiones de local y producción

---

## Extensión de Chrome

- El código fuente está en `chrome-extension/`
- El build final está en `chrome-extension/dist/`
- Para publicar:
  1. Entra a `chrome-extension/dist/`
  2. Crea un ZIP con todo el contenido de esa carpeta
  3. Sube el ZIP a la Chrome Web Store
- El `manifest.json` debe tener:
  - `"name": "Athos Cybersecurity Platform"`
  - `host_permissions` con URLs de backend local y producción

---

## Integración con Supabase
- Se usa para autenticación, base de datos y almacenamiento de archivos (logos, etc.)
- La instancia de Supabase se centraliza en `frontend/src/lib/supabaseClient.js`
- El backend usa la clave de servicio para operaciones administrativas

---

## Contacto y soporte
- Para dudas, soporte o contribuciones, contacta a: [nicobrave@icloud.com](mailto:nicobrave@icloud.com)

---

## Notas adicionales
- El proyecto está listo para desarrollo local y despliegue en producción sin fricción
- El frontend y backend detectan el entorno automáticamente
- La extensión puede comunicarse tanto con el backend local como con el de producción
