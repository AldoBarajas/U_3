-- Datos reproducibles: SOLO ejecutar despues de schema.sql en una BD vacia.
BEGIN;
SET search_path TO biblioteca, public;
INSERT INTO persona (id_persona, nombres, apellido_paterno, correo, tipo_persona)
VALUES (1,'Ana','Torres','ana.torres@ejemplo.edu','ESTUDIANTE'),
       (2,'Luis','Gomez','luis.gomez@ejemplo.edu','DOCENTE');
INSERT INTO estudiante (id_persona, matricula, semestre)
VALUES (1,'MAT-2026-001',5);
INSERT INTO docente (id_persona, numero_empleado, departamento)
VALUES (2,'EMP-0001','Ingenieria');
INSERT INTO persona_telefono VALUES (1,'8661234567'), (1,'8661234568');
INSERT INTO autor (id_autor,nombre) VALUES (1,'Autora de ejemplo'),(2,'Coautor de ejemplo');
INSERT INTO libro (isbn,titulo,anio_publicacion) VALUES ('9786070000001','Fundamentos de bases de datos',2023);
INSERT INTO libro_autor (isbn,id_autor) VALUES ('9786070000001',1),('9786070000001',2);
INSERT INTO coleccion (id_coleccion,nombre) VALUES (1,'Tecnologia');
INSERT INTO libro_coleccion VALUES ('9786070000001',1);
INSERT INTO ejemplar (id_ejemplar,isbn,codigo_inventario,estado)
VALUES (1,'9786070000001','INV-001','DISPONIBLE'),
       (2,'9786070000001','INV-002','EN_REPARACION');
INSERT INTO prestamo (id_prestamo,id_persona,id_ejemplar,fecha_salida,fecha_limite)
VALUES (1,1,1,DATE '2026-11-02',DATE '2026-11-16');
INSERT INTO incidencia (id_incidencia,id_prestamo,tipo,fecha,observacion)
VALUES (1,1,'OTRA',DATE '2026-11-03','Ejemplo de observacion para verificar vinculo historico');
-- Adelanta secuencias de identidad despues de insertar IDs explicitos (solo laboratorio).
SELECT setval(pg_get_serial_sequence('biblioteca.persona','id_persona'), 2, true);
SELECT setval(pg_get_serial_sequence('biblioteca.autor','id_autor'), 2, true);
SELECT setval(pg_get_serial_sequence('biblioteca.coleccion','id_coleccion'), 1, true);
SELECT setval(pg_get_serial_sequence('biblioteca.ejemplar','id_ejemplar'), 2, true);
SELECT setval(pg_get_serial_sequence('biblioteca.prestamo','id_prestamo'), 1, true);
SELECT setval(pg_get_serial_sequence('biblioteca.incidencia','id_incidencia'), 1, true);
COMMIT;
