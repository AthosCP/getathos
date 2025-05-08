from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Obtener todos los tenant_id válidos
tenants = supabase.table('tenants').select('id').execute().data
tenant_ids = {t['id'] for t in tenants}

# Obtener todos los usuarios de Auth
users_auth = supabase.auth.admin.list_users()
# Obtener todos los usuarios de la tabla users
users_db = supabase.table('users').select('*').execute().data
db_dict = {u['id']: u for u in users_db}

# Crear los usuarios faltantes en la tabla users
for auth_user in users_auth:
    user_id = auth_user.id
    meta = auth_user.user_metadata
    role_auth = meta.get('role')
    tenant_auth = meta.get('tenant_id')
    email = auth_user.email
    if user_id not in db_dict:
        if tenant_auth not in tenant_ids:
            print(f"NO SE PUEDE CREAR usuario {user_id} ({email}): tenant_id {tenant_auth} NO existe en la tabla tenants.")
            continue
        print(f"Creando usuario {user_id} ({email}) en la tabla users...")
        supabase.table('users').insert({
            "id": user_id,
            "email": email,
            "role": role_auth,
            "tenant_id": tenant_auth,
            "created_at": datetime.now().isoformat()
        }).execute()

print("Sincronización completada: usuarios de Auth ahora existen en la tabla users (solo con tenant válido).")

# Lista de tenant_id huérfanos detectados manualmente (puedes automatizarlo si quieres)
tenant_ids_faltantes = [
    "87a3c50c-d932-4383-8dc6-5db3630bf0f0",
    "1b64330a-5f8f-4722-a248-0e9b564f540d",
    "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
]

for tid in tenant_ids_faltantes:
    print(f"Creando tenant {tid}...")
    supabase.table('tenants').insert({
        "id": tid,
        "name": f"Tenant {tid[:8]}",
        "description": "Creado automáticamente para sincronización"
    }).execute()

print("Tenants faltantes creados.")

print("JWT claims:", claims)