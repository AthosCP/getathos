from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from uuid import UUID
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token, get_jwt, verify_jwt_in_request
from supabase.lib.client_options import ClientOptions
import json # Importar json
import requests
from urllib.parse import urlparse
import hashlib
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Cargar variables de entorno
load_dotenv()

# Cargar sitios prohibidos desde el archivo JSON
def load_prohibited_sites():
    try:
        print("[Backend] Iniciando carga de sitios prohibidos...")
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, 'prohibidos.json')
            print(f"[Backend] Ruta del archivo de sitios prohibidos: {json_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                categories = json.load(f)
                print(f"[Backend] Se cargaron {len(categories)} categorías de sitios prohibidos")
                return categories
        except FileNotFoundError:
            print(f"[Backend] Archivo no encontrado: {json_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"[Backend] Error al decodificar el archivo JSON: {str(e)}")
            return {}
    except Exception as e:
        print(f"[Backend] Error en load_prohibited_sites: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

prohibited_sites = load_prohibited_sites()

# Función para verificar una URL usando Google Web Risk API
def check_url_with_webrisk(url):
    try:
        # Normalizar el dominio
        domain = normalize_domain(url)
        if not domain:
            return False, "URL inválida"

        # Obtener el token JWT y claims
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not jwt_token:
            return False, "No autorizado"

        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        user_id = claims.get('user_id')

        # Obtener conexión a Supabase
        user_supabase = get_supabase_with_jwt(jwt_token)

        # 1. Verificar políticas específicas del tenant y grupos
        if role == 'user':
            # Obtener grupos del usuario
            user_groups_res = user_supabase.table('group_users').select('group_id').eq('user_id', user_id).execute()
            user_groups = [g['group_id'] for g in user_groups_res.data] if user_groups_res.data else []
            
            # Ejecutar consultas separadas y combinar resultados
            # Primero obtenemos las políticas del tenant sin grupo
            tenant_policies = user_supabase.table('policies').select('*')\
                .eq('tenant_id', tenant_id)\
                .is_('group_id', 'null')\
                .eq('domain', domain)\
                .eq('type', 'access')\
                .execute()
            
            group_policies = None
            if user_groups:
                # Luego obtenemos las políticas de los grupos del usuario
                group_policies = user_supabase.table('policies').select('*')\
                    .in_('group_id', user_groups)\
                    .eq('domain', domain)\
                    .eq('type', 'access')\
                    .execute()
            
            # Combinamos los resultados
            policies_data = tenant_policies.data
            if group_policies and group_policies.data:
                policies_data += group_policies.data
        else:
            # Para otros roles, simplemente filtramos por tenant_id
            policies = user_supabase.table('policies').select('*')\
                .eq('tenant_id', tenant_id)\
                .eq('domain', domain)\
                .execute()
            policies_data = policies.data

        if policies_data:
            # Si hay políticas específicas, usar la más restrictiva
            for policy in policies_data:
                if policy['action'] == 'block':
                    return True, "Dominio bloqueado por política"
            return False, None

        # 2. Verificar configuración del tenant
        tenant_config = user_supabase.table('tenant_configs').select('*').eq('tenant_id', tenant_id).maybe_single().execute()
        
        if tenant_config.data:
            config = tenant_config.data
            if domain in config.get('blocked_domains', []):
                return True, "Dominio bloqueado por configuración del tenant"
            if domain in config.get('allowed_domains', []):
                return False, None

        # 3. Verificar lista global de sitios prohibidos
        prohibited_sites = load_prohibited_sites()
        if domain in prohibited_sites:
            return True, "Dominio en lista global de sitios prohibidos"

        return False, None

    except Exception as e:
        print(f"Error en check_url_with_webrisk: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e)

    except Exception as e:
        print(f"Error en check_url_with_webrisk: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def normalize_domain(domain):
    """
    Normaliza un dominio o URL para extraer el dominio base.
    Ejemplos:
    - https://www.example.com -> example.com
    - http://sub.example.com -> sub.example.com
    - www.example.com -> example.com
    - example.com -> example.com
    """
    try:
        # Si es una URL completa, extraer el dominio
        if '://' in domain:
            domain = domain.split('://')[1]
        
        # Eliminar www. si existe
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Eliminar cualquier ruta o parámetros después del dominio
        domain = domain.split('/')[0]
        
        # Eliminar cualquier puerto
        domain = domain.split(':')[0]
        
        return domain.lower().strip()
    except Exception as e:
        print(f"[Backend] Error al normalizar dominio {domain}: {str(e)}")
        return domain.lower().strip()

app = Flask(__name__)
# Configuración de JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Token nunca expira
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'
jwt = JWTManager(app)

print("JWT_SECRET_KEY:", app.config['JWT_SECRET_KEY'])

# Configuración de Flask-Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]  # No hay límite global, solo por endpoint
)

# Middleware para verificar token
@app.before_request
def verify_token():
    if request.endpoint and 'static' not in request.endpoint:
        try:
            if request.headers.get('Authorization'):
                verify_jwt_in_request()
        except Exception as e:
            if request.endpoint not in ['login', 'register']:
                return jsonify({"success": False, "error": "Token inválido o expirado"}), 401

# Configuración más permisiva de CORS para desarrollo y producción
CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": [
            "http://localhost:5173",
            "http://localhost:4173",
            "https://athos-frontend.onrender.com",
            "https://getathos.com",
            "https://www.getathos.com",
            "chrome-extension://*"  # Permitir todas las extensiones de Chrome
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Configurar headers de seguridad
@app.after_request
def add_security_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:* http://127.0.0.1:*; style-src 'self' 'unsafe-inline';"
    return response

# Configuración de Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def get_supabase_with_jwt(jwt_token):
    options = ClientOptions()
    options.headers["Authorization"] = f"Bearer {jwt_token}"
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
        options=options
    )

def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({"success": False, "error": "No autorizado"}), 403
        return fn(*args, **kwargs)
    return wrapper

def athos_owner_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'athos_owner':
            return jsonify({"success": False, "error": "No autorizado"}), 403
        return fn(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    return jsonify({
        "name": "Athos API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/login",
            "config": "/api/config",
            "tenants": "/api/tenants",
            "users": "/api/users"
        }
    })

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")  # Limita a 5 intentos por minuto por IP
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        print("[Backend] Intentando login para:", email)
        
        # Autenticación con Supabase
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if hasattr(response, 'session') and response.session:
            # Crear token JWT personalizado
            tenant_id = response.user.user_metadata.get('tenant_id')
            role = response.user.user_metadata.get('role')
            user_id = response.user.id

            print(f"[Backend] Login exitoso - User ID: {user_id}, Role: {role}, Tenant: {tenant_id}")

            # Si es admin y no tiene tenant_id, usar None o un valor especial
            if role == 'admin' and not tenant_id:
                # Para admin, podemos usar None o un valor especial como "admin"
                tenant_id = None  # o "admin" o un UUID específico

            # Crear el diccionario de claims
            claims = {
                "email": response.user.email,
                "role": role,
                "tenant_id": tenant_id,
                "supabase_token": response.session.access_token
            }
            
            # Imprimir para depuración
            print(f"[Backend] User metadata: {response.user.user_metadata}")
            print(f"[Backend] Generated JWT claims: {claims}")
            
            # Crear el token con los claims
            access_token = create_access_token(
                identity=user_id,  # Esto establecerá el campo 'sub' en el JWT
                additional_claims=claims
            )
            
            print("[Backend] Token JWT generado exitosamente")
            
            return jsonify({
                "success": True,
                "access_token": access_token,
                "user": response.user.email,
                "user_id": user_id,
                "role": role
            })
        else:
            print("[Backend] Login fallido - Credenciales inválidas")
            return jsonify({
                "success": False,
                "error": "Credenciales inválidas"
            }), 401
    except Exception as e:
        print(f"[Backend] Error en login: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 401

@app.route('/api/config', methods=['GET'])
@jwt_required()
def get_config():
    claims = get_jwt()
    email = claims.get('email')
    role = claims.get('role')
    tenant_id = claims.get('tenant_id')
    # Configuración por defecto
    default_config = {
        "extension_enabled": False,
        "blocked_domains": [],
        "allowed_domains": [],
        "user": {
            "email": email,
            "role": role
        }
    }
    # Intentar obtener la configuración del tenant si existe
    if tenant_id:
        config = supabase.table('tenant_configs').select('*').eq('tenant_id', tenant_id).execute()
        if config.data:
            return jsonify({"success": True, "data": {**default_config, **config.data[0]}})
    return jsonify({"success": True, "data": default_config})

@app.route('/api/tenants', methods=['GET'])
def get_tenants():
    try:
        # ASUMIMOS QUE ESTE ENDPOINT ES PARA UN ROL QUE BYPASSEA RLS o tiene una política muy permisiva
        # O DEBERÍA SER PROTEGIDO Y USAR user_supabase
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No token provided"}), 401

        # Esta validación de rol 'superadmin' es la original, pero 'superadmin' no es un rol que tengamos definido en JWT actualmente.
        # Considerar cambiar a athos_owner_required o admin_required si este endpoint se usa.
        # user = supabase.auth.get_user(auth_header.split(' ')[1]) 
        # role = user.user.user_metadata.get('role')
        # if role != 'superadmin': 
        #     return jsonify({"error": "Unauthorized"}), 403

        # Si se usa el cliente global supabase, y este usa service_role_key, RLS es bypassada.
        tenants = supabase.table('tenants').select('*').execute() 
        return jsonify({
            "success": True,
            "data": tenants.data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 401

@app.route('/api/tenants', methods=['POST'])
def create_tenant():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No token provided"}), 401

        user = supabase.auth.get_user(auth_header.split(' ')[1])
        if user.user.user_metadata.get('role') != 'admin':
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json()
        tenant = supabase.table('tenants').insert({
            'name': data.get('name'),
            'description': data.get('description')
        }).execute()

        return jsonify({
            "success": True,
            "data": tenant.data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 401

@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        print(f"GET /api/users - Claims: {claims}")

        if role == 'admin':
            # Admin global ve todos los usuarios (sujeto a RLS "Admin acceso total a users")
            users_query = user_supabase.table('users').select('*')
        elif role == 'client':
            # Cliente ve solo usuarios de su tenant con rol 'user'
            users_query = user_supabase.table('users').select('*').eq('tenant_id', tenant_id).eq('role', 'user')
        else:
            return jsonify({"error": "Rol no autorizado para ver usuarios"}), 403
        
        users = users_query.execute()
        print(f"GET /api/users - Usuarios encontrados: {len(users.data)}")
        return jsonify({"success": True, "data": users.data})
    except Exception as e:
        print(f"=== ERROR en admin_get_users ===")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje de error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/users/<user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    claims = get_jwt()
    role = claims.get('role')
    tenant_id = claims.get('tenant_id')
    supabase_token = claims.get('supabase_token')
    jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_supabase = get_supabase_with_jwt(jwt_token)
    user_data = user_supabase.table('users').select('*').eq('id', user_id).execute()
    if not user_data.data:
        return jsonify({"error": "Usuario no encontrado"}), 404
    target_user = user_data.data[0]
    if role == 'admin':
        pass
    elif role == 'client':
        if target_user.get('tenant_id') != tenant_id and claims['sub'] != user_id:
            return jsonify({"error": "No autorizado"}), 403
    elif claims['sub'] != user_id:
        return jsonify({"error": "No autorizado"}), 403
    return jsonify({"success": True, "data": target_user})

@app.route('/api/users', methods=['POST'])
@jwt_required()
def create_user():
    try:
        claims = get_jwt()
        requesting_role = claims.get('role')
        requesting_tenant_id = claims.get('tenant_id')
        data = request.get_json()

        # Validar datos requeridos
        if not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email y password son requeridos"}), 400

        # Validar rol solicitado
        requested_role = data.get('role', 'user')
        if requested_role not in ['user', 'client', 'admin', 'athos_owner']:
            return jsonify({"error": "Rol inválido"}), 400

        # Validar permisos según rol del solicitante
        if requesting_role == 'athos_owner':
            # Athos owner puede crear cualquier rol
            pass
        elif requesting_role == 'admin':
            # Admin puede crear users, clients y otros admins en su mismo tenant
            if requested_role == 'athos_owner':
                return jsonify({"error": "No autorizado para crear usuarios athos_owner"}), 403
            # Asegurar que el nuevo admin pertenece al mismo tenant
            data['tenant_id'] = requesting_tenant_id
        elif requesting_role == 'client':
            # Client solo puede crear users
            if requested_role != 'user':
                return jsonify({"error": "Solo puede crear usuarios con rol 'user'"}), 403
            data['tenant_id'] = requesting_tenant_id
        else:
            return jsonify({"error": "No autorizado para crear usuarios"}), 403

        # Validar tenant_id según el rol
        if requesting_role == 'athos_owner':
            # Athos owner puede crear sin tenant_id para roles admin y athos_owner
            if requested_role in ['admin', 'athos_owner']:
                data['tenant_id'] = None
            elif not data.get('tenant_id'):
                return jsonify({"error": "tenant_id es requerido"}), 400

        # Obtener cliente autenticado
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Verificar límite de usuarios si aplica
        if data.get('tenant_id'):
            tenant = user_supabase.table('tenants').select('max_users').eq('id', data['tenant_id']).single().execute()
            if not tenant.data:
                return jsonify({"error": "Tenant no encontrado"}), 404
            
            current_users = user_supabase.table('users').select('id').eq('tenant_id', data['tenant_id']).execute()
            if len(current_users.data) >= tenant.data['max_users']:
                return jsonify({"error": f"Límite de usuarios alcanzado para este tenant"}), 400

        # Crear usuario en Auth
        auth_response = user_supabase.auth.admin.create_user({
            "email": data['email'],
            "password": data['password'],
            "email_confirm": True,
            "user_metadata": {
                "role": requested_role,
                "tenant_id": data.get('tenant_id')
            }
        })

        # Crear usuario en la tabla users
        user_data = {
            "id": auth_response.user.id,
            "email": data['email'],
            "role": requested_role,
            "tenant_id": data.get('tenant_id'),
            "status": "active",
            "created_at": datetime.utcnow().isoformat()
        }

        new_user = user_supabase.table('users').insert(user_data).execute()

        if not new_user.data:
            # Si falla la inserción, eliminar el usuario de Auth
            user_supabase.auth.admin.delete_user(auth_response.user.id)
            return jsonify({"error": "Error al crear usuario en la base de datos"}), 500

        # Actualizar contador de usuarios del tenant
        if data.get('tenant_id'):
            user_supabase.rpc('increment_users_count', {'tenant_id': data['tenant_id']}).execute()

        return jsonify({
            "success": True, 
            "data": new_user.data[0],
            "message": f"Usuario {requested_role} creado exitosamente"
        }), 201

    except Exception as e:
        print(f"Error en create_user: {str(e)}")
        # Si se creó el usuario en Auth pero falló algo más, intentar limpiar
        if 'auth_response' in locals():
            try:
                user_supabase.auth.admin.delete_user(auth_response.user.id)
            except:
                pass
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    try:
        claims = get_jwt()
        requesting_role = claims.get('role')
        requesting_tenant_id = claims.get('tenant_id')
        data = request.get_json()

        # Obtener cliente autenticado
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Obtener usuario actual
        current_user = user_supabase.table('users').select('*').eq('id', user_id).single().execute()
        if not current_user.data:
            return jsonify({"error": "Usuario no encontrado"}), 404

        current_user_data = current_user.data
        current_role = current_user_data.get('role')
        current_tenant_id = current_user_data.get('tenant_id')

        # Validar permisos según rol del solicitante
        if requesting_role == 'athos_owner':
            # Athos owner puede modificar cualquier usuario
            pass
        elif requesting_role == 'admin':
            # Admin solo puede modificar usuarios de su mismo tenant
            if str(current_tenant_id) != str(requesting_tenant_id):
                return jsonify({"error": "No autorizado para modificar usuarios de otros tenants"}), 403
            
            # Validar cambio de rol
            new_role = data.get('role')
            if new_role and new_role != current_role:
                if new_role == 'athos_owner':
                    return jsonify({"error": "No autorizado para asignar rol athos_owner"}), 403
                # Asegurar que el nuevo rol mantiene el mismo tenant
                data['tenant_id'] = requesting_tenant_id
        elif requesting_role == 'client':
            # Client solo puede modificar usuarios de su mismo tenant
            if str(current_tenant_id) != str(requesting_tenant_id):
                return jsonify({"error": "No autorizado para modificar usuarios de otros tenants"}), 403
            
            # Client no puede cambiar roles
            if 'role' in data:
                return jsonify({"error": "No autorizado para cambiar roles"}), 403
        else:
            return jsonify({"error": "No autorizado para modificar usuarios"}), 403

        # Preparar datos de actualización
        update_data = {}
        if 'email' in data:
            update_data['email'] = data['email']
        if 'role' in data:
            update_data['role'] = data['role']
        if 'tenant_id' in data:
            update_data['tenant_id'] = data['tenant_id']
        if 'status' in data:
            update_data['status'] = data['status']

        if not update_data:
            return jsonify({"error": "No hay datos para actualizar"}), 400

        # Actualizar usuario en la tabla users
        updated_user = user_supabase.table('users').update(update_data).eq('id', user_id).execute()

        if not updated_user.data:
            return jsonify({"error": "Error al actualizar usuario"}), 500

        # Actualizar metadatos en Auth si cambió el rol o tenant_id
        if 'role' in update_data or 'tenant_id' in update_data:
            try:
                user_supabase.auth.admin.update_user_by_id(user_id, {
                    'user_metadata': {
                        'role': update_data.get('role', current_role),
                        'tenant_id': update_data.get('tenant_id', current_tenant_id)
                    }
                })
            except Exception as e:
                print(f"Error actualizando metadatos en Auth: {str(e)}")
                # Continuar aunque falle la actualización de metadatos

        return jsonify({
            "success": True,
            "data": updated_user.data[0],
            "message": "Usuario actualizado exitosamente"
        })

    except Exception as e:
        print(f"Error en update_user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Solo admin puede eliminar cualquier usuario, client solo los de su tenant
        user_data = user_supabase.table('users').select('*').eq('id', user_id).execute()
        if not user_data.data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        target_user = user_data.data[0]

        if role == 'admin':
            pass
        elif role == 'client':
            if target_user.get('tenant_id') != tenant_id:
                return jsonify({"error": "No autorizado"}), 403
        else:
            return jsonify({"error": "No autorizado"}), 403

        # Primero eliminar de Supabase Auth
        try:
            user_supabase.auth.admin.delete_user(user_id)
        except Exception as e:
            print(f"Error eliminando en Supabase Auth: {str(e)}")
            return jsonify({"success": False, "error": f"Error eliminando en Auth: {str(e)}"}), 400

        # Si fue exitoso, eliminar de la tabla users
        user_supabase.table('users').delete().eq('id', user_id).execute()
        # Actualizar el conteo de usuarios del tenant
        user_supabase.table('tenants').update({
            'users_count': len(user_supabase.table('users').select('id').eq('tenant_id', tenant_id).execute().data)
        }).eq('id', tenant_id).execute()
        return jsonify({
            "success": True,
            "message": "Usuario eliminado correctamente"
        })
    except Exception as e:
        print(f"Error en delete_user: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        print(f"Intentando registrar usuario: {email}")
        
        # Registrar usuario en Supabase
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        print(f"Respuesta de registro: {response}")
        
        if hasattr(response, 'user'):
            return jsonify({
                "success": True,
                "message": "Usuario registrado exitosamente",
                "user": response.user.email
            })
        else:
            return jsonify({
                "success": False,
                "error": "Error al registrar usuario"
            }), 400
    except Exception as e:
        print(f"Error en registro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

# --- ENDPOINTS DE POLÍTICAS ---
@app.route('/api/policies', methods=['GET'])
@jwt_required()
def get_policies():
    try:
        print("[Backend] Iniciando obtención de políticas...")
        claims = get_jwt()
        print("[Backend] Claims del JWT:", claims)
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        user_id = claims.get('sub')  # Usar el campo sub como user_id
        print(f"[Backend] Usuario: {user_id}, Rol: {role}, Tenant: {tenant_id}")

        if not user_id:
            print("[Backend] ERROR: sub (user_id) es None en los claims")
            return jsonify({"success": False, "error": "user_id no encontrado en el token"}), 401

        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Nuevo: filtrar por type (access por defecto)
        policy_type = request.args.get('type', 'access')

        # Obtener políticas según el rol
        if role == 'user':
            print("[Backend] Obteniendo políticas para usuario normal")
            try:
                # Obtener grupos del usuario
                print(f"[Backend] Consultando grupos para user_id: {user_id}")
                user_groups_res = user_supabase.table('group_users').select('group_id').eq('user_id', user_id).execute()
                print(f"[Backend] Respuesta de grupos: {user_groups_res}")
                user_groups = [g['group_id'] for g in user_groups_res.data] if user_groups_res.data else []
                print(f"[Backend] Grupos del usuario: {user_groups}")

                # Obtener políticas del tenant sin grupo
                tenant_policies = user_supabase.table('policies').select('*').eq('tenant_id', tenant_id).is_('group_id', 'null').eq('type', policy_type).execute()
                print(f"[Backend] Políticas del tenant: {len(tenant_policies.data)} encontradas")

                # Obtener políticas de los grupos del usuario
                group_policies = []
                if user_groups:
                    group_policies = user_supabase.table('policies').select('*').in_('group_id', user_groups).eq('type', policy_type).execute().data
                    print(f"[Backend] Políticas de grupos: {len(group_policies)} encontradas")

                # Combinar políticas
                all_policies = tenant_policies.data + group_policies
                print(f"[Backend] Total de políticas: {len(all_policies)}")

                # Obtener información de grupos para las políticas
                group_ids = [p['group_id'] for p in all_policies if p.get('group_id')]
                group_info = {}
                if group_ids:
                    groups_res = user_supabase.table('groups').select('id, name').in_('id', group_ids).execute()
                    group_info = {g['id']: g for g in groups_res.data}

                # Procesar políticas
                processed_policies = []
                for policy in all_policies:
                    processed_policy = {
                        'id': policy['id'],
                        'domain': policy.get('domain'),
                        'action': policy['action'],
                        'category': policy.get('category'),
                        'block_reason': policy.get('block_reason'),
                        'group_id': policy.get('group_id'),
                        'group': group_info.get(policy.get('group_id')),
                        'user_id': policy.get('user_id'),
                        'type': policy.get('type', 'access')
                    }
                    processed_policies.append(processed_policy)

                print(f"[Backend] Políticas procesadas exitosamente: {len(processed_policies)}")
                return jsonify({"success": True, "data": processed_policies})

            except Exception as e:
                print(f"[Backend] Error al obtener políticas para usuario: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({"success": False, "error": str(e)}), 500

        else:  # Para client y admin
            print("[Backend] Obteniendo políticas para rol administrativo")
            # Para client y admin, obtener todas las políticas del tenant con información de grupos
            policies = user_supabase.table('policies').select('*, groups(name)').eq('tenant_id', tenant_id).eq('type', policy_type).execute()
            print(f"[Backend] Políticas encontradas para tenant: {len(policies.data)}")
            
            # Debug: imprimir la primera política para ver qué campos vienen
            if policies.data:
                print(f"[Backend] Ejemplo de política recibida: {policies.data[0]}")
            
            # Procesar las políticas para incluir la información del grupo
            processed_policies = []
            for policy in policies.data:
                processed_policy = {
                    'id': policy['id'],
                    'domain': policy.get('domain'),
                    'action': policy['action'],
                    'category': policy.get('category'),
                    'block_reason': policy.get('block_reason'),
                    'group_id': policy.get('group_id'),
                    'group': policy.get('groups'),
                    'user_id': policy.get('user_id'),
                    'type': policy.get('type', 'access')
                }
                if processed_policy['group'] is None:
                    del processed_policy['group']
                processed_policies.append(processed_policy)
            
            return jsonify({"success": True, "data": processed_policies})

    except Exception as e:
        print(f"[Backend] Error en get_policies: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/policies', methods=['POST'])
@jwt_required()
def create_policy():
    try:
        claims = get_jwt()
        role = claims.get('role')
        requesting_tenant_id = claims.get('tenant_id')
        data = request.get_json()
        
        print("[Backend] Iniciando creación de política...")
        print("[Backend] Datos recibidos:", data)
        print("[Backend] Claims JWT:", claims)
        
        if not data:
            print("[Backend] Error: No se recibieron datos en el request")
            return jsonify({"success": False, "error": "No se recibieron datos en el request"}), 400
        
        policy_tenant_id = None
        group_id = data.get('group_id')
        policy_type = data.get('type', 'access')
        user_id = data.get('user_id')

        print(f"[Backend] Tipo de política: {policy_type}")
        print(f"[Backend] User ID: {user_id}")
        print(f"[Backend] Group ID: {group_id}")

        if role == 'client':
            if not requesting_tenant_id:
                print("[Backend] Error: Cliente sin tenant_id")
                return jsonify({"success": False, "error": "Cliente debe tener un tenant_id asociado"}), 403
            policy_tenant_id = requesting_tenant_id
            if group_id:
                jwt_token_client = request.headers.get('Authorization', '').replace('Bearer ', '')
                client_supabase = get_supabase_with_jwt(jwt_token_client)
                group_check = client_supabase.table('groups').select('id, tenant_id').eq('id', group_id).eq('tenant_id', policy_tenant_id).maybe_single().execute()
                if not group_check.data:
                    print("[Backend] Error: Grupo no encontrado o no pertenece al tenant del cliente")
                    return jsonify({"success": False, "error": "Grupo no encontrado o no pertenece al tenant del cliente"}), 400
        elif role == 'admin':
            policy_tenant_id = data.get('tenant_id')
            if not policy_tenant_id:
                print("[Backend] Error: Admin debe especificar tenant_id")
                return jsonify({"success": False, "error": "Admin debe especificar tenant_id"}), 400
            if group_id:
                jwt_token_admin = request.headers.get('Authorization', '').replace('Bearer ', '')
                admin_supabase = get_supabase_with_jwt(jwt_token_admin)
                group_check = admin_supabase.table('groups').select('id, tenant_id').eq('id', group_id).eq('tenant_id', policy_tenant_id).maybe_single().execute()
                if not group_check.data:
                    print("[Backend] Error: Grupo no encontrado o no pertenece al tenant especificado")
                    return jsonify({"success": False, "error": "Grupo no encontrado o no pertenece al tenant_id especificado"}), 400
        else:
            print("[Backend] Error: Rol no autorizado")
            return jsonify({"success": False, "error": "No autorizado para crear políticas"}), 403
            
        if not policy_tenant_id:
            print("[Backend] Error: Política sin tenant")
            return jsonify({"success": False, "error": "La política debe estar asociada a un tenant"}), 400

        if data.get('action') not in ['allow', 'block']:
            print("[Backend] Error: Acción inválida")
            return jsonify({"success": False, "error": "Acción inválida"}), 400
        if policy_type not in ['access', 'download']:
            print("[Backend] Error: Tipo de política inválido")
            return jsonify({"success": False, "error": "Tipo de política inválido"}), 400
        if policy_type == 'access' and not data.get('domain'):
            print("[Backend] Error: Dominio requerido para políticas de acceso")
            return jsonify({"success": False, "error": "Dominio requerido para políticas de acceso"}), 400
        
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        insert_data = {
            'action': data['action'],
            'tenant_id': policy_tenant_id,
            'type': policy_type
        }
        
        if group_id:
            insert_data['group_id'] = group_id
        if policy_type == 'access':
            insert_data['domain'] = data['domain']
        if policy_type == 'download':
            if user_id:
                insert_data['user_id'] = user_id
            if group_id:
                insert_data['group_id'] = group_id
        
        print("[Backend] Datos a insertar en policies:", insert_data)
        
        try:
            new_policy_res = user_supabase.table('policies').insert(insert_data).execute()
            print("[Backend] Respuesta de Supabase:", new_policy_res)
        except Exception as e:
            print(f"[Backend] Error al insertar en Supabase: {str(e)}")
            return jsonify({"success": False, "error": f"Error al crear la política en la base de datos: {str(e)}"}), 500

        if not new_policy_res.data or (hasattr(new_policy_res, 'error') and new_policy_res.error):
            error_detail = new_policy_res.error.message if hasattr(new_policy_res, 'error') and new_policy_res.error else "No data returned"
            print(f"[Backend] Error al crear política en Supabase: {error_detail}")
            return jsonify({"success": False, "error": f"No se pudo crear la política: {error_detail}"}), 500
        
        print("[Backend] Política creada exitosamente")
        return jsonify({"success": True, "data": new_policy_res.data[0]}), 201
        
    except Exception as e:
        print(f"[Backend] Error en create_policy: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Error interno del servidor: {str(e)}"}), 500

@app.route('/api/policies/<policy_id_str>', methods=['PUT']) # Usar policy_id_str
@jwt_required()
def update_policy(policy_id_str): # Usar policy_id_str
    try:
        claims = get_jwt()
        role = claims.get('role')
        requesting_tenant_id = claims.get('tenant_id')
        
        try:
            policy_id = UUID(policy_id_str, version=4)
        except ValueError:
            return jsonify({"success": False, "error": "Formato de policy_id inválido."}), 400

        data = request.get_json()
        print(f"Intentando actualizar política {policy_id} con datos: {data}")
        
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        current_policy_res = user_supabase.table('policies').select('id, tenant_id, group_id, type').eq('id', policy_id).maybe_single().execute()
        if not current_policy_res.data:
            return jsonify({"error": "Política no encontrada"}), 404
        
        current_policy = current_policy_res.data
        current_policy_tenant_id = current_policy.get('tenant_id')
        current_policy_type = current_policy.get('type', 'access')

        if role == 'client':
            if not requesting_tenant_id or str(current_policy_tenant_id) != str(requesting_tenant_id):
                return jsonify({"error": "No autorizado para modificar esta política (cliente)"}), 403
        elif role == 'admin':
            pass
        else:
            return jsonify({"error": "No autorizado para modificar políticas"}), 403
        
        update_payload = {}
        if 'domain' in data and data['domain'] is not None:
            update_payload['domain'] = data['domain']
        if 'action' in data and data['action'] is not None:
            if data['action'] not in ['allow', 'block']:
                return jsonify({"error": "Acción inválida"}), 400
            update_payload['action'] = data['action']
        if 'type' in data and data['type'] in ['access', 'download']:
            update_payload['type'] = data['type']
        new_group_id = data.get('group_id')
        new_tenant_id_str = data.get('tenant_id')
        final_policy_tenant_id_str = current_policy_tenant_id
        if role == 'admin' and new_tenant_id_str is not None and new_tenant_id_str != str(current_policy_tenant_id):
            try:
                UUID(new_tenant_id_str, version=4)
                final_policy_tenant_id_str = new_tenant_id_str
                update_payload['tenant_id'] = final_policy_tenant_id_str
            except ValueError:
                 return jsonify({"error": "Formato de nuevo tenant_id inválido."}), 400
        if new_group_id is not None:
            if not final_policy_tenant_id_str:
                 return jsonify({"error": "Se requiere un tenant_id para asociar la política a un grupo."}),400
            try:
                parsed_new_group_id = UUID(new_group_id, version=4)
                group_check = user_supabase.table('groups').select('id, tenant_id').eq('id', parsed_new_group_id).eq('tenant_id', final_policy_tenant_id_str).maybe_single().execute()
                if not group_check.data:
                    return jsonify({"error": f"Nuevo grupo {new_group_id} no encontrado o no pertenece al tenant {final_policy_tenant_id_str}"}), 400
                update_payload['group_id'] = str(parsed_new_group_id)
                update_payload['tenant_id'] = str(group_check.data['tenant_id'])
            except ValueError:
                return jsonify({"error": "Formato de nuevo group_id inválido."}), 400
        elif 'group_id' in data and data['group_id'] is None:
            update_payload['group_id'] = None
            if not final_policy_tenant_id_str and role == 'admin':
                 return jsonify({"error": "Admin debe especificar un tenant_id si se desasocia la política de un grupo y no tenía uno antes."}), 400
            update_payload['tenant_id'] = final_policy_tenant_id_str
        if 'user_id' in data:
            update_payload['user_id'] = data['user_id']
        if not update_payload:
            current_policy_full_res = user_supabase.table('policies').select('*, groups(name)').eq('id', policy_id).maybe_single().execute()
            if current_policy_full_res.data:
                 processed_policy = current_policy_full_res.data
                 if processed_policy.get('groups') is not None:
                    processed_policy['group'] = processed_policy.pop('groups')
                    if processed_policy['group'] is None: del processed_policy['group']
                 elif 'groups' in processed_policy: del processed_policy['groups']
                 return jsonify({"success": True, "data": processed_policy, "message": "No changes detected"}), 200
            else:
                 return jsonify({"error": "Política no encontrada al final del proceso."}), 404
        print("Payload de actualización para policies:", update_payload)
        updated_policy_res = user_supabase.table('policies').update(update_payload).eq('id', policy_id).select('*, groups(name)').maybe_single().execute()
        if not updated_policy_res.data or (hasattr(updated_policy_res, 'error') and updated_policy_res.error):
            error_detail = updated_policy_res.error.message if hasattr(updated_policy_res, 'error') and updated_policy_res.error else "No data returned"
            print(f"Error al actualizar política en Supabase: {error_detail}")
            return jsonify({"success": False, "error": f"No se pudo actualizar la política: {error_detail}"}), 500
        processed_updated_policy = updated_policy_res.data
        if processed_updated_policy.get('groups') is not None:
            processed_updated_policy['group'] = processed_updated_policy.pop('groups')
            if processed_updated_policy['group'] is None: del processed_updated_policy['group']
        elif 'groups' in processed_updated_policy: del processed_updated_policy['groups']
        return jsonify({"success": True, "data": processed_updated_policy})
    except Exception as e:
        print(f"Error en update_policy: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/policies/<policy_id_str>', methods=['DELETE']) # Usar policy_id_str
@jwt_required()
def delete_policy(policy_id_str): # Usar policy_id_str
    try:
        claims = get_jwt()
        role = claims.get('role')
        requesting_tenant_id = claims.get('tenant_id')
        
        try:
            policy_id = UUID(policy_id_str, version=4)
        except ValueError:
            return jsonify({"success": False, "error": "Formato de policy_id inválido."}), 400

        print(f"DELETE /api/policies/{policy_id} - JWT claims: {claims}")
        print(f"Role: {role}, Tenant ID: {requesting_tenant_id}")
        
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        policy_res = user_supabase.table('policies').select('id, tenant_id').eq('id', policy_id).maybe_single().execute()
        
        if not policy_res.data:
            return jsonify({"error": "Política no encontrada"}), 404
            
        target_policy = policy_res.data
        target_policy_tenant_id = target_policy.get('tenant_id')
        
        if role == 'admin':
            print("Usuario es admin, puede eliminar cualquier política (RLS dependiente)")
            pass # RLS se encargará de si puede o no eliminar.
        elif role == 'client':
            print(f"Usuario es client, verificando tenant_id: {requesting_tenant_id} vs política: {target_policy_tenant_id}")
            if not requesting_tenant_id or str(target_policy_tenant_id) != str(requesting_tenant_id):
                return jsonify({"error": "No autorizado para eliminar esta política"}), 403
        else: # Otros roles
            print(f"Rol no autorizado: {role}")
            return jsonify({"error": "No autorizado para eliminar políticas"}), 403
            
        deleted_res = user_supabase.table('policies').delete().eq('id', policy_id).execute()

        # Supabase delete no devuelve error si no se borra nada por RLS, pero `deleted_res.data` estará vacío.
        # O si la RLS lo impide, puede lanzar un error que es capturado por el try-except general.
        if hasattr(deleted_res, 'error') and deleted_res.error:
            print(f"Error al eliminar política en Supabase: {deleted_res.error.message}")
            return jsonify({"success": False, "error": f"Error al eliminar política: {deleted_res.error.message}"}), 500
        
        # Podríamos chequear deleted_res.data para ver si algo fue realmente borrado,
        # pero si la RLS previene, el error debería ser capturado.
        # Si el ID no existe, el `policy_res` anterior ya lo hubiera detectado.

        print(f"Política eliminada o intento de eliminación para: {policy_id}")
        return jsonify({"success": True, "message": "Política eliminada correctamente"})
    except Exception as e:
        error_msg = str(e)
        print(f"Error en delete_policy: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": error_msg}), 400

# --- ENDPOINTS DE HISTORIAL DE NAVEGACIÓN ---
@app.route('/api/navigation_logs', methods=['GET'])
@jwt_required()
def get_navigation_logs():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        # Filtros
        user_id = request.args.get('user_id')
        domain = request.args.get('domain')
        url = request.args.get('url')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        action = request.args.get('action')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        autocomplete = request.args.get('autocomplete')  # 'domain' o 'url'
        autocomplete_query = request.args.get('q', '')

        base_query = user_supabase.table('navigation_logs').select('*')
        if role == 'admin':
            pass
        elif role == 'client':
            base_query = base_query.eq('tenant_id', tenant_id)
        else:
            return jsonify({"error": "No autorizado"}), 403
        if user_id:
            base_query = base_query.eq('user_id', user_id)
        if domain:
            base_query = base_query.ilike('domain', f'%{domain}%')
        if url:
            base_query = base_query.ilike('url', f'%{url}%')
        if date_from:
            base_query = base_query.gte('timestamp', date_from)
        if date_to:
            base_query = base_query.lte('timestamp', date_to)
        if action and action != 'all':
            base_query = base_query.eq('action', action)

        # Autocompletado
        if autocomplete == 'domain':
            ac_query = user_supabase.table('navigation_logs').select('domain').distinct('domain')
            if role == 'client':
                ac_query = ac_query.eq('tenant_id', tenant_id)
            if autocomplete_query:
                ac_query = ac_query.ilike('domain', f'%{autocomplete_query}%')
            ac_domains = ac_query.limit(10).execute()
            domains = [row['domain'] for row in ac_domains.data]
            return jsonify({"success": True, "suggestions": domains})
        if autocomplete == 'url':
            ac_query = user_supabase.table('navigation_logs').select('url').distinct('url')
            if role == 'client':
                ac_query = ac_query.eq('tenant_id', tenant_id)
            if autocomplete_query:
                ac_query = ac_query.ilike('url', f'%{autocomplete_query}%')
            ac_urls = ac_query.limit(10).execute()
            urls = [row['url'] for row in ac_urls.data]
            return jsonify({"success": True, "suggestions": urls})

        # Total de registros filtrados
        count_query = user_supabase.table('navigation_logs').select('id', count='exact')
        if role == 'client':
            count_query = count_query.eq('tenant_id', tenant_id)
        if user_id:
            count_query = count_query.eq('user_id', user_id)
        if domain:
            count_query = count_query.ilike('domain', f'%{domain}%')
        if url:
            count_query = count_query.ilike('url', f'%{url}%')
        if date_from:
            count_query = count_query.gte('timestamp', date_from)
        if date_to:
            count_query = count_query.lte('timestamp', date_to)
        if action and action != 'all':
            count_query = count_query.eq('action', action)
        count_result = count_query.execute()
        total = count_result.count if hasattr(count_result, 'count') else len(count_result.data)

        # Paginación y datos
        from_idx = (page - 1) * page_size
        to_idx = from_idx + page_size - 1
        data_query = base_query.order('timestamp', desc=True).range(from_idx, to_idx)
        logs = data_query.execute()
        return jsonify({"success": True, "data": logs.data, "total": total, "page": page, "page_size": page_size})
    except Exception as e:
        print(f"Error en get_navigation_logs: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

def verify_policies(domain, tenant_id, role, user_id=None):
    try:
        print(f"[Backend] Verificando políticas para tenant_id: {tenant_id}, role: {role}, user_id: {user_id}")
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        # Cargar sitios prohibidos
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prohibidos_path = os.path.join(current_dir, 'prohibidos.json')
        with open(prohibidos_path, 'r', encoding='utf-8') as f:
            prohibited_sites = json.load(f)
        # Verificar si el dominio está en la lista de prohibidos
        domain = domain.lower()
        for category, sites in prohibited_sites.items():
            for site in sites:
                if site in domain:
                    return {
                        'action': 'bloqueado',
                        'info': {
                            'category': category,
                            'block_reason': f'Sitio bloqueado por {category}'
                        }
                    }
        # Si no hay user_id, solo verificar políticas globales
        if not user_id:
            policies = user_supabase.table('policies').select('*').eq('tenant_id', tenant_id).is_('group_id', 'null').eq('type', 'access').execute()
            for policy in policies.data:
                if policy['domain'] in domain:
                    return {
                        'action': policy['action'],
                        'info': {
                            'category': policy.get('category', 'sin categoría'),
                            'block_reason': policy.get('block_reason', 'Bloqueado por política personalizada')
                        }
                    }
            return {'action': 'permitido', 'info': None}
        # Si hay user_id, verificar políticas específicas del usuario
        user_groups_res = user_supabase.table('group_users').select('group_id').eq('user_id', user_id).execute()
        user_groups = [group['group_id'] for group in user_groups_res.data]
        # Verificar políticas globales primero
        global_policies = user_supabase.table('policies').select('*').eq('tenant_id', tenant_id).is_('group_id', 'null').eq('type', 'access').execute()
        for policy in global_policies.data:
            if policy['domain'] in domain:
                return {
                    'action': policy['action'],
                    'info': {
                        'category': policy.get('category', 'sin categoría'),
                        'block_reason': policy.get('block_reason', 'Bloqueado por política personalizada')
                    }
                }
        # Luego verificar políticas de grupos
        if user_groups:
            group_policies = user_supabase.table('policies').select('*').eq('tenant_id', tenant_id).in_('group_id', user_groups).eq('type', 'access').execute()
            for policy in group_policies.data:
                if policy['domain'] in domain:
                    return {
                        'action': policy['action'],
                        'info': {
                            'category': policy.get('category', 'sin categoría'),
                            'block_reason': policy.get('block_reason', 'Bloqueado por política personalizada')
                        }
                    }
        return {'action': 'permitido', 'info': None}
    except Exception as e:
        print(f"[Backend] Error al verificar políticas: {str(e)}")
        return {'action': 'bloqueado', 'info': {'category': 'error', 'block_reason': 'Error al verificar políticas'}}

@app.route('/api/navigation_logs', methods=['POST'])
@jwt_required()
def create_navigation_log():
    try:
        print("[Backend] Iniciando registro de navegación...")
        data = request.get_json()
        print(f"[Backend] Datos recibidos: {data}")
        
        # Obtener claims del token JWT
        claims = get_jwt()
        tenant_id = claims.get('tenant_id')
        role = claims.get('role')
        user_id = claims.get('sub')  # sub es el user_id en el token JWT
        
        if not tenant_id:
            return jsonify({"success": False, "error": "No se encontró tenant_id en el token"}), 400
            
        # Normalizar el dominio
        url = data.get('url', '')
        domain = normalize_domain(url)
        
        # Verificar políticas
        print(f"[Backend] Verificando políticas para dominio: {url}")
        policy_result = verify_policies(domain, tenant_id, role, user_id)
        print(f"[Backend] Resultado de verify_policies: {policy_result}")
        action = policy_result.get('action', 'visitado')
        # Mapear acciones a los valores aceptados por la base de datos
        action_map = {
            'block': 'bloqueado',
            'bloqueo': 'bloqueado',
            'allow': 'permitido',
            'permitir': 'permitido',
            'visit': 'visitado',
            'visitado': 'visitado',
            'interact': 'interaccion',
            'interaccion': 'interaccion'
        }
        action = action_map.get(action, action)
        policy_info = policy_result.get('info', {})
        if isinstance(policy_info, dict):
            policy_info = json.dumps(policy_info)
        else:
            policy_info = json.dumps({'block_reason': policy_info})
        
        # Preparar datos del log
        log_data = {
            'user_id': user_id,
            'tenant_id': tenant_id,
            'domain': url,
            'url': url,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': action,
            'policy_info': policy_info,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'tab_title': data.get('tab_title'),
            'time_on_page': data.get('time_on_page'),
            'open_tabs_count': data.get('open_tabs_count'),
            'tab_focused': data.get('tab_focused'),
            'event_type': data.get('event_type', 'navegacion'),
            'event_details': data.get('event_details', {}),
            'risk_score': calculate_risk_score(data.get('event_type', 'navegacion'), data.get('event_details', {})),
            'city': data.get('city'),
            'country': data.get('country')
        }
        
        print(f"[Backend] Registrando log con datos: {log_data}")
        
        # Registrar el log
        user_supabase = get_supabase_with_jwt(request.headers.get('Authorization', '').replace('Bearer ', ''))
        result = user_supabase.table('navigation_logs').insert(log_data).execute()
        
        print("[Backend] Log registrado exitosamente")
        return jsonify({"success": True, "data": result.data})
        
    except Exception as e:
        print(f"[Backend] Error al registrar log: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

def calculate_risk_score(event_type: str, event_details: dict) -> int:
    """Calcula el puntaje de riesgo basado en el tipo de evento y sus detalles"""
    base_scores = {
        'navegacion': 10,
        'click': 15,
        'copy': 25,
        'paste': 25,
        'download': 35,
        'file_upload': 35,
        'cut': 25,
        'print': 30
    }
    
    score = base_scores.get(event_type, 10)
    
    # Ajustar score basado en detalles específicos
    if event_details:
        if event_type in ['copy', 'paste', 'cut']:
            text = event_details.get('texto', '')
            if text and len(text) > 100:  # Texto largo
                score += 10
        elif event_type in ['download', 'file_upload']:
            filename = event_details.get('nombre_archivo', '')
            if filename:
                ext = filename.split('.')[-1].lower()
                if ext in ['doc', 'docx', 'pdf', 'xls', 'xlsx']:  # Archivos sensibles
                    score += 15
    
    return min(score, 100)  # Máximo 100

@app.route('/api/navigation_logs/block', methods=['POST'])
@jwt_required()
def block_domain():
    try:
        data = request.get_json()
        domain = data.get('domain')
        
        # Obtener claims del token JWT
        claims = get_jwt()
        tenant_id = claims.get('tenant_id')
        
        # Obtener el token JWT para pasar a Supabase
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        if not domain:
            return jsonify({'success': False, 'error': 'Dominio requerido'}), 400
            
        # Verificar si el dominio ya está en la lista de bloqueados
        existing_query = user_supabase.table('policies').select('*')
        if tenant_id:
            existing_query = existing_query.eq('tenant_id', tenant_id)
        existing_query = existing_query.eq('domain', domain).eq('action', 'block')
        existing = existing_query.execute()
        
        if existing.data:
            return jsonify({'success': False, 'error': 'El dominio ya está bloqueado'}), 400
            
        # Crear nueva política de bloqueo
        new_policy = user_supabase.table('policies').insert({
            'tenant_id': tenant_id,
            'domain': domain,
            'action': 'block',
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        return jsonify({
            'success': True,
            'message': f'Dominio {domain} bloqueado exitosamente'
        })
        
    except Exception as e:
        print(f"Error en block_domain: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-download', methods=['POST'])
@jwt_required()
def check_download():
    """
    Verifica si un usuario puede descargar archivos según las políticas configuradas.
    Recibe: { url, filename, filesize, mimetype }
    Retorna: { allowed: bool, reason: string }
    """
    try:
        data = request.get_json()
        url = data.get('url', '')
        filename = data.get('filename', '')
        
        # Obtener claims del token JWT
        claims = get_jwt()
        tenant_id = claims.get('tenant_id')
        role = claims.get('role')
        user_id = claims.get('sub')
        
        print(f"[Backend] Verificando descarga - Usuario: {user_id}, Archivo: {filename}, URL: {url}")
        
        # Obtener conexión a Supabase
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        # Por defecto, permitir descargas
        allowed = True
        reason = "Descarga permitida"
        
        # 1. Verificar políticas globales del tenant (sin user_id ni group_id)
        global_policies = user_supabase.table('policies').select('*')\
            .eq('tenant_id', tenant_id)\
            .is_('user_id', 'null')\
            .is_('group_id', 'null')\
            .eq('type', 'download')\
            .execute()
        
        print(f"[Backend] Políticas globales encontradas: {len(global_policies.data)}")
        if global_policies.data:
            print(f"[Backend] Políticas globales: {global_policies.data}")
            for policy in global_policies.data:
                if policy['action'] == 'block':
                    allowed = False
                    reason = "Descargas bloqueadas por política global del tenant"
                    print(f"[Backend] Descarga bloqueada por política global")
                    return jsonify({"allowed": False, "reason": reason})
        
        # 2. Verificar políticas de grupos del usuario
        if role == 'user':
            # Obtener grupos del usuario
            user_groups_res = user_supabase.table('group_users').select('group_id').eq('user_id', user_id).execute()
            user_groups = [g['group_id'] for g in user_groups_res.data] if user_groups_res.data else []
            
            if user_groups:
                group_policies = user_supabase.table('policies').select('*')\
                    .in_('group_id', user_groups)\
                    .eq('type', 'download')\
                    .execute()
                
                print(f"[Backend] Políticas de grupos encontradas: {len(group_policies.data)}")
                if group_policies.data:
                    print(f"[Backend] Políticas de grupos: {group_policies.data}")
                    for policy in group_policies.data:
                        if policy['action'] == 'block':
                            allowed = False
                            reason = "Descargas bloqueadas por política de grupo"
                            print(f"[Backend] Descarga bloqueada por política de grupo")
                            return jsonify({"allowed": False, "reason": reason})
        
        # 3. Verificar políticas específicas del usuario
        user_policies = user_supabase.table('policies').select('*')\
            .eq('tenant_id', tenant_id)\
            .eq('user_id', user_id)\
            .eq('type', 'download')\
            .execute()
        
        print(f"[Backend] Políticas de usuario encontradas: {len(user_policies.data)}")
        if user_policies.data:
            print(f"[Backend] Políticas de usuario: {user_policies.data}")
            for policy in user_policies.data:
                if policy['action'] == 'block':
                    allowed = False
                    reason = "Descargas bloqueadas por política de usuario"
                    print(f"[Backend] Descarga bloqueada por política de usuario")
                    return jsonify({"allowed": False, "reason": reason})
        
        print(f"[Backend] Resultado final - Permitido: {allowed}, Razón: {reason}")
        return jsonify({"allowed": allowed, "reason": reason})
        
    except Exception as e:
        print(f"[Backend] Error en check_download: {str(e)}")
        import traceback
        traceback.print_exc()
        # En caso de error, permitir la descarga para no interrumpir al usuario
        return jsonify({"allowed": True, "reason": "Error al verificar políticas"})

# --- ENDPOINT: DASHBOARD ---
@app.route('/api/admin/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def admin_dashboard():
    try:
        claims = get_jwt()
        admin_id = claims.get('sub')  # Obtener el ID del admin actual
        print(f"ADMIN_DASHBOARD - Claims: {claims}")
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # 1. Obtener todos los tenants de este admin
        tenants = user_supabase.table('tenants').select('*').eq('admin_id', admin_id).execute().data
        tenant_ids = [t['id'] for t in tenants]
        
        if not tenant_ids:
            return jsonify({
                "success": True,
                "data": {
                    "total_clients": 0,
                    "total_users": 0,
                    "active_clients": 0,
                    "active_users": 0,
                    "recent_clients": []
                }
            })

        # 2. Total de clientes (tenants) de este admin
        total_clients = len(tenants)
        
        # 3. Total de usuarios de los tenants de este admin
        users = user_supabase.table('users').select('id').in_('tenant_id', tenant_ids).execute().data
        total_users = len(users)
        
        # 4. Clientes activos
        active_clients = len([t for t in tenants if t['status'] == 'active'])
        
        # 5. Usuarios activos
        active_users = len([u for u in users if u.get('status') == 'active'])
        
        # 6. Últimos 5 clientes
        recent_clients = sorted(tenants, key=lambda x: x['created_at'], reverse=True)[:5]
        
        print(f"ADMIN_DASHBOARD - total_clients: {total_clients}, total_users: {total_users}")
        return jsonify({
            "success": True,
            "data": {
                "total_clients": total_clients,
                "total_users": total_users,
                "active_clients": active_clients,
                "active_users": active_users,
                "recent_clients": recent_clients
            }
        })
    except Exception as e:
        print(f"ADMIN_DASHBOARD - Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

# --- ENDPOINTS: CLIENTES (TENANTS) ---
@app.route('/api/admin/clients', methods=['GET'])
@jwt_required()
@admin_required
def admin_get_clients():
    try:
        print("=== Iniciando admin_get_clients ===")
        claims = get_jwt()
        admin_id = claims.get('sub')  # Obtener el ID del admin actual
        print(f"Claims del token: {claims}")

        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        print("Intentando obtener clientes de Supabase...")
        # Filtrar por admin_id para obtener solo los clientes de este admin
        tenants = user_supabase.table('tenants').select('*').eq('admin_id', admin_id).execute().data
        print(f"Clientes obtenidos exitosamente: {len(tenants)}")

        return jsonify({"success": True, "data": tenants})
    except Exception as e:
        print(f"=== ERROR en admin_get_clients ===")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje de error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/clients', methods=['POST'])
@jwt_required()
@admin_required
def admin_create_client():
    try:
        data = request.get_json()
        claims = get_jwt()
        admin_id = claims.get('sub')  # El ID del admin que está creando el tenant

        # Obtener el JWT y el cliente autenticado
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Prints de depuración
        print(f"admin_id a insertar: {admin_id} (type: {type(admin_id)})")
        print(f"sub del JWT: {claims.get('sub')} (type: {type(claims.get('sub'))})")

        tenant = user_supabase.table('tenants').insert({
            'name': data.get('name'),
            'description': data.get('description'),
            'max_users': data.get('max_users', 10),
            'status': 'active',
            'admin_id': admin_id,  # Asignamos el admin_id
            'created_at': datetime.utcnow().isoformat()
        }).execute().data[0]
        return jsonify({"success": True, "data": tenant})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/clients/<client_id>', methods=['PUT'])
@jwt_required()
@admin_required
def admin_update_client(client_id):
    try:
        data = request.get_json()
        update_data = {k: v for k, v in data.items() if k in ['name', 'description', 'max_users', 'status']}
        result = supabase.table('tenants').update(update_data).eq('id', client_id).execute()
        if not result.data:
            return jsonify({"success": False, "error": "Cliente no encontrado o no se pudo actualizar"}), 404
        tenant = result.data[0]
        return jsonify({"success": True, "data": tenant})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/clients/<client_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def admin_delete_client(client_id):
    try:
        supabase.table('tenants').delete().eq('id', client_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- ENDPOINTS: USUARIOS ---
@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
@admin_required
def admin_get_users():
    try:
        print("=== Iniciando admin_get_users ===")
        claims = get_jwt()
        print(f"Claims del token: {claims}")
        admin_id = claims.get('sub')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # 1. Obtener todos los tenants de este admin
        tenants = user_supabase.table('tenants').select('id, name').eq('admin_id', admin_id).execute().data
        tenant_ids = [t['id'] for t in tenants]
        if not tenant_ids:
            return jsonify({"success": True, "data": []})

        # 2. Obtener los usuarios de esos tenants
        users = user_supabase.table('users').select('*').in_('tenant_id', tenant_ids).execute().data

        # 3. Enriquecer con el nombre del tenant
        tenants_dict = {t['id']: t.get('name', '') for t in tenants}
        for u in users:
            u['tenant_name'] = tenants_dict.get(u.get('tenant_id'), '')

        print(f"Usuarios encontrados: {len(users)}")
        return jsonify({"success": True, "data": users})
    except Exception as e:
        print(f"=== ERROR en admin_get_users ===")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje de error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/users', methods=['POST'])
@jwt_required()
@admin_required
def admin_create_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')
        tenant_id = data.get('tenant_id')
        
        if not tenant_id:
            return jsonify({"success": False, "error": "Debe seleccionar un cliente (tenant)"}), 400
            
        # Obtener el JWT y el cliente autenticado
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        # Validar límite de usuarios
        tenant = user_supabase.table('tenants').select('id, max_users').eq('id', tenant_id).execute().data
        if not tenant:
            return jsonify({"success": False, "error": "Cliente (tenant) no encontrado"}), 404
            
        max_users = tenant[0].get('max_users', 0)
        current_users = user_supabase.table('users').select('id').eq('tenant_id', tenant_id).execute().data
        if len(current_users) >= max_users:
            return jsonify({"success": False, "error": f"El cliente ha alcanzado el límite máximo de usuarios ({max_users})."}), 400
            
        # Crear usuario en Supabase Auth y en la tabla users
        auth_user = user_supabase.auth.admin.create_user({
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {'role': role, 'tenant_id': tenant_id}
        })
        
        user = user_supabase.table('users').insert({
            'id': auth_user.user.id,
            'email': email,
            'role': role,
            'tenant_id': tenant_id,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }).execute().data[0]
        
        user['tenant_name'] = user_supabase.table('tenants').select('name').eq('id', tenant_id).execute().data[0]['name'] if tenant_id else ''
        
        # Actualizar el conteo de usuarios del tenant
        user_supabase.table('tenants').update({
            'users_count': len(user_supabase.table('users').select('id').eq('tenant_id', tenant_id).execute().data)
        }).eq('id', tenant_id).execute()
        
        return jsonify({"success": True, "data": user})
    except Exception as e:
        print(f"Error en admin_create_user: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/users/<user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def admin_update_user(user_id):
    try:
        data = request.get_json()
        update_data = {k: v for k, v in data.items() if k in ['role', 'tenant_id', 'status']}
        user = supabase.table('users').update(update_data).eq('id', user_id).execute().data[0]
        # Actualizar metadatos en Auth
        if 'role' in update_data or 'tenant_id' in update_data:
            supabase.auth.admin.update_user_by_id(user_id, {
                'user_metadata': {
                    'role': update_data.get('role', user['role']),
                    'tenant_id': update_data.get('tenant_id', user['tenant_id'])
                }
            })
        user['tenant_name'] = supabase.table('tenants').select('name').eq('id', user['tenant_id']).execute().data[0]['name'] if user['tenant_id'] else ''
        return jsonify({"success": True, "data": user})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def admin_delete_user(user_id):
    try:
        # Obtener tenant_id antes de eliminar
        user_data = supabase.table('users').select('tenant_id').eq('id', user_id).execute()
        if not user_data.data:
            return jsonify({"success": False, "error": "Usuario no encontrado"}), 404
        tenant_id = user_data.data[0]['tenant_id']

        # Primero eliminar de Supabase Auth
        try:
            supabase.auth.admin.delete_user(user_id)
        except Exception as e:
            print(f"Error eliminando en Supabase Auth: {str(e)}")
            return jsonify({"success": False, "error": f"Error eliminando en Auth: {str(e)}"}), 400

        # Si fue exitoso, eliminar de la tabla users
        supabase.table('users').delete().eq('id', user_id).execute()
        # Actualizar el conteo de usuarios del tenant
        supabase.table('tenants').update({
            'users_count': len(supabase.table('users').select('id').eq('tenant_id', tenant_id).execute().data)
        }).eq('id', tenant_id).execute()
        return jsonify({
            "success": True,
            "message": "Usuario eliminado correctamente"
        })
    except Exception as e:
        print(f"Error en delete_user: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

# --- ENDPOINTS ATHOS OWNER: ADMINS ---
@app.route('/api/athos/admins', methods=['GET'])
@jwt_required()
@athos_owner_required
def athos_get_admins():
    try:
        claims = get_jwt()
        print(f"ATHOS_GET_ADMINS - Claims: {claims}")
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        admins = user_supabase.table('users').select('*').eq('role', 'admin').execute().data
        print(f"ATHOS_GET_ADMINS - Admins encontrados: {len(admins)}")
        return jsonify({"success": True, "data": admins})
    except Exception as e:
        print(f"ATHOS_GET_ADMINS - Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/admins', methods=['POST'])
@jwt_required()
@athos_owner_required
def athos_create_admin():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')
        max_clients = data.get('max_clients', 10)

        if not email or not password:
            return jsonify({"success": False, "error": "Email y password son requeridos"}), 400

        # Obtener el JWT del usuario actual y el cliente Supabase autenticado
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # 1. Crear usuario admin en Auth
        try:
            auth_user = supabase.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {'role': 'admin'}
            })
        except Exception as e:
            if 'already registered' in str(e) or 'User already registered' in str(e) or 'duplicate key' in str(e):
                return jsonify({"success": False, "error": "El email ya está registrado en Auth"}), 400
            return jsonify({"success": False, "error": f"Error creando usuario en Auth: {str(e)}"}), 400

        # 2. Insertar en la tabla users usando el cliente autenticado
        try:
            user = user_supabase.table('users').insert({
                'id': auth_user.user.id,
                'email': email,
                'role': 'admin',
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }).execute().data[0]
        except Exception as e:
            try:
                supabase.auth.admin.delete_user(auth_user.user.id)
            except Exception as del_e:
                return jsonify({"success": False, "error": f"Error al crear usuario en la base de datos y al limpiar en Auth: {str(e)} / {str(del_e)}"}), 500
            return jsonify({"success": False, "error": f"Error al crear usuario en la base de datos: {str(e)}"}), 500

        # 3. Crear cliente Demo para este admin
        try:
            demo_tenant = user_supabase.table('tenants').insert({
                'name': f'Demo {name or email}',
                'description': 'Cliente Demo creado automáticamente',
                'max_users': 10,
                'status': 'active',
                'admin_id': auth_user.user.id,
                'created_at': datetime.utcnow().isoformat()
            }).execute().data[0]
        except Exception as e:
            try:
                user_supabase.table('users').delete().eq('id', auth_user.user.id).execute()
                supabase.auth.admin.delete_user(auth_user.user.id)
            except Exception as del_e:
                return jsonify({"success": False, "error": f"Error al crear el cliente demo y al limpiar el admin: {str(e)} / {str(del_e)}"}), 500
            return jsonify({"success": False, "error": f"Error al crear el cliente demo: {str(e)}"}), 500

        # 4. Crear usuario client demo para el cliente Demo usando el cliente autenticado
        try:
            demo_client_email = f"cliente.{email}"
            demo_client_auth = supabase.auth.admin.create_user({
                'email': demo_client_email,
                'password': '123',
                'email_confirm': True,
                'user_metadata': {'role': 'client', 'tenant_id': demo_tenant['id']}
            })
            demo_client_user = user_supabase.table('users').insert({
                'id': demo_client_auth.user.id,
                'email': demo_client_email,
                'role': 'client',
                'tenant_id': demo_tenant['id'],
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }).execute().data[0]
        except Exception as e:
            # Limpiar todo si falla aquí
            try:
                user_supabase.table('users').delete().eq('id', auth_user.user.id).execute()
                supabase.auth.admin.delete_user(auth_user.user.id)
                user_supabase.table('tenants').delete().eq('id', demo_tenant['id']).execute()
            except Exception as del_e:
                return jsonify({"success": False, "error": f"Error al crear el usuario client demo y al limpiar todo: {str(e)} / {str(del_e)}"}), 500
            return jsonify({"success": False, "error": f"Error al crear el usuario client demo: {str(e)}"}), 500

        # 5. Crear usuario user demo para el cliente Demo usando el cliente autenticado
        try:
            demo_user_email = f"user.{email}"
            demo_user_auth = supabase.auth.admin.create_user({
                'email': demo_user_email,
                'password': '123',
                'email_confirm': True,
                'user_metadata': {'role': 'user', 'tenant_id': demo_tenant['id']}
            })
            demo_user = user_supabase.table('users').insert({
                'id': demo_user_auth.user.id,
                'email': demo_user_email,
                'role': 'user',
                'tenant_id': demo_tenant['id'],
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }).execute().data[0]
        except Exception as e:
            # Limpiar todo si falla aquí
            try:
                user_supabase.table('users').delete().eq('id', auth_user.user.id).execute()
                user_supabase.table('users').delete().eq('id', demo_client_auth.user.id).execute()
                supabase.auth.admin.delete_user(auth_user.user.id)
                supabase.auth.admin.delete_user(demo_client_auth.user.id)
                user_supabase.table('tenants').delete().eq('id', demo_tenant['id']).execute()
            except Exception as del_e:
                return jsonify({"success": False, "error": f"Error al crear el usuario user demo y al limpiar todo: {str(e)} / {str(del_e)}"}), 500
            return jsonify({"success": False, "error": f"Error al crear el usuario user demo: {str(e)}"}), 500

        return jsonify({"success": True, "admin": user, "demo_tenant": demo_tenant, "demo_client_user": demo_client_user, "demo_user": demo_user})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/admins/<admin_id>', methods=['PUT'])
@jwt_required()
@athos_owner_required
def athos_update_admin(admin_id):
    try:
        data = request.get_json()
        updated = supabase.table('users').update(data).eq('id', admin_id).execute().data[0]
        return jsonify({"success": True, "data": updated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/admins/<admin_id>', methods=['DELETE'])
@jwt_required()
@athos_owner_required
def athos_delete_admin(admin_id):
    try:
        supabase.table('users').delete().eq('id', admin_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- ENDPOINTS ATHOS OWNER: CLIENTES ---
@app.route('/api/athos/clientes', methods=['GET'])
@jwt_required()
@athos_owner_required
def athos_get_clientes():
    try:
        claims = get_jwt()
        print(f"ATHOS_GET_CLIENTES - Claims: {claims}")
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        query = user_supabase.table('tenants').select('*')
        name = request.args.get('name')
        admin_id = request.args.get('admin_id')
        if name:
            query = query.ilike('name', f'%{name}%')
        if admin_id:
            query = query.eq('admin_id', admin_id)
        clientes = query.execute().data
        print(f"ATHOS_GET_CLIENTES - Clientes encontrados: {len(clientes)}")
        return jsonify({"success": True, "data": clientes})
    except Exception as e:
        print(f"ATHOS_GET_CLIENTES - Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/clientes', methods=['POST'])
@jwt_required()
@athos_owner_required
def athos_create_cliente():
    try:
        data = request.get_json()
        cliente = supabase.table('tenants').insert({
            'name': data.get('name'),
            'description': data.get('description'),
            'max_users': data.get('max_users', 10),
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }).execute().data[0]
        return jsonify({"success": True, "data": cliente})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/clientes/<cliente_id>', methods=['PUT'])
@jwt_required()
@athos_owner_required
def athos_update_cliente(cliente_id):
    try:
        data = request.get_json()
        updated = supabase.table('tenants').update(data).eq('id', cliente_id).execute().data[0]
        return jsonify({"success": True, "data": updated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/clientes/<cliente_id>', methods=['DELETE'])
@jwt_required()
@athos_owner_required
def athos_delete_cliente(cliente_id):
    try:
        supabase.table('tenants').delete().eq('id', cliente_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- ENDPOINTS ATHOS OWNER: USUARIOS ---
@app.route('/api/athos/usuarios', methods=['GET'])
@jwt_required()
@athos_owner_required
def athos_get_usuarios():
    try:
        print("=== Iniciando athos_get_usuarios ===")
        claims = get_jwt()
        print(f"Claims del token: {claims}")
        
        # Obtener el token JWT para pasar a Supabase
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        print("Iniciando consulta a Supabase...")
        query = user_supabase.table('users').select('*')
        
        # Aplicar filtros si existen
        email = request.args.get('email')
        role = request.args.get('role')
        tenant_id = request.args.get('tenant_id')
        
        if email:
            print(f"Aplicando filtro de email: {email}")
            query = query.ilike('email', f'%{email}%')
        if role:
            print(f"Aplicando filtro de role: {role}")
            query = query.eq('role', role)
        if tenant_id:
            print(f"Aplicando filtro de tenant_id: {tenant_id}")
            query = query.eq('tenant_id', tenant_id)
            
        print("Ejecutando consulta final...")
        usuarios = query.execute()
        print(f"Usuarios encontrados: {len(usuarios.data)}")
        
        return jsonify({"success": True, "data": usuarios.data})
    except Exception as e:
        print(f"=== ERROR en athos_get_usuarios ===")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje de error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/usuarios', methods=['POST'])
@jwt_required()
@athos_owner_required
def athos_create_usuario():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        auth_user = supabase.auth.admin.create_user({
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {'role': 'user'}
        })
        user = supabase.table('users').insert({
            'id': auth_user.user.id,
            'email': email,
            'role': 'user',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }).execute().data[0]
        return jsonify({"success": True, "data": user})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/usuarios/<usuario_id>', methods=['PUT'])
@jwt_required()
@athos_owner_required
def athos_update_usuario(usuario_id):
    try:
        data = request.get_json()
        updated = supabase.table('users').update(data).eq('id', usuario_id).execute().data[0]
        return jsonify({"success": True, "data": updated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/athos/usuarios/<usuario_id>', methods=['DELETE'])
@jwt_required()
@athos_owner_required
def athos_delete_usuario(usuario_id):
    try:
        supabase.table('users').delete().eq('id', usuario_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- ENDPOINT: ALERTAS (EXISTENTE, AHORA LEE alert_stats) ---
@app.route('/api/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    try:
        claims = get_jwt()
        tenant_id = claims.get('tenant_id')
        role = claims.get('role')

        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        query = user_supabase.table('alert_stats').select('*')

        # RLS ya debería filtrar por tenant_id para 'client' y 'user'
        # Si es admin, RLS permite ver todo.

        alert_stats_res = query.order('last_updated', desc=True).execute()

        print(f"Estadísticas obtenidas para tenant {tenant_id} (rol {role}): {len(alert_stats_res.data)}")

        # Devolvemos las estadísticas directamente.
        return jsonify({"success": True, "data": alert_stats_res.data})

    except Exception as e:
        import traceback
        print(f"Error en get_alerts: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/prohibited_sites', methods=['GET'])
def get_prohibited_sites():
    try:
        print("[Backend] Iniciando carga de sitios prohibidos...")
        # Cargar el archivo prohibidos.json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'prohibidos.json')
        print(f"[Backend] Ruta del archivo: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[Backend] Se cargaron {len(data)} categorías de sitios prohibidos")
        
        # Excluir la categoría 'recomendaciones' si existe
        data = {k: v for k, v in data.items() if k != 'recomendaciones'}
        return jsonify({"success": True, "data": data})
    except Exception as e:
        print(f"[Backend] Error al leer prohibidos.json: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/navigation_logs/riesgo', methods=['GET'])
@jwt_required()
def get_risk_logs():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Filtros
        user_id = request.args.get('user_id')
        category = request.args.get('category')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))

        # Construir la consulta base
        base_query = user_supabase.table('navigation_logs').select('*')
        
        # Aplicar filtros de permisos
        if role == 'admin':
            pass
        elif role == 'client':
            base_query = base_query.eq('tenant_id', tenant_id)
        else:
            return jsonify({"error": "No autorizado"}), 403

        # Aplicar filtros adicionales
        if user_id:
            base_query = base_query.eq('user_id', user_id)
        if category:
            base_query = base_query.eq('policy_info->category', category)
        if date_from:
            base_query = base_query.gte('timestamp', date_from)
        if date_to:
            base_query = base_query.lte('timestamp', date_to)

        # Total de registros filtrados
        count_query = user_supabase.table('navigation_logs').select('id', count='exact')
        if role == 'client':
            count_query = count_query.eq('tenant_id', tenant_id)
        if user_id:
            count_query = count_query.eq('user_id', user_id)
        if category:
            count_query = count_query.eq('policy_info->category', category)
        if date_from:
            count_query = count_query.gte('timestamp', date_from)
        if date_to:
            count_query = count_query.lte('timestamp', date_to)
        count_result = count_query.execute()
        total = count_result.count if hasattr(count_result, 'count') else len(count_result.data)

        # Paginación y datos
        from_idx = (page - 1) * page_size
        to_idx = from_idx + page_size - 1
        data_query = base_query.order('risk_score', desc=True).order('timestamp', desc=True).range(from_idx, to_idx)
        logs = data_query.execute()

        # Calcular riesgo para registros que no lo tengan
        for log in logs.data:
            if log.get('risk_score') is None:
                score = 0
                event_details = log.get('event_details', {})  # Inicializar siempre
                # Calcular riesgo basado en el tipo de evento
                event_type = log.get('event_type', 'navegacion')
                if event_type == 'formulario':
                    score += 20
                elif event_type == 'descarga':
                    score += 30
                elif event_type == 'bloqueo':
                    score += 50
                elif event_type == 'navegacion':
                    # Verificar si es una interacción de usuario
                    if isinstance(event_details, dict):
                        tipo_evento = event_details.get('tipo_evento')
                        if tipo_evento in ['copy', 'paste']:
                            score += 25
                        elif tipo_evento in ['download', 'file_upload']:
                            score += 35
                        elif tipo_evento == 'click':
                            score += 15
                        else:
                            score += 10
                    else:
                        score += 10

                # Ajustar según detalles específicos
                if isinstance(event_details, dict):
                    if event_details.get('sensitive_fields'):
                        score += 15
                    if event_details.get('file_type') in ['exe', 'zip', 'rar']:
                        score += 25
                    if event_details.get('nombre_archivo'):
                        extension = event_details['nombre_archivo'].split('.')[-1].lower()
                        if extension in ['exe', 'zip', 'rar', 'pdf', 'doc', 'docx']:
                            score += 20

                # Ajustar según la acción
                action = log.get('action')
                if action == 'bloqueado':
                    score += 30
                elif action == 'permitido':
                    score -= 10

                # Asegurar que el score esté entre 0 y 100
                log['risk_score'] = max(0, min(score, 100))

        return jsonify({
            "success": True,
            "data": logs.data,
            "total": total,
            "page": page,
            "page_size": page_size
        })

    except Exception as e:
        print(f"Error en get_risk_logs: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/navigation_logs/comport', methods=['GET'])
@jwt_required()
def get_comport_navigation_logs():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Filtros
        user_id = request.args.get('user_id')
        tipo = request.args.get('tipo')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))

        # Obtener logs de navegación filtrados
        base_query = user_supabase.table('navigation_logs').select('*')
        if role == 'admin':
            pass
        elif role == 'client':
            base_query = base_query.eq('tenant_id', tenant_id)
        else:
            return jsonify({"error": "No autorizado"}), 403
        if user_id:
            base_query = base_query.eq('user_id', user_id)
        if date_from:
            base_query = base_query.gte('timestamp', date_from)
        if date_to:
            base_query = base_query.lte('timestamp', date_to)
        logs = base_query.order('timestamp', desc=True).limit(1000).execute().data

        # --- Lógica base de comportamientos anómalos ---
        eventos = []
        # 1. Cambio de horario
        for log in logs:
            hora = log.get('timestamp')
            if hora:
                hora_dt = None
                try:
                    from dateutil import parser
                    hora_dt = parser.parse(hora)
                except Exception:
                    continue
                if hora_dt.hour < 8 or hora_dt.hour > 19:
                    eventos.append({
                        'usuario': log.get('user_id'),
                        'tipo': 'Cambio de horario',
                        'detalle': f"Acceso fuera de horario laboral a {log.get('domain')}",
                        'hora': hora,
                        'sospechoso': True
                    })
        # 2. Sitio inusual (primer acceso a un dominio para ese usuario)
        user_domains = {}
        for log in reversed(logs):  # Procesar en orden cronológico
            uid = log.get('user_id')
            # Normalizar dominio base
            dom = normalize_domain(log.get('domain') or log.get('url') or '')
            hora = log.get('timestamp')
            if not uid or not dom:
                continue
            if uid not in user_domains:
                user_domains[uid] = set()
            if dom not in user_domains[uid]:
                eventos.append({
                    'usuario': uid,
                    'tipo': 'Sitio inusual',
                    'detalle': f"Primer acceso a dominio desconocido: {dom}",
                    'hora': hora,
                    'sospechoso': True
                })
                user_domains[uid].add(dom)
        # 3. Patrón irregular (más de 5 accesos en 10 minutos)
        from collections import defaultdict
        import datetime
        user_times = defaultdict(list)
        for log in logs:
            uid = log.get('user_id')
            hora = log.get('timestamp')
            if not uid or not hora:
                continue
            try:
                from dateutil import parser
                hora_dt = parser.parse(hora)
            except Exception:
                continue
            user_times[uid].append(hora_dt)
        for uid, times in user_times.items():
            times = sorted(times)
            for i in range(len(times)):
                window = [t for t in times if 0 <= (t - times[i]).total_seconds() <= 600]
                if len(window) > 5:
                    eventos.append({
                        'usuario': uid,
                        'tipo': 'Patrón irregular',
                        'detalle': f"{len(window)} accesos en menos de 10 minutos",
                        'hora': times[i].isoformat(),
                        'sospechoso': True
                    })
                    break  # Solo un evento por usuario
        # Filtros adicionales
        if tipo:
            eventos = [e for e in eventos if e['tipo'] == tipo]
        if user_id:
            eventos = [e for e in eventos if e['usuario'] == user_id]
        if date_from:
            eventos = [e for e in eventos if e['hora'] >= date_from]
        if date_to:
            eventos = [e for e in eventos if e['hora'] <= date_to]
        eventos = sorted(eventos, key=lambda x: x['hora'], reverse=True)
        total = len(eventos)
        start = (page - 1) * page_size
        end = start + page_size
        data = eventos[start:end]
        return jsonify({
            'success': True,
            'data': data,
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/navigation_logs/geo', methods=['GET'])
@jwt_required()
def get_geo_navigation_logs():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Filtros
        user_id = request.args.get('user_id')
        pais = request.args.get('pais')
        ciudad = request.args.get('ciudad')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        estado = request.args.get('estado')  # 'habitual' o 'no_habitual'
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))

        # Construir query base
        base_query = user_supabase.table('navigation_logs').select('*')
        
        # Aplicar filtros de tenant y usuario
        if role == 'client':
            base_query = base_query.eq('tenant_id', tenant_id)
        elif role != 'admin':
            return jsonify({"error": "No autorizado"}), 403
            
        if user_id:
            base_query = base_query.eq('user_id', user_id)
        if date_from:
            base_query = base_query.gte('timestamp', date_from)
        if date_to:
            base_query = base_query.lte('timestamp', date_to)
            
        # Aplicar filtros de ubicación si existen
        if pais:
            base_query = base_query.ilike('country', f'%{pais}%')
        if ciudad:
            base_query = base_query.ilike('city', f'%{ciudad}%')

        # Obtener total de registros
        count_query = user_supabase.table('navigation_logs').select('*', count='exact')
        if role == 'client':
            count_query = count_query.eq('tenant_id', tenant_id)
        if user_id:
            count_query = count_query.eq('user_id', user_id)
        if date_from:
            count_query = count_query.gte('timestamp', date_from)
        if date_to:
            count_query = count_query.lte('timestamp', date_to)
        if pais:
            count_query = count_query.ilike('country', f'%{pais}%')
        if ciudad:
            count_query = count_query.ilike('city', f'%{ciudad}%')
            
        count_result = count_query.execute()
        total = count_result.count if hasattr(count_result, 'count') else 0

        # Obtener datos paginados
        logs = base_query.order('timestamp', desc=True).range(
            (page - 1) * page_size,
            page * page_size - 1
        ).execute().data

        # Procesar logs para determinar IPs habituales
        eventos = []
        user_ips = {}
        
        # Primero obtener todas las IPs históricas para cada usuario
        if estado in ['habitual', 'no_habitual']:
            historical_ips = user_supabase.table('navigation_logs')\
                .select('user_id,ip_address')\
                .order('timestamp', desc=True)\
                .limit(1000)\
                .execute().data
            
            for log in historical_ips:
                uid = log.get('user_id')
                ip = log.get('ip_address')
                if uid and ip:
                    if uid not in user_ips:
                        user_ips[uid] = set()
                    user_ips[uid].add(ip)

        # Procesar los logs de la página actual
        for log in logs:
            uid = log.get('user_id')
            ip = log.get('ip_address')
            ciudad_val = log.get('city')
            pais_val = log.get('country')
            hora = log.get('timestamp')
            
            if not uid or not ip:
                continue

            # Determinar si es IP habitual
            alerta = False
            if estado in ['habitual', 'no_habitual']:
                if uid in user_ips and ip not in user_ips[uid]:
                    alerta = True
            elif estado == 'habitual':
                continue
            elif estado == 'no_habitual':
                continue

            evento = {
                'usuario': uid,
                'ip': ip,
                'ciudad': ciudad_val or '-',
                'pais': pais_val or '-',
                'hora': hora,
                'alerta': alerta
            }
            eventos.append(evento)

        return jsonify({
            'success': True,
            'data': eventos,
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/navigation_logs/stats', methods=['GET'])
@jwt_required()
def get_navigation_stats():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Obtener parámetros de filtro
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        # Construir la consulta base
        query = user_supabase.table('navigation_logs').select('*')

        # Aplicar filtros de tenant_id según el rol
        if role == 'admin':
            pass  # Los admins pueden ver todo
        elif role == 'client':
            query = query.eq('tenant_id', tenant_id)
        else:
            return jsonify({"success": False, "error": "No autorizado"}), 403

        # Aplicar filtros de fecha si se proporcionan
        if date_from:
            try:
                datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.gte('timestamp', date_from)
            except ValueError:
                return jsonify({"success": False, "error": "Formato de fecha inválido"}), 400

        if date_to:
            try:
                datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.lte('timestamp', date_to)
            except ValueError:
                return jsonify({"success": False, "error": "Formato de fecha inválido"}), 400

        # Ejecutar la consulta
        logs = query.execute()
        print(f"Total de logs obtenidos: {len(logs.data)}")

        if not logs.data:
            return jsonify({
                "success": True,
                "data": {
                    "total_sites": 0,
                    "most_frequent_category": None,
                    "active_users": 0,
                    "avg_session_time": "0m",
                    "category_distribution": [],
                    "user_distribution": [],
                    "hourly_distribution": []
                }
            })

        # Procesar los datos
        logs_data = logs.data

        # Calcular estadísticas básicas
        total_sites = len(logs_data)
        active_users = len(set(log.get('user_id') for log in logs_data if log.get('user_id')))
        print(f"Usuarios activos: {active_users}")

        # Distribución por categorías
        category_counts = {}
        for log in logs_data:
            policy_info = log.get('policy_info')
            if isinstance(policy_info, dict):
                category = policy_info.get('category', 'sin categoría')
            else:
                category = 'sin categoría'
            category_counts[category] = category_counts.get(category, 0) + 1

        most_frequent_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None
        category_distribution = [{"category": k, "count": v} for k, v in category_counts.items()]

        # Distribución por usuario
        user_counts = {}
        for log in logs_data:
            user_id = log.get('user_id')
            if user_id:
                user_counts[user_id] = user_counts.get(user_id, 0) + 1

        user_distribution = [{"user_id": k, "count": v} for k, v in user_counts.items()]

        # Distribución por hora
        hourly_counts = {str(hour).zfill(2): 0 for hour in range(24)}
        for log in logs_data:
            timestamp = log.get('timestamp')
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).hour
                    hourly_counts[str(hour).zfill(2)] = hourly_counts.get(str(hour).zfill(2), 0) + 1
                except (ValueError, AttributeError):
                    continue

        hourly_distribution = [{"hour": k, "count": v} for k, v in sorted(hourly_counts.items())]

        # Calcular tiempo promedio de sesión
        user_sessions = {}
        for log in logs_data:
            user_id = log.get('user_id')
            timestamp = log.get('timestamp')
            if not user_id or not timestamp:
                continue
            try:
                timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if user_id not in user_sessions:
                    user_sessions[user_id] = []
                user_sessions[user_id].append(timestamp_dt)
            except (ValueError, AttributeError) as e:
                print(f"Error procesando timestamp: {e}")
                continue

        print(f"Usuarios con logs: {len(user_sessions)}")

        # Calcular duración promedio de sesión
        session_durations = []
        SESSION_TIMEOUT = 1800  # 30 minutos en segundos

        for user_id, timestamps in user_sessions.items():
            if len(timestamps) < 2:
                continue

            # Ordenar timestamps
            timestamps.sort()
            
            current_session_start = timestamps[0]
            last_timestamp = timestamps[0]
            
            for timestamp in timestamps[1:]:
                time_diff = (timestamp - last_timestamp).total_seconds()
                
                if time_diff > SESSION_TIMEOUT:
                    # Finalizar sesión actual
                    session_duration = (last_timestamp - current_session_start).total_seconds()
                    if session_duration > 0:
                        session_durations.append(session_duration)
                        print(f"Sesión para usuario {user_id}: {session_duration/60:.2f} minutos")
                    # Iniciar nueva sesión
                    current_session_start = timestamp
                
                last_timestamp = timestamp
            
            # Procesar última sesión
            session_duration = (last_timestamp - current_session_start).total_seconds()
            if session_duration > 0:
                session_durations.append(session_duration)
                print(f"Última sesión para usuario {user_id}: {session_duration/60:.2f} minutos")

        print(f"Duración total de sesiones: {sum(session_durations)/60:.2f} minutos")
        print(f"Número de sesiones válidas: {len(session_durations)}")

        # Calcular tiempo promedio en formato amigable
        if session_durations:
            avg_seconds = sum(session_durations) / len(session_durations)
            print(f"Promedio en segundos: {avg_seconds}")
            minutes = int(avg_seconds // 60)
            if minutes < 60:
                avg_session_time = f"{minutes}m"
            else:
                hours = minutes // 60
                remaining_minutes = minutes % 60
                if hours < 24:
                    avg_session_time = f"{hours}h {remaining_minutes}m"
                else:
                    days = hours // 24
                    remaining_hours = hours % 24
                    if remaining_hours > 0:
                        avg_session_time = f"{days}d {remaining_hours}h {remaining_minutes}m"
                    else:
                        avg_session_time = f"{days}d {remaining_minutes}m"
        else:
            avg_session_time = "0m"

        return jsonify({
            "success": True,
            "data": {
                "total_sites": total_sites,
                "most_frequent_category": most_frequent_category,
                "active_users": active_users,
                "avg_session_time": avg_session_time,
                "category_distribution": category_distribution,
                "user_distribution": user_distribution,
                "hourly_distribution": hourly_distribution
            }
        })

    except Exception as e:
        import traceback
        print(f"Error en get_navigation_stats: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/alerts/stats', methods=['GET'])
@jwt_required()
def get_alerts_stats():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        # Obtener parámetros de filtro
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        user_id = request.args.get('user_id')
        category = request.args.get('category')

        # Construir la consulta base
        query = user_supabase.table('navigation_logs').select('*')

        # Aplicar filtros de tenant_id según el rol
        if role == 'admin':
            pass  # Los admins pueden ver todo
        elif role == 'client':
            query = query.eq('tenant_id', tenant_id)
        else:
            return jsonify({"success": False, "error": "No autorizado"}), 403

        # Aplicar filtros adicionales
        if date_from:
            try:
                datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.gte('timestamp', date_from)
            except ValueError:
                return jsonify({"success": False, "error": "Formato de fecha inválido"}), 400

        if date_to:
            try:
                datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.lte('timestamp', date_to)
            except ValueError:
                return jsonify({"success": False, "error": "Formato de fecha inválido"}), 400

        if user_id:
            query = query.eq('user_id', user_id)

        if category:
            query = query.eq('policy_info->category', category)

        # Ejecutar la consulta
        logs = query.execute()
        logs_data = logs.data

        if not logs_data:
            return jsonify({
                "success": True,
                "data": {
                    "total_alerts": 0,
                    "alerts_by_category": {},
                    "alerts_by_user": {},
                    "alerts_by_hour": {str(hour).zfill(2): 0 for hour in range(24)},
                    "alerts_by_severity": {
                        "high": 0,
                        "medium": 0,
                        "low": 0
                    },
                    "alerts_trend": []
                }
            })

        # Procesar los datos
        alerts_by_category = {}
        alerts_by_user = {}
        alerts_by_hour = {str(hour).zfill(2): 0 for hour in range(24)}
        alerts_by_severity = {"high": 0, "medium": 0, "low": 0}
        alerts_trend = []

        for log in logs_data:
            # Contar por categoría
            policy_info = log.get('policy_info')
            if isinstance(policy_info, dict):
                category = policy_info.get('category', 'sin categoría')
            else:
                category = 'sin categoría'
            alerts_by_category[category] = alerts_by_category.get(category, 0) + 1

            # Contar por usuario
            user_id = log.get('user_id')
            if user_id:
                alerts_by_user[user_id] = alerts_by_user.get(user_id, 0) + 1

            # Contar por hora
            timestamp = log.get('timestamp')
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).hour
                    alerts_by_hour[str(hour).zfill(2)] = alerts_by_hour.get(str(hour).zfill(2), 0) + 1
                except (ValueError, AttributeError):
                    continue

            # Contar por severidad
            risk_score = log.get('risk_score')
            if risk_score is None:
                risk_score = 0
            if risk_score > 80:
                alerts_by_severity["high"] += 1
            elif risk_score > 50:
                alerts_by_severity["medium"] += 1
            else:
                alerts_by_severity["low"] += 1

            # Preparar tendencia
            if timestamp:
                try:
                    date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    alerts_trend.append(date.isoformat())
                except (ValueError, AttributeError):
                    continue

        # Procesar tendencia
        trend_data = {}
        for date in alerts_trend:
            trend_data[date] = trend_data.get(date, 0) + 1
        alerts_trend = [{"date": date, "count": count} for date, count in sorted(trend_data.items())]

        return jsonify({
            "success": True,
            "data": {
                "total_alerts": len(logs_data),
                "alerts_by_category": alerts_by_category,
                "alerts_by_user": alerts_by_user,
                "alerts_by_hour": alerts_by_hour,
                "alerts_by_severity": alerts_by_severity,
                "alerts_trend": alerts_trend
            }
        })

    except Exception as e:
        import traceback
        print(f"Error en get_alerts_stats: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

# --- ENDPOINTS DE GRUPOS DE USUARIOS ---
@app.route('/api/groups', methods=['POST'])
@jwt_required()
def create_group():
    try:
        claims = get_jwt()
        role = claims.get('role')
        request_tenant_id = claims.get('tenant_id') # Tenant del usuario que hace la request
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        user_ids = data.get('user_ids', []) # Lista de IDs de usuarios para el grupo

        if not name:
            return jsonify({"success": False, "error": "El nombre del grupo es requerido"}), 400

        target_tenant_id = None
        if role == 'client':
            target_tenant_id = request_tenant_id
        elif role == 'admin':
            target_tenant_id = data.get('tenant_id', request_tenant_id) 
            if not target_tenant_id and role == 'admin':
                 pass # Puede ser None si son grupos globales para admins. Ajustar según necesidad.


        # Validar que los usuarios existan y pertenezcan al tenant_id correcto (si aplica)
        if target_tenant_id and user_ids:
            users_check = user_supabase.table('users').select('id').eq('tenant_id', target_tenant_id).in_('id', user_ids).execute()
            if len(users_check.data) != len(set(user_ids)): # Compara con set para evitar duplicados en user_ids
                # Identificar usuarios faltantes o no pertenecientes
                existing_user_ids_in_tenant = {str(u['id']) for u in users_check.data}
                missing_or_invalid_ids = [uid for uid in user_ids if str(uid) not in existing_user_ids_in_tenant]
                print(f"Usuarios inválidos o no encontrados en el tenant {target_tenant_id}: {missing_or_invalid_ids}")
                return jsonify({"success": False, "error": f"Algunos usuarios no existen o no pertenecen al tenant especificado: {missing_or_invalid_ids}"}), 400
        
        # Insertar el nuevo grupo
        group_data = {
            'name': name,
            'description': description
        }
        # Solo añadir tenant_id si no es None
        if target_tenant_id:
            group_data['tenant_id'] = target_tenant_id
        
        new_group_res = user_supabase.table('groups').insert(group_data).execute()

        if not new_group_res.data:
            # Intenta obtener más información del error de Supabase si está disponible
            error_message = "No se pudo crear el grupo"
            if hasattr(new_group_res, 'error') and new_group_res.error:
                error_message += f": {new_group_res.error.message}"
            print(f"Error al crear grupo en Supabase: {error_message}, data: {group_data}")
            return jsonify({"success": False, "error": error_message}), 500
        
        created_group = new_group_res.data[0]
        group_id = created_group['id']

        # Asociar usuarios al grupo
        if user_ids:
            # Asegurarse de que no hay user_ids duplicados
            unique_user_ids = list(set(user_ids))
            group_user_associations = []
            for user_id in unique_user_ids:
                assoc_data = {'group_id': group_id, 'user_id': user_id}
                # Solo añadir tenant_id a la tabla de cruce si el grupo lo tiene.
                if target_tenant_id: 
                    assoc_data['tenant_id'] = target_tenant_id
                group_user_associations.append(assoc_data)
            
            if group_user_associations: # Solo insertar si hay asociaciones
                assoc_res = user_supabase.table('group_users').insert(group_user_associations).execute()
                if hasattr(assoc_res, 'error') and assoc_res.error:
                    # Si falla la asociación, el grupo ya fue creado. Se podría revertir o loggear.
                    print(f"Error al asociar usuarios al grupo {group_id}: {assoc_res.error.message}")
                    # Devolver el grupo creado pero con una advertencia o un error parcial.
                    # Por ahora, devolvemos el grupo pero loggeamos el error.
                    # Considerar una transacción si es crítico que ambas operaciones (crear grupo, añadir miembros) sean atómicas.

        return jsonify({"success": True, "data": created_group}), 201

    except Exception as e:
        print(f"Error en create_group: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/groups', methods=['GET'])
@jwt_required()
def get_groups():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id') # Tenant del usuario que hace la request
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        base_query = user_supabase.table('groups').select('id, name, description, tenant_id, created_at, updated_at')
        
        if role == 'client':
            base_query = base_query.eq('tenant_id', tenant_id)
        elif role == 'admin':
            filter_tenant_id = request.args.get('tenant_id')
            if filter_tenant_id:
                try:
                    UUID(filter_tenant_id, version=4) # Validar que es un UUID
                    base_query = base_query.eq('tenant_id', filter_tenant_id)
                except ValueError:
                    return jsonify({"success": False, "error": "Formato de tenant_id inválido para el filtro."}), 400
            # Si admin no filtra, ve todos los grupos que RLS le permita.
        else:
            return jsonify({"success": False, "error": "No autorizado para ver grupos"}), 403

        groups_res = base_query.order('name', desc=False).execute()
        
        if hasattr(groups_res, 'error') and groups_res.error:
            print(f"Error al obtener grupos: {groups_res.error.message}")
            return jsonify({"success": False, "error": f"Error al obtener grupos: {groups_res.error.message}"}), 500

        processed_groups = []
        if groups_res.data:
            group_ids = [g['id'] for g in groups_res.data]
            
            # Obtener conteo de usuarios por grupo
            # La columna group_id en group_users es la FK a groups.id
            counts_res = user_supabase.table('group_users').select('group_id, user_id').in_('group_id', group_ids).execute() # Contamos user_id para obtener el número de usuarios
            
            user_counts = {}
            if counts_res.data:
                for row in counts_res.data:
                    gid = row['group_id']
                    user_counts[gid] = user_counts.get(gid, 0) + 1

            # Obtener los miembros (id, email) de cada grupo
            # Esta consulta puede ser pesada si hay muchos grupos/usuarios.
            # group_members_res = user_supabase.table('group_users').select('group_id, users(id, email)').in_('group_id', group_ids).execute()
            # La anterior tiene una sintaxis incorrecta para el join selectivo.
            # Necesitas que 'users' sea una relación en 'group_users' o usar una función RPC.
            # Alternativa: Obtener todos los (group_id, user_id) y luego info de users.
            
            group_user_pairs_res = user_supabase.table('group_users').select('group_id, user_id').in_('group_id', group_ids).execute()
            
            all_user_ids_in_groups = list(set([pair['user_id'] for pair in group_user_pairs_res.data if pair.get('user_id')]))
            users_info = {}
            if all_user_ids_in_groups:
                users_data_res = user_supabase.table('users').select('id, email').in_('id', all_user_ids_in_groups).execute()
                if users_data_res.data:
                    for u_info in users_data_res.data:
                        users_info[str(u_info['id'])] = {'id': str(u_info['id']), 'email': u_info['email']}
            
            members_by_group = {}
            if group_user_pairs_res.data:
                for pair in group_user_pairs_res.data:
                    gid = pair['group_id']
                    uid = str(pair['user_id'])
                    if gid not in members_by_group:
                        members_by_group[gid] = []
                    if uid in users_info: # Solo añadir si tenemos la info del usuario (debería ser siempre si no hay datos huérfanos)
                        members_by_group[gid].append(users_info[uid])


            for group in groups_res.data:
                gid = group['id']
                processed_group = {
                    "id": gid,
                    "name": group["name"],
                    "description": group.get("description"),
                    "tenant_id": group.get("tenant_id"),
                    "created_at": group.get("created_at"),
                    "updated_at": group.get("updated_at"),
                    "user_count": user_counts.get(gid, 0),
                    "users": members_by_group.get(gid, []) 
                }
                processed_groups.append(processed_group)

        return jsonify({"success": True, "data": processed_groups})

    except Exception as e:
        print(f"Error en get_groups: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/groups/<group_id_str>', methods=['PUT']) # Cambiado a group_id_str para claridad
@jwt_required()
def update_group(group_id_str): # Cambiado a group_id_str
    try:
        claims = get_jwt()
        role = claims.get('role')
        request_tenant_id = claims.get('tenant_id') # Tenant del usuario que hace la request
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        try:
            group_id = UUID(group_id_str, version=4) # Validar y convertir a UUID
        except ValueError:
            return jsonify({"success": False, "error": "Formato de group_id inválido."}), 400

        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        user_ids_str = data.get('user_ids') # Lista completa de IDs de usuarios para el grupo (como strings)

        # Validar user_ids si se proporcionan
        user_ids_uuid = []
        if user_ids_str is not None:
            try:
                user_ids_uuid = [UUID(uid, version=4) for uid in user_ids_str]
                user_ids_uuid = list(set(user_ids_uuid)) # Eliminar duplicados
            except ValueError:
                return jsonify({"success": False, "error": "Formato de user_id inválido en la lista."}), 400
        
        # Verificar que el grupo existe y el usuario tiene permiso
        group_check_query = user_supabase.table('groups').select('id, tenant_id').eq('id', group_id)
        
        # Solo los clients están restringidos a su tenant_id explícitamente aquí.
        # Admin RLS debería permitir o denegar basado en su propia lógica.
        if role == 'client':
            group_check_query = group_check_query.eq('tenant_id', request_tenant_id)
        
        group_check_res = group_check_query.maybe_single().execute()

        if not group_check_res.data:
            return jsonify({"success": False, "error": "Grupo no encontrado o no autorizado"}), 404
        
        current_group_tenant_id_str = group_check_res.data.get('tenant_id')
        # Convertir current_group_tenant_id_str a UUID si no es None
        current_group_tenant_id = UUID(current_group_tenant_id_str) if current_group_tenant_id_str else None


        update_payload = {}
        if name is not None: # Permitir string vacío para nombre si la lógica de negocio lo permite
            update_payload['name'] = name
        if description is not None: # Permitir string vacío para descripción
            update_payload['description'] = description
        
        # Solo actualizar si hay algo que cambiar en la tabla 'groups'
        if update_payload:
            update_payload['updated_at'] = datetime.utcnow().isoformat()
            updated_group_res = user_supabase.table('groups').update(update_payload).eq('id', group_id).execute()
            if hasattr(updated_group_res, 'error') and updated_group_res.error:
                 print(f"Error al actualizar tabla groups: {updated_group_res.error.message}")
                 return jsonify({"success": False, "error": f"Error al actualizar el grupo: {updated_group_res.error.message}"}), 500
            if not updated_group_res.data: # Debería haber datos si la actualización fue exitosa
                 return jsonify({"success": False, "error": "No se pudo actualizar el grupo (no se devolvieron datos)"}), 500

        # Actualizar asociaciones de usuarios si se proporcionan user_ids_uuid
        if user_ids_str is not None: # Lista vacía [] significa quitar todos los usuarios
            # Validar usuarios contra el tenant del grupo
            if current_group_tenant_id and user_ids_uuid: # Solo validar si el grupo tiene tenant y se pasan user_ids
                users_check = user_supabase.table('users').select('id').eq('tenant_id', current_group_tenant_id).in_('id', [str(uid) for uid in user_ids_uuid]).execute()
                if len(users_check.data) != len(user_ids_uuid):
                    existing_user_ids_in_tenant = {str(u['id']) for u in users_check.data}
                    missing_or_invalid_ids = [str(uid) for uid in user_ids_uuid if str(uid) not in existing_user_ids_in_tenant]
                    print(f"Usuarios inválidos en PUT /api/groups/{group_id}: {missing_or_invalid_ids}")
                    return jsonify({"success": False, "error": f"Algunos usuarios no existen o no pertenecen al tenant del grupo: {missing_or_invalid_ids}"}), 400
            
            # Eliminar asociaciones existentes para este grupo
            delete_assoc_res = user_supabase.table('group_users').delete().eq('group_id', group_id).execute()
            if hasattr(delete_assoc_res, 'error') and delete_assoc_res.error:
                print(f"Error al eliminar asociaciones de usuarios para grupo {group_id}: {delete_assoc_res.error.message}")
                # Continuar de todos modos, ya que el grupo podría haber sido actualizado.
                # O devolver un error si esto es crítico.

            # Crear nuevas asociaciones
            if user_ids_uuid: # Solo si la lista no está vacía
                group_user_associations = []
                for user_id_assoc_uuid in user_ids_uuid:
                    assoc_data = {'group_id': group_id, 'user_id': user_id_assoc_uuid}
                    if current_group_tenant_id:
                        assoc_data['tenant_id'] = current_group_tenant_id # Añadir tenant_id del grupo
                    group_user_associations.append(assoc_data)
                
                if group_user_associations:
                    assoc_res = user_supabase.table('group_users').insert(group_user_associations).execute()
                    if hasattr(assoc_res, 'error') and assoc_res.error:
                        print(f"Error al crear nuevas asociaciones de usuarios para grupo {group_id}: {assoc_res.error.message}")
                        # Considerar el manejo de este error.
        
        # Obtener el grupo completamente actualizado para la respuesta (similar a get_groups)
        # Esto asegura que devolvemos el estado más reciente con conteo y usuarios.
        final_group_res = user_supabase.table('groups').select('id, name, description, tenant_id, created_at, updated_at').eq('id', group_id).single().execute()
        if not final_group_res.data:
             return jsonify({"success": False, "error": "No se pudo obtener el grupo actualizado después de la operación"}), 500

        group_for_response_base = final_group_res.data
        gid_resp = group_for_response_base['id']

        counts_resp_res = user_supabase.table('group_users').select('user_id', count='exact').eq('group_id', gid_resp).execute() # Usar count='exact'
        user_count_resp = counts_resp_res.count if hasattr(counts_resp_res, 'count') else 0
        
        members_resp_pairs = user_supabase.table('group_users').select('user_id').eq('group_id', gid_resp).execute()
        members_resp_user_ids = [str(pair['user_id']) for pair in members_resp_pairs.data if pair.get('user_id')]
        
        users_info_resp = {}
        if members_resp_user_ids:
            users_data_resp_final = user_supabase.table('users').select('id, email').in_('id', members_resp_user_ids).execute()
            if users_data_resp_final.data:
                for u_info_f in users_data_resp_final.data:
                    users_info_resp[str(u_info_f['id'])] = {'id': str(u_info_f['id']), 'email': u_info_f['email']}
        
        final_user_list = [users_info_resp[uid_str] for uid_str in members_resp_user_ids if uid_str in users_info_resp]

        processed_group_final = {
            "id": gid_resp,
            "name": group_for_response_base["name"],
            "description": group_for_response_base.get("description"),
            "tenant_id": group_for_response_base.get("tenant_id"),
            "created_at": group_for_response_base.get("created_at"),
            "updated_at": group_for_response_base.get("updated_at"),
            "user_count": user_count_resp,
            "users": final_user_list
        }
        return jsonify({"success": True, "data": processed_group_final})

    except Exception as e:
        print(f"Error en update_group (group_id: {group_id_str}): {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/groups/<group_id_str>', methods=['DELETE']) # Cambiado a group_id_str
@jwt_required()
def delete_group(group_id_str): # Cambiado a group_id_str
    try:
        claims = get_jwt()
        role = claims.get('role')
        request_tenant_id = claims.get('tenant_id') # Tenant del usuario que hace la request
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)

        try:
            group_id = UUID(group_id_str, version=4) # Validar y convertir a UUID
        except ValueError:
            return jsonify({"success": False, "error": "Formato de group_id inválido."}), 400

        # Verificar que el grupo existe y el usuario tiene permiso
        group_check_query = user_supabase.table('groups').select('id, tenant_id').eq('id', group_id)
        if role == 'client':
            group_check_query = group_check_query.eq('tenant_id', request_tenant_id)
        
        group_check_res = group_check_query.maybe_single().execute()

        if not group_check_res.data:
            return jsonify({"success": False, "error": "Grupo no encontrado o no autorizado para eliminar"}), 404

        # Eliminar asociaciones de usuarios primero (dependencia).
        # Esto es importante si hay FK con ON DELETE CASCADE, pero hacerlo explícitamente es más seguro.
        delete_assoc_res = user_supabase.table('group_users').delete().eq('group_id', group_id).execute()
        if hasattr(delete_assoc_res, 'error') and delete_assoc_res.error:
             print(f"Error al eliminar asociaciones de usuarios para grupo {group_id} durante DELETE: {delete_assoc_res.error.message}")
             # Considerar si se debe detener la eliminación del grupo aquí. Por ahora, continuamos.

        # Eliminar el grupo
        deleted_group_res = user_supabase.table('groups').delete().eq('id', group_id).execute()

        if hasattr(deleted_group_res, 'error') and deleted_group_res.error:
            print(f"Error al eliminar grupo {group_id} de la tabla groups: {deleted_group_res.error.message}")
            return jsonify({"success": False, "error": f"Error al eliminar el grupo: {deleted_group_res.error.message}"}), 500
        
        if not deleted_group_res.data and not (hasattr(deleted_group_res, 'error') and deleted_group_res.error):
            # Si no hay datos Y no hay error, podría significar que la RLS lo previno silenciosamente o ya no existía
            # (aunque la comprobación inicial debería haberlo detectado).
            # Supabase delete() devuelve los registros eliminados. Si está vacío, es posible que no se haya eliminado nada.
             print(f"Advertencia: La eliminación del grupo {group_id} no devolvió datos y no reportó error explícito.")
             # Podríamos tratar esto como un error o no, dependiendo de la expectativa.
             # Por seguridad, si no hay datos, asumimos que algo no fue como se esperaba, a menos que la RLS sea la causa.
             # return jsonify({"success": False, "error": "El grupo no pudo ser eliminado o ya no existía."}), 404


        return jsonify({"success": True, "message": "Grupo eliminado correctamente"})

    except Exception as e:
        print(f"Error en delete_group (group_id: {group_id_str}): {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# --- FIN ENDPOINTS DE GRUPOS DE USUARIOS ---

def check_url_with_policies(url):
    try:
        print(f"[Backend] Iniciando verificación de políticas para URL: {url}")
        # Normalizar el dominio
        domain = normalize_domain(url)
        if not domain:
            print("[Backend] Error: URL inválida después de normalización")
            return False, "URL inválida"

        # Obtener el token JWT y claims
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not jwt_token:
            print("[Backend] Error: No se encontró token JWT")
            return False, "No autorizado"

        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        user_id = claims.get('sub')  # Usar sub en lugar de user_id
        print(f"[Backend] Verificando para usuario: {user_id}, rol: {role}, tenant: {tenant_id}")

        # Obtener conexión a Supabase
        user_supabase = get_supabase_with_jwt(jwt_token)

        # 1. Verificar políticas específicas del tenant y grupos
        if role == 'user':
            print("[Backend] Verificando políticas para usuario normal")
            try:
                # Obtener políticas del tenant sin grupo
                tenant_policies = user_supabase.table('policies').select('*').eq('tenant_id', tenant_id).is_('group_id', 'null').execute()
                print(f"[Backend] Políticas del tenant: {len(tenant_policies.data)} encontradas")
                
                # Intentar obtener grupos del usuario, pero no fallar si la tabla no existe
                user_groups = []
                try:
                    user_groups_res = user_supabase.table('group_users').select('group_id').eq('user_id', user_id).execute()
                    user_groups = [g['group_id'] for g in user_groups_res.data] if user_groups_res.data else []
                    print(f"[Backend] Grupos del usuario: {user_groups}")
                except Exception as e:
                    print(f"[Backend] No se pudo obtener grupos del usuario (puede que la tabla no exista): {str(e)}")
                
                # Obtener políticas de los grupos del usuario si hay grupos
                group_policies = []
                if user_groups:
                    try:
                        group_policies = user_supabase.table('policies').select('*').in_('group_id', user_groups).execute().data
                        print(f"[Backend] Políticas de grupos: {len(group_policies)} encontradas")
                    except Exception as e:
                        print(f"[Backend] Error al obtener políticas de grupos: {str(e)}")
                
                # Combinar y filtrar políticas para el dominio
                all_policies = tenant_policies.data + group_policies
                domain_policies = [p for p in all_policies if p['domain'] == domain]
                print(f"[Backend] Políticas específicas para el dominio: {len(domain_policies)} encontradas")
            except Exception as e:
                print(f"[Backend] Error al obtener políticas: {str(e)}")
                raise Exception(f"Error al obtener políticas: {str(e)}")
        else:
            print("[Backend] Verificando políticas para rol administrativo")
            try:
                # Para client y admin, solo verificar políticas del tenant
                domain_policies = user_supabase.table('policies').select('*').eq('tenant_id', tenant_id).eq('domain', domain).execute().data
                print(f"[Backend] Políticas del tenant para el dominio: {len(domain_policies)} encontradas")
            except Exception as e:
                print(f"[Backend] Error al obtener políticas: {str(e)}")
                raise Exception(f"Error al obtener políticas: {str(e)}")

        if domain_policies:
            print("[Backend] Analizando políticas encontradas")
            # Si hay políticas específicas, usar la más restrictiva
            for policy in domain_policies:
                if policy['action'] == 'block':
                    print(f"[Backend] Dominio bloqueado por política: {policy}")
                    return True, {
                        "reason": "policy_violation",
                        "policy_details": policy
                    }
            print("[Backend] Dominio permitido por políticas")
            return False, None

        # 2. Verificar configuración del tenant
        print("[Backend] Verificando configuración del tenant")
        try:
            tenant_config = user_supabase.table('tenant_configs').select('*').eq('tenant_id', tenant_id).maybe_single().execute()
            
            if tenant_config and tenant_config.data:
                config = tenant_config.data
                if domain in config.get('blocked_domains', []):
                    print(f"[Backend] Dominio bloqueado por configuración del tenant: {domain}")
                    return True, {
                        "reason": "tenant_config",
                        "config_details": {"type": "blocked_domains"}
                    }
                if domain in config.get('allowed_domains', []):
                    print(f"[Backend] Dominio permitido por configuración del tenant: {domain}")
                    return False, None
            else:
                print("[Backend] No se encontró configuración del tenant, continuando con verificación global")
        except Exception as e:
            print(f"[Backend] Error al verificar configuración del tenant: {str(e)}")
            print("[Backend] Continuando con verificación global")

        # 3. Verificar lista global de sitios prohibidos
        print("[Backend] Verificando lista global de sitios prohibidos")
        try:
            prohibited_categories = load_prohibited_sites()
            # Verificar si el dominio está en alguna categoría prohibida
            for category, sites in prohibited_categories.items():
                if domain in sites:
                    print(f"[Backend] Dominio encontrado en categoría prohibida: {category}")
                    return True, {
                        "reason": "prohibited_site",
                        "site_details": {"category": category}
                    }
        except Exception as e:
            print(f"[Backend] Error al verificar lista de sitios prohibidos: {str(e)}")
            raise Exception(f"Error al verificar lista de sitios prohibidos: {str(e)}")

        print(f"[Backend] Dominio permitido: {domain}")
        return False, None

    except Exception as e:
        print(f"[Backend] Error en check_url_with_policies: {str(e)}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error en verificación de políticas: {str(e)}")

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host='0.0.0.0', port=port) 