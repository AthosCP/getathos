# Variables de Entorno

Este documento describe las variables de entorno necesarias para ejecutar el proyecto Athos.

## Supabase
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_ANON_KEY=your_supabase_anon_key
```

## Backend
```
FLASK_SECRET_KEY=your_flask_secret_key
FLASK_ENV=development
```

## Frontend
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

## Extensión
```
PLASMO_PUBLIC_SUPABASE_URL=your_supabase_url
PLASMO_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

## Instrucciones

1. Copia este archivo como `.env` en cada directorio del proyecto (backend, admin-panel, extension)
2. Reemplaza los valores con tus credenciales reales
3. Asegúrate de que el archivo `.env` esté en el `.gitignore` 