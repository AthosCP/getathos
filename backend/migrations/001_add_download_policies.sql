-- Agregar campos necesarios para políticas de descarga
ALTER TABLE policies 
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS type TEXT CHECK (type IN ('access', 'download')) NOT NULL DEFAULT 'access';

-- Modificar la restricción de dominio para permitir NULL en políticas de descarga
ALTER TABLE policies 
    ALTER COLUMN domain DROP NOT NULL;

-- Agregar restricciones para políticas de descarga
ALTER TABLE policies 
    DROP CONSTRAINT IF EXISTS unique_domain_per_tenant_group,
    ADD CONSTRAINT unique_domain_per_tenant_group UNIQUE (domain, tenant_id, group_id) WHERE domain IS NOT NULL,
    ADD CONSTRAINT unique_user_policy UNIQUE (tenant_id, user_id, type) WHERE user_id IS NOT NULL,
    ADD CONSTRAINT unique_group_policy UNIQUE (tenant_id, group_id, type) WHERE group_id IS NOT NULL,
    ADD CONSTRAINT check_domain_for_access CHECK (type != 'access' OR domain IS NOT NULL); 