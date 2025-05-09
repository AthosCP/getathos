from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from uuid import UUID
from datetime import datetime, timedelta
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token, get_jwt, verify_jwt_in_request
from supabase.lib.client_options import ClientOptions

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
# Configuración de JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Token nunca expira
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'
jwt = JWTManager(app)

print("JWT_SECRET_KEY:", app.config['JWT_SECRET_KEY'])

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
            "https://www.getathos.com"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

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
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        # Autenticación con Supabase
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if hasattr(response, 'session') and response.session:
            # Crear token JWT personalizado
            tenant_id = response.user.user_metadata.get('tenant_id')
            role = response.user.user_metadata.get('role')

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
            print(f"User metadata: {response.user.user_metadata}")
            print(f"Generated JWT claims: {claims}")
            
            # Crear el token con los claims
            access_token = create_access_token(
                identity=response.user.id,
                additional_claims=claims
            )
            
            return jsonify({
                "success": True,
                "access_token": access_token,
                "user": response.user.email,
                "user_id": response.user.id,
                "role": role
            })
        else:
            return jsonify({
                "success": False,
                "error": "Credenciales inválidas"
            }), 401
    except Exception as e:
        print(f"Error en login: {str(e)}")
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
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No token provided"}), 401

        user = supabase.auth.get_user(auth_header.split(' ')[1])
        role = user.user.user_metadata.get('role')
        if role != 'superadmin':
            return jsonify({"error": "Unauthorized"}), 403

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
    claims = get_jwt()
    role = claims.get('role')
    tenant_id = claims.get('tenant_id')
    supabase_token = claims.get('supabase_token')
    jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_supabase = get_supabase_with_jwt(jwt_token)
    if role == 'admin':
        users = user_supabase.table('users').select('*').execute()
    elif role == 'client':
        users = user_supabase.table('users').select('*').eq('tenant_id', tenant_id).eq('role', 'user').execute()
    else:
        return jsonify({"error": "No autorizado"}), 403
    return jsonify({"success": True, "data": users.data})

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
def create_user():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No token provided"}), 401

        # Verificar el token y obtener el usuario
        admin = supabase.auth.get_user(auth_header.split(' ')[1])
        role = admin.user.user_metadata.get('role')
        tenant_id = admin.user.user_metadata.get('tenant_id')

        data = request.get_json()

        # Forzar tenant_id según el rol
        if role == 'client':
            data['tenant_id'] = tenant_id
        # Si es admin global, puede crear en cualquier tenant (usa el que venga del frontend)

        # Crear usuario en Supabase Auth
        auth_response = supabase.auth.admin.create_user({
            "email": data.get('email'),
            "password": data.get('password'),
            "email_confirm": True,
            "user_metadata": {
                "role": data.get('role', 'user'),
                "tenant_id": data.get('tenant_id')
            }
        })

        # Crear usuario en la tabla users
        user_data = {
            "id": auth_response.user.id,
            "email": data.get('email'),
            "role": data.get('role', 'user'),
            "tenant_id": data.get('tenant_id'),
        }

        new_user = supabase.table('users').insert(user_data).execute()

        user = new_user.data[0]
        user['tenant_name'] = supabase.table('tenants').select('name').eq('id', tenant_id).execute().data[0]['name'] if tenant_id else ''
        # Actualizar el conteo de usuarios del tenant
        supabase.table('tenants').update({
            'users_count': len(supabase.table('users').select('id').eq('tenant_id', tenant_id).execute().data)
        }).eq('id', tenant_id).execute()
        return jsonify({
            "success": True,
            "data": user
        })
    except Exception as e:
        print(f"Error en create_user: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No token provided"}), 401

        user = supabase.auth.get_user(auth_header.split(' ')[1])
        role = user.user.user_metadata.get('role')
        tenant_id = user.user.user_metadata.get('tenant_id')

        data = request.get_json()

        # Solo admin puede editar cualquier usuario, client solo los de su tenant
        user_data = supabase.table('users').select('*').eq('id', user_id).execute()
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

        # Actualizar usuario en la tabla users
        updated_user = supabase.table('users').update({
            "role": data.get('role'),
            "tenant_id": data.get('tenant_id')
        }).eq('id', user_id).execute()

        if not updated_user.data:
            return jsonify({"error": "Usuario no encontrado"}), 404

        return jsonify({
            "success": True,
            "data": updated_user.data[0]
        })
    except Exception as e:
        print(f"Error en update_user: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No token provided"}), 401

        user = supabase.auth.get_user(auth_header.split(' ')[1])
        role = user.user.user_metadata.get('role')
        tenant_id = user.user.user_metadata.get('tenant_id')

        # Solo admin puede eliminar cualquier usuario, client solo los de su tenant
        user_data = supabase.table('users').select('*').eq('id', user_id).execute()
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
    claims = get_jwt()
    role = claims.get('role')
    tenant_id = claims.get('tenant_id')
    action = request.args.get('action')
    
    # Agregar logs para depuración
    print(f"GET /api/policies - JWT claims: {claims}")
    print(f"Role: {role}, Tenant ID: {tenant_id}")
    
    jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # Crear cliente Supabase con JWT para que respete RLS
    user_supabase = get_supabase_with_jwt(jwt_token)
    
    query = user_supabase.table('policies').select('*')
    
    if role == 'admin':
        print("Usuario es admin, puede ver todas las políticas")
        pass
    elif role in ['client', 'user']:  # Permitir también a usuarios regulares
        print(f"Usuario es {role}, filtrando por tenant_id: {tenant_id}")
        query = query.eq('tenant_id', tenant_id)
    else:
        print(f"Rol no autorizado: {role}")
        return jsonify({"error": "No autorizado"}), 403
        
    if action:
        query = query.eq('action', action)
        
    try:
        policies = query.execute()
        print(f"Políticas encontradas: {len(policies.data)}")
        return jsonify({"success": True, "data": policies.data})
    except Exception as e:
        error_msg = str(e)
        print(f"Error al obtener políticas: {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/api/policies', methods=['POST'])
@jwt_required()
def create_policy():
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        data = request.get_json()
        
        print("Intentando crear política con datos:", data)
        print("Claims JWT:", claims)
        
        if role == 'client':
            data['tenant_id'] = tenant_id
        elif role == 'admin':
            if not data.get('tenant_id'):
                return jsonify({"error": "Falta tenant_id"}), 400
        else:
            return jsonify({"error": "No autorizado"}), 403
            
        # Validar acción
        if data.get('action') not in ['allow', 'block']:
            return jsonify({"error": "Acción inválida"}), 400
            
        # Insertar política
        new_policy = supabase.table('policies').insert({
            'tenant_id': data['tenant_id'],
            'domain': data['domain'],
            'action': data['action']
        }).execute()
        
        return jsonify({"success": True, "data": new_policy.data[0]})
    except Exception as e:
        print(f"Error en create_policy: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/policies/<policy_id>', methods=['PUT'])
@jwt_required()
def update_policy(policy_id):
    try:
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        
        data = request.get_json()
        
        # Verificar permisos
        if role == 'client':
            # Verificar que la política pertenece al tenant
            policy = supabase.table('policies').select('*').eq('id', policy_id).eq('tenant_id', tenant_id).execute()
            if not policy.data:
                return jsonify({"error": "No autorizado"}), 403
        elif role != 'admin':
            return jsonify({"error": "No autorizado"}), 403
            
        # Validar acción
        if data.get('action') not in ['allow', 'block']:
            return jsonify({"error": "Acción inválida"}), 400
            
        # Actualizar política
        updated_policy = supabase.table('policies').update({
            'domain': data['domain'],
            'action': data['action']
        }).eq('id', policy_id).execute()
        
        return jsonify({"success": True, "data": updated_policy.data[0]})
    except Exception as e:
        print(f"Error en update_policy: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/policies/<policy_id>', methods=['DELETE'])
@jwt_required()
def delete_policy(policy_id):
    try:
        # Obtener claims del JWT
        claims = get_jwt()
        role = claims.get('role')
        tenant_id = claims.get('tenant_id')
        
        # Logs para depuración
        print(f"DELETE /api/policies/{policy_id} - JWT claims: {claims}")
        print(f"Role: {role}, Tenant ID: {tenant_id}")
        
        # Usar el token para crear un cliente Supabase con JWT
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        # Obtener política usando el cliente con JWT
        policy = user_supabase.table('policies').select('*').eq('id', policy_id).execute()
        
        if not policy.data:
            return jsonify({"error": "Política no encontrada"}), 404
            
        target_policy = policy.data[0]
        
        # Verificar permisos basados en rol
        if role == 'admin':
            print("Usuario es admin, puede eliminar cualquier política")
            pass
        elif role == 'client':
            print(f"Usuario es client, verificando tenant_id: {tenant_id} vs política: {target_policy.get('tenant_id')}")
            if target_policy.get('tenant_id') != tenant_id:
                return jsonify({"error": "No autorizado"}), 403
        else:
            print(f"Rol no autorizado: {role}")
            return jsonify({"error": "No autorizado"}), 403
            
        # Eliminar política usando el cliente con JWT
        deleted = user_supabase.table('policies').delete().eq('id', policy_id).execute()
        print(f"Política eliminada: {policy_id}")
        
        return jsonify({"success": True, "message": "Política eliminada"})
    except Exception as e:
        error_msg = str(e)
        print(f"Error en delete_policy: {error_msg}")
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

@app.route('/api/navigation_logs', methods=['POST'])
@jwt_required()
def create_navigation_log():
    try:
        # Obtener datos del JWT
        claims = get_jwt()
        user_id = claims.get('sub')  # ID del usuario desde el JWT
        tenant_id = claims.get('tenant_id')
        
        # Obtener el token JWT para pasar a Supabase
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_supabase = get_supabase_with_jwt(jwt_token)
        
        # Obtener datos del request
        data = request.get_json()
        domain = data.get('domain')
        url = data.get('url')
        timestamp = data.get('timestamp') or datetime.utcnow().isoformat()
        action = data.get('action')
        policy_info = None
        
        print(f"Registrando navegación: {domain} ({action}) por usuario {user_id}")

        # Si la acción es "bloqueado", buscar la política activa
        if action == 'bloqueado':
            policy_query = user_supabase.table('policies').select('*')
            if tenant_id:
                policy_query = policy_query.eq('tenant_id', tenant_id)
            policy_query = policy_query.eq('domain', domain).eq('action', 'block')
            policy = policy_query.execute()
            
            if policy.data:
                p = policy.data[0]
                policy_info = {
                    "policy_id": p.get('id'),
                    "action": p.get('action'),
                    "created_at": p.get('created_at')
                }

        # Insertar el registro en navigation_logs
        log_data = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "domain": domain,
            "url": url,
            "timestamp": timestamp,
            "action": action,
            "policy_info": policy_info
        }
        
        # Log para depuración
        print(f"Datos de log a insertar: {log_data}")
        
        # Usar user_supabase en lugar de supabase para respetar RLS
        new_log = user_supabase.table('navigation_logs').insert(log_data).execute()
        return jsonify({"success": True, "data": new_log.data[0]})
    except Exception as e:
        print(f"Error en create_navigation_log: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

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

# --- ENDPOINT: DASHBOARD ---
@app.route('/api/admin/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def admin_dashboard():
    try:
        # Total de clientes
        tenants = supabase.table('tenants').select('*').execute().data
        total_clients = len(tenants)
        # Total de usuarios
        users = supabase.table('users').select('*').execute().data
        total_users = len(users)
        # Clientes activos
        active_clients = len([t for t in tenants if t.get('status') == 'active'])
        # Usuarios activos
        active_users = len([u for u in users if u.get('status') == 'active'])
        # Últimos 5 clientes
        recent_clients = sorted(tenants, key=lambda t: t.get('created_at', ''), reverse=True)[:5]
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
        return jsonify({"success": False, "error": str(e)})

# --- ENDPOINTS: CLIENTES (TENANTS) ---
@app.route('/api/admin/clients', methods=['GET'])
@jwt_required()
@admin_required
def admin_get_clients():
    try:
        tenants = supabase.table('tenants').select('*').execute().data
        return jsonify({"success": True, "data": tenants})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/clients', methods=['POST'])
@jwt_required()
@admin_required
def admin_create_client():
    try:
        data = request.get_json()
        tenant = supabase.table('tenants').insert({
            'name': data.get('name'),
            'description': data.get('description'),
            'max_users': data.get('max_users', 10),
            'status': 'active',
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
        users = supabase.table('users').select('*').execute().data
        # Enriquecer con nombre del tenant
        tenants = {t['id']: t['name'] for t in supabase.table('tenants').select('id,name').execute().data}
        for u in users:
            u['tenant_name'] = tenants.get(u.get('tenant_id'), '')
        return jsonify({"success": True, "data": users})
    except Exception as e:
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
        # Validar límite de usuarios
        tenant = supabase.table('tenants').select('id, max_users').eq('id', tenant_id).execute().data
        if not tenant:
            return jsonify({"success": False, "error": "Cliente (tenant) no encontrado"}), 404
        max_users = tenant[0].get('max_users', 0)
        current_users = supabase.table('users').select('id').eq('tenant_id', tenant_id).execute().data
        if len(current_users) >= max_users:
            return jsonify({"success": False, "error": f"El cliente ha alcanzado el límite máximo de usuarios ({max_users})."}), 400
        # Crear usuario en Supabase Auth y en la tabla users
        auth_user = supabase.auth.admin.create_user({
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {'role': role, 'tenant_id': tenant_id}
        })
        user = supabase.table('users').insert({
            'id': auth_user.user.id,
            'email': email,
            'role': role,
            'tenant_id': tenant_id,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }).execute().data[0]
        user['tenant_name'] = supabase.table('tenants').select('name').eq('id', tenant_id).execute().data[0]['name'] if tenant_id else ''
        # Actualizar el conteo de usuarios del tenant
        supabase.table('tenants').update({
            'users_count': len(supabase.table('users').select('id').eq('tenant_id', tenant_id).execute().data)
        }).eq('id', tenant_id).execute()
        return jsonify({"success": True, "data": user})
    except Exception as e:
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
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 