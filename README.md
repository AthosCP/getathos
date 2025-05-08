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
