from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(dotenv_path="../backend/.env")  # Ajusta la ruta si es necesario

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Email y rol del usuario athos_owner
athos_email = "athos@getathos.com"
athos_role = "athos_owner"

# Buscar usuario en Auth
users_auth = supabase.auth.admin.list_users()
athos_auth = next((u for u in users_auth if u.email == athos_email), None)

if not athos_auth:
    print("No se encontró el usuario en Auth. Crea el usuario primero en el panel de Supabase Auth.")
    exit(1)

user_id = athos_auth.id

# Buscar en la tabla users
users_db = supabase.table('users').select('*').eq('id', user_id).execute().data

if not users_db:
    print(f"Creando usuario {user_id} ({athos_email}) en la tabla users...")
    supabase.table('users').insert({
        "id": user_id,
        "email": athos_email,
        "role": athos_role,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }).execute()
else:
    print(f"Actualizando usuario {user_id} ({athos_email}) en la tabla users...")
    supabase.table('users').update({
        "role": athos_role,
        "status": "active"
    }).eq('id', user_id).execute()

print("Usuario athos_owner sincronizado en la tabla users.")

# (Opcional) Actualizar user_metadata en Auth
print("Actualizando user_metadata en Auth...")
supabase.auth.admin.update_user_by_id(user_id, {
    "user_metadata": {
        "role": athos_role
    }
})
print("user_metadata actualizado.")

print("¡Listo! El usuario athos_owner está correctamente configurado en Auth y en la tabla users.")