from supabase import create_client
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# === USUARIOS DE EXTENSIÓN A CREAR ===
extension_users = [
    {
        "email": "usuario1.extension@empresa1.com",
        "password": "Athos2024!",
        "role": "user",
        "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"
    },
    {
        "email": "usuario2.extension@empresa1.com",
        "password": "Athos2024!",
        "role": "user",
        "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"
    },
    {
        "email": "usuario3.extension@empresa1.com",
        "password": "Athos2024!",
        "role": "user",
        "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"
    },
    {
        "email": "usuario4.extension@empresa1.com",
        "password": "Athos2024!",
        "role": "user",
        "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"
    },
    {
        "email": "usuario5.extension@empresa1.com",
        "password": "Athos2024!",
        "role": "user",
        "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"
    }
]
# ================================

usuarios = [
    {
        "user_id": "b828d6e2-d82c-4ca1-822e-a8424cde051d",
        "metadata": {"role": "user", "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"}
    },
    {
        "user_id": "d8c4c4a0-9d06-49b2-bf65-c7af7ae32e99",
        "metadata": {"role": "user", "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"}
    },
    {
        "user_id": "e06cf433-37dd-4519-8881-179d3e43dee7",
        "metadata": {"role": "user", "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"}
    },
    {
        "user_id": "8f72635b-203a-4760-9e82-461d9717c960",
        "metadata": {"role": "user", "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"}
    },
    {
        "user_id": "aa78cf81-1144-4bb4-a0fe-50632a6014a8",
        "metadata": {"role": "user", "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"}
    },
    {
        "user_id": "a864a62b-fc9e-4838-a099-1d331b7819e8",
        "metadata": {"role": "client", "tenant_id": "1b64330a-5f8f-4722-a248-0e9b564f540d"}
    }
]

for usuario in usuarios:
    print(f"Actualizando usuario {usuario['user_id']} con metadatos {usuario['metadata']}")
    response = supabase.auth.admin.update_user_by_id(
        usuario["user_id"],
        attributes={"user_metadata": usuario["metadata"]}
    )
    print("Respuesta de Supabase:", response)

for user in extension_users:
    print(f"Creando usuario {user['email']} en Supabase Auth...")
    response = supabase.auth.admin.create_user({
        "email": user["email"],
        "password": user["password"],
        "email_confirm": True,
        "user_metadata": {
            "role": user["role"],
            "tenant_id": user["tenant_id"]
        }
    })
    print("Respuesta de Supabase:", response)
    # Sincronizar con tabla users si es necesario (opcional, ya están insertados) 