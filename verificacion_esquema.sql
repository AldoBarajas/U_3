-- Ejecutar despues de schema.sql. Consultas para evidencias de pgAdmin/psql.
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'biblioteca' AND table_type = 'BASE TABLE' ORDER BY table_name;
SELECT count(*) AS total_tablas
FROM information_schema.tables
WHERE table_schema = 'biblioteca' AND table_type = 'BASE TABLE'; -- 12
SELECT constraint_type, count(*) AS cantidad
FROM information_schema.table_constraints
WHERE table_schema = 'biblioteca'
GROUP BY constraint_type ORDER BY constraint_type;
SELECT tc.table_name, tc.constraint_name, kcu.column_name,
       ccu.table_name AS tabla_referenciada, ccu.column_name AS columna_referenciada
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
 ON tc.constraint_name = kcu.constraint_name AND tc.constraint_schema = kcu.constraint_schema
JOIN information_schema.constraint_column_usage ccu
 ON tc.constraint_name = ccu.constraint_name AND tc.constraint_schema = ccu.constraint_schema
WHERE tc.table_schema = 'biblioteca' AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position;
-- Lista de indices especiales y triggers diferibles (incluye triggers internos del gestor).
SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='biblioteca' ORDER BY tablename,indexname;
SELECT event_object_table, trigger_name, action_timing, event_manipulation
FROM information_schema.triggers WHERE trigger_schema = 'biblioteca'
ORDER BY event_object_table,trigger_name;
SELECT * FROM biblioteca.vw_disponibilidad ORDER BY id_ejemplar;
SELECT * FROM biblioteca.vw_prestamo_atraso ORDER BY id_prestamo;
SELECT * FROM biblioteca.vw_libro_antiguedad ORDER BY isbn;
