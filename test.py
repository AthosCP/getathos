import requests
import json
import base64
from datetime import datetime
import time

# Configuración
BASE_URL = "http://api.getathos.com"  # Cambiar a api.getathos.com en producción
CREDENTIALS = {
    "email": "user.nicobrave@icloud.com",
    "password": "123"
}

# Headers comunes
headers = {
    "Content-Type": "application/json"
}

def decode_jwt_payload(token):
    """Decodifica el payload de un JWT token"""
    try:
        # Separar las partes del token
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Token JWT inválido")
        
        # Obtener el payload (segunda parte)
        payload = parts[1]
        
        # Agregar padding si es necesario
        missing_padding = len(payload) % 4
        if missing_padding:
            payload += '=' * (4 - missing_padding)
        
        # Decodificar base64
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded_payload = json.loads(decoded_bytes.decode('utf-8'))
        
        return decoded_payload
    except Exception as e:
        print(f"Error al decodificar JWT: {e}")
        return None

def test_login():
    print("\n=== Probando Login ===")
    try:
        response = requests.post(
            f"{BASE_URL}/api/login",
            json=CREDENTIALS,
            headers=headers,
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")
            return data.get("access_token")
        else:
            print(f"Error: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("Error: Timeout en la conexión")
        return None
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar al servidor")
        return None
    except Exception as e:
        print(f"Error en login: {e}")
        return None

def test_verify_session(token):
    print("\n=== Probando Verificación de Sesión ===")
    
    # Decodificar el token para obtener el user_id
    payload = decode_jwt_payload(token)
    if not payload:
        print("No se pudo decodificar el token JWT")
        return
    
    user_id = payload.get('sub') or payload.get('user_id')
    if not user_id:
        print("No se encontró user_id en el token")
        print(f"Payload del token: {payload}")
        return
    
    print(f"User ID extraído del token: {user_id}")
    
    # Crear headers con autorización
    auth_headers = headers.copy()
    auth_headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/users/{user_id}",
            headers=auth_headers,
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("Error: Timeout en la verificación de sesión")
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar al servidor")
    except Exception as e:
        print(f"Error en verificación de sesión: {e}")

def test_events(token):
    print("\n=== Probando Registro de Eventos ===")
    
    # Crear headers con autorización
    auth_headers = headers.copy()
    auth_headers["Authorization"] = f"Bearer {token}"
    
    # Evento de copia
    copy_event = {
        "url": "https://ejemplo.com",
        "domain": "ejemplo.com",
        "event_type": "copy",
        "event_details": {
            "tipo_evento": "copy",
            "elemento_target": {
                "tag": "selection",
                "text": "texto de prueba"
            },
            "texto": "texto de prueba",
            "timestamp": datetime.now().isoformat(),
            "url_origen": "https://ejemplo.com"
        },
        "tab_title": "Página de ejemplo",
        "time_on_page": 60,
        "open_tabs_count": 3,
        "tab_focused": True
    }
    
    test_single_event("Evento de copia", copy_event, auth_headers)
    
    # Evento de descarga
    download_event = {
        "url": "https://ejemplo.com/archivo.pdf",
        "domain": "ejemplo.com",
        "event_type": "download",
        "event_details": {
            "tipo_evento": "download",
            "elemento_target": {
                "tag": "a",
                "href": "https://ejemplo.com/archivo.pdf",
                "text": "Descargar PDF"
            },
            "nombre_archivo": "archivo.pdf",
            "timestamp": datetime.now().isoformat(),
            "url_origen": "https://ejemplo.com"
        },
        "tab_title": "Página de ejemplo",
        "time_on_page": 60,
        "open_tabs_count": 3,
        "tab_focused": True
    }
    
    test_single_event("Evento de descarga", download_event, auth_headers)
    
    # Evento de impresión
    print_event = {
        "url": "https://ejemplo.com",
        "domain": "ejemplo.com",
        "event_type": "print",
        "event_details": {
            "tipo_evento": "print",
            "elemento_target": {
                "tag": "window"
            },
            "timestamp": datetime.now().isoformat(),
            "url_origen": "https://ejemplo.com"
        },
        "tab_title": "Página de ejemplo",
        "time_on_page": 60,
        "open_tabs_count": 3,
        "tab_focused": True
    }
    
    test_single_event("Evento de impresión", print_event, auth_headers)
    
    # Evento de click
    click_event = {
        "url": "https://ejemplo.com",
        "domain": "ejemplo.com",
        "event_type": "click",
        "event_details": {
            "tipo_evento": "click",
            "elemento_target": {
                "tag": "button",
                "id": "submit-btn",
                "class": "btn btn-primary",
                "text": "Enviar"
            },
            "timestamp": datetime.now().isoformat(),
            "url_origen": "https://ejemplo.com"
        },
        "tab_title": "Página de ejemplo",
        "time_on_page": 60,
        "open_tabs_count": 3,
        "tab_focused": True
    }
    
    test_single_event("Evento de click", click_event, auth_headers)
    
    # Evento de file upload
    upload_event = {
        "url": "https://ejemplo.com/upload",
        "domain": "ejemplo.com",
        "event_type": "file_upload",
        "event_details": {
            "tipo_evento": "file_upload",
            "elemento_target": {
                "tag": "input",
                "id": "file-input",
                "class": "form-control"
            },
            "nombre_archivo": "documento.pdf",
            "timestamp": datetime.now().isoformat(),
            "url_origen": "https://ejemplo.com/upload"
        },
        "tab_title": "Subir archivo",
        "time_on_page": 120,
        "open_tabs_count": 2,
        "tab_focused": True
    }
    
    test_single_event("Evento de file upload", upload_event, auth_headers)

def test_single_event(event_name, event_data, auth_headers):
    """Función auxiliar para probar un evento individual"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/navigation_logs",
            json=event_data,
            headers=auth_headers,
            timeout=10
        )
        print(f"\n{event_name}:")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"Error: Timeout en {event_name}")
    except requests.exceptions.ConnectionError:
        print(f"Error: No se pudo conectar al servidor para {event_name}")
    except Exception as e:
        print(f"Error en {event_name}: {e}")

def test_get_events(token):
    print("\n=== Probando Obtención de Eventos ===")
    
    # Crear headers con autorización
    auth_headers = headers.copy()
    auth_headers["Authorization"] = f"Bearer {token}"
    
    try:
        # Obtener eventos de riesgo
        response = requests.get(
            f"{BASE_URL}/api/navigation_logs/riesgo",
            headers=auth_headers,
            timeout=10
        )
        print("\nEventos de riesgo:")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Número de eventos obtenidos: {len(data) if isinstance(data, list) else 'N/A'}")
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
            
        # Obtener estadísticas de navegación
        response = requests.get(
            f"{BASE_URL}/api/navigation_logs/stats",
            headers=auth_headers,
            timeout=10
        )
        print("\nEstadísticas de navegación:")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("Error: Timeout al obtener eventos")
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar al servidor")
    except Exception as e:
        print(f"Error al obtener eventos: {e}")

def main():
    print("=== INICIANDO PRUEBAS DE API ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Usuario: {CREDENTIALS['email']}")
    
    try:
        # Login y obtener token
        token = test_login()
        if not token:
            print("\n❌ Error: No se pudo obtener el token. Abortando pruebas.")
            return
        
        print(f"\n✅ Token obtenido exitosamente")
        print(f"Token (primeros 50 caracteres): {token[:50]}...")
        
        # Esperar un momento para asegurar que el token se procese
        time.sleep(1)
        
        # Verificar sesión
        test_verify_session(token)
        
        # Probar eventos
        test_events(token)
        
        # Obtener eventos
        test_get_events(token)
        
        print("\n=== PRUEBAS COMPLETADAS ===")
        
    except KeyboardInterrupt:
        print("\n\nPruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()