-- Crear extensión para UUID si no existe
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear tabla de tenants si no existe
CREATE TABLE IF NOT EXISTS tenants (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Crear tabla de configuraciones de tenant si no existe
CREATE TABLE IF NOT EXISTS tenant_configs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    blocked_domains TEXT[] DEFAULT '{}',
    allowed_domains TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Crear tabla de usuarios si no existe
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Tabla de políticas de acceso por tenant
CREATE TABLE IF NOT EXISTS policies (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    action TEXT CHECK (action IN ('allow', 'block')) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Tabla de historial de navegación
CREATE TABLE IF NOT EXISTS navigation_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    url TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    action TEXT CHECK (action IN ('visitado', 'bloqueado', 'permitido')) NOT NULL,
    policy_info JSONB DEFAULT NULL
);

-- Habilitar RLS en las tablas
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Eliminar políticas existentes si existen
DROP POLICY IF EXISTS "Los administradores pueden ver todos los tenants" ON tenants;
DROP POLICY IF EXISTS "Los usuarios pueden ver las configuraciones de su tenant" ON tenant_configs;
DROP POLICY IF EXISTS "Los usuarios pueden ver otros usuarios de su tenant" ON users;

-- Crear nuevas políticas
CREATE POLICY "Los administradores pueden ver todos los tenants"
    ON tenants FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY "Los usuarios pueden ver las configuraciones de su tenant"
    ON tenant_configs FOR SELECT
    USING (
        tenant_id IN (
            SELECT tenant_id FROM users
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Los usuarios pueden ver otros usuarios de su tenant"
    ON users FOR SELECT
    USING (
        tenant_id IN (
            SELECT tenant_id FROM users
            WHERE id = auth.uid()
        )
    );

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_tenant_id ON tenant_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Habilitar RLS en la tabla policies
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;

-- Política para permitir a los usuarios ver las políticas de su tenant
DROP POLICY IF EXISTS "Permitir lectura de policies por tenant" ON policies;
CREATE POLICY "Permitir lectura de policies por tenant"
ON policies
FOR SELECT
USING (
  tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
);

-- Política para permitir a los administradores ver todas las políticas
DROP POLICY IF EXISTS "Administradores ven todas las policies" ON policies;
CREATE POLICY "Administradores ven todas las policies"
ON policies
FOR SELECT
USING (
  (auth.jwt() ->> 'role')::text = 'admin'
);

-- Política para permitir a los clientes crear políticas en su tenant
DROP POLICY IF EXISTS "Clientes crean policies en su tenant" ON policies;
CREATE POLICY "Clientes crean policies en su tenant"
ON policies
FOR INSERT
WITH CHECK (
  tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
  AND (auth.jwt() ->> 'role')::text = 'client'
);

-- Política para permitir a los administradores crear políticas
DROP POLICY IF EXISTS "Administradores crean policies" ON policies;
CREATE POLICY "Administradores crean policies"
ON policies
FOR INSERT
WITH CHECK (
  (auth.jwt() ->> 'role')::text = 'admin'
);

-- Política para permitir a los clientes actualizar políticas de su tenant
DROP POLICY IF EXISTS "Clientes actualizan policies de su tenant" ON policies;
CREATE POLICY "Clientes actualizan policies de su tenant"
ON policies
FOR UPDATE
USING (
  tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
  AND (auth.jwt() ->> 'role')::text = 'client'
);

-- Política para permitir a los administradores actualizar políticas
DROP POLICY IF EXISTS "Administradores actualizan policies" ON policies;
CREATE POLICY "Administradores actualizan policies"
ON policies
FOR UPDATE
USING (
  (auth.jwt() ->> 'role')::text = 'admin'
);

-- Política para permitir a los clientes eliminar políticas de su tenant
DROP POLICY IF EXISTS "Clientes eliminan policies de su tenant" ON policies;
CREATE POLICY "Clientes eliminan policies de su tenant"
ON policies
FOR DELETE
USING (
  tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
  AND (auth.jwt() ->> 'role')::text = 'client'
);

-- Política para permitir a los administradores eliminar políticas
DROP POLICY IF EXISTS "Administradores eliminan policies" ON policies;
CREATE POLICY "Administradores eliminan policies"
ON policies
FOR DELETE
USING (
  (auth.jwt() ->> 'role')::text = 'admin'
); 