# Athos Web Control - Extensión Chrome

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