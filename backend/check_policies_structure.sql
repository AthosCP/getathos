-- Verificar la estructura de la tabla policies
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM 
    information_schema.columns 
WHERE 
    table_name = 'policies'
ORDER BY 
    ordinal_position;

-- Verificar las restricciones de la tabla
SELECT 
    tc.constraint_name, 
    tc.constraint_type,
    cc.check_clause
FROM 
    information_schema.table_constraints tc
LEFT JOIN 
    information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
WHERE 
    tc.table_name = 'policies';

-- Verificar si hay políticas de descarga existentes
SELECT 
    id,
    tenant_id,
    user_id,
    group_id,
    domain,
    action,
    type,
    created_at
FROM 
    policies 
WHERE 
    type = 'download'; 