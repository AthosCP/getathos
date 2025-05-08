# Guía de Despliegue para Athos

Esta guía detalla el proceso para desplegar Athos en [Render](https://render.com) y configurar el dominio personalizado [getathos.com](https://getathos.com).

## Prerequisitos

1. Cuenta en [Render.com](https://render.com)
2. Repositorio en GitHub conectado a Render
3. Dominio personalizado (getathos.com) y acceso a su configuración DNS
4. Proyecto Supabase para autenticación y base de datos

## Despliegue en Render

### 1. Configuración en Render

1. Inicia sesión en [Render Dashboard](https://dashboard.render.com)
2. Selecciona "Blueprints" en el panel lateral
3. Haz clic en "New Blueprint Instance"
4. Selecciona el repositorio de GitHub que contiene tu proyecto Athos
5. Render detectará automáticamente el archivo `render.yaml` y mostrará los servicios a crear
6. Configura las variables de entorno (ver paso siguiente)
7. Haz clic en "Apply" para iniciar el despliegue

### 2. Variables de Entorno

Deberás configurar las siguientes variables de entorno:

**Para el servicio Backend (athos-api)**:
- `SUPABASE_URL`: URL de tu proyecto Supabase
- `SUPABASE_KEY`: Clave `service_role` de tu proyecto Supabase (¡nunca uses esta clave en el frontend!)
- `JWT_SECRET_KEY`: Clave secreta para la generación de tokens JWT (Render puede generar esta automáticamente)

**Para el servicio Frontend (athos-frontend)**:
- `PUBLIC_API_URL`: URL del servicio backend (se configura automáticamente)

### 3. Configuración del Dominio Personalizado

#### Para el Frontend:

1. Ve al servicio "athos-frontend" en tu dashboard de Render
2. Selecciona la pestaña "Settings" y luego "Custom Domain"
3. Haz clic en "Add Custom Domain"
4. Ingresa "getathos.com" y sigue las instrucciones para verificar la propiedad del dominio
5. Configura un registro CNAME en tu proveedor DNS apuntando a tu dominio de Render

#### Para el Backend:

1. Ve al servicio "athos-api" en tu dashboard de Render
2. Selecciona la pestaña "Settings" y luego "Custom Domain"
3. Haz clic en "Add Custom Domain"
4. Ingresa "api.getathos.com" y sigue las instrucciones
5. Configura un registro CNAME en tu proveedor DNS

### 4. Configuración de Supabase

1. En tu proyecto Supabase, configura las URLs permitidas para autenticación:
   - Añade "https://getathos.com" a "Site URL"
   - Añade "https://getathos.com/*" a "Redirect URLs"
   
2. Configure CORS en Supabase para permitir solicitudes desde:
   - https://getathos.com
   - https://api.getathos.com 
   - chrome-extension://*

## Verificación del Despliegue

Una vez completado el despliegue, verifica:

1. Que puedes acceder a la aplicación en https://getathos.com
2. Que la API responde en https://api.getathos.com
3. Que puedes registrar usuarios y acceder con ellos
4. Que la extensión de Chrome puede comunicarse con la API

## Solución de Problemas

### Problema: La extensión no se comunica con la API
- Verifica que estás usando la URL correcta en `config.js`
- Asegúrate de que CORS está correctamente configurado en el backend

### Problema: Errores 401 en la API
- Verifica que el `JWT_SECRET_KEY` es el mismo que se está utilizando en el backend
- Comprueba que los tokens JWT se generan y transmiten correctamente

### Problema: Errores de base de datos
- Verifica las políticas RLS en Supabase
- Comprueba que las migraciones de base de datos se han aplicado correctamente

## Actualizaciones

Para actualizar la aplicación, simplemente haz push de tus cambios al repositorio de GitHub. Render detectará automáticamente los cambios y los desplegará. 