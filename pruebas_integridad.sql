-- Pruebas autoevaluadas para PostgreSQL. REQUIERE datos_ejemplo.sql antes.
-- Los bloques manejan errores esperados; cualquier fallo inesperado interrumpe la ejecucion.
SET search_path TO biblioteca, public;

DO $$
DECLARE rechazado BOOLEAN := FALSE;
BEGIN
  BEGIN
    INSERT INTO ejemplar(isbn,codigo_inventario,estado)
    VALUES('9786079999999','INV-FK-ERR','DISPONIBLE');
  EXCEPTION WHEN foreign_key_violation THEN rechazado := TRUE;
  END;
  IF NOT rechazado THEN RAISE EXCEPTION 'FALLO: FK ejemplar/libro'; END IF;
  RAISE NOTICE 'OK: FK ejemplar/libro rechaza inexistentes';
END $$;

DO $$
DECLARE rechazado BOOLEAN := FALSE;
BEGIN
  BEGIN
    INSERT INTO ejemplar(isbn,codigo_inventario,estado)
    VALUES('9786070000001','INV-ERR-EST','NO_PERMITIDO');
  EXCEPTION WHEN check_violation THEN rechazado := TRUE;
  END;
  IF NOT rechazado THEN RAISE EXCEPTION 'FALLO: CHECK estado'; END IF;
  RAISE NOTICE 'OK: CHECK dominio estado';
END $$;

DO $$
DECLARE rechazado BOOLEAN := FALSE;
BEGIN
  BEGIN
    INSERT INTO prestamo(id_persona,id_ejemplar,fecha_salida,fecha_limite)
    VALUES(2,1,DATE '2026-11-04',DATE '2026-11-20');
  EXCEPTION WHEN unique_violation THEN rechazado := TRUE;
  END;
  IF NOT rechazado THEN RAISE EXCEPTION 'FALLO: prestamo activo duplicado'; END IF;
  RAISE NOTICE 'OK: indice unico parcial impide doble prestamo activo';
END $$;

DO $$
DECLARE rechazado BOOLEAN := FALSE;
BEGIN
  BEGIN
    INSERT INTO prestamo(id_persona,id_ejemplar,fecha_salida,fecha_limite)
    VALUES(2,2,DATE '2026-11-10',DATE '2026-11-05');
  EXCEPTION WHEN check_violation THEN rechazado := TRUE;
  END;
  IF NOT rechazado THEN RAISE EXCEPTION 'FALLO: fecha limite anterior'; END IF;
  RAISE NOTICE 'OK: CHECK fechas';
END $$;

DO $$
DECLARE rechazado BOOLEAN := FALSE;
BEGIN
  BEGIN
    DELETE FROM prestamo WHERE id_prestamo = 1;
  EXCEPTION WHEN foreign_key_violation THEN rechazado := TRUE;
  END;
  IF NOT rechazado THEN RAISE EXCEPTION 'FALLO: historial incidencia'; END IF;
  RAISE NOTICE 'OK: RESTRICT preserva prestamo con incidencia';
END $$;

DO $$
DECLARE rechazado BOOLEAN := FALSE;
BEGIN
  BEGIN
    INSERT INTO persona(id_persona,nombres,apellido_paterno,correo,tipo_persona)
    VALUES(90,'Sin','Subtipo','sin.subtipo@ejemplo.edu','ESTUDIANTE');
    SET CONSTRAINTS ALL IMMEDIATE; -- Fuerza el trigger diferible en esta prueba.
  EXCEPTION WHEN check_violation THEN rechazado := TRUE;
  END;
  IF NOT rechazado THEN RAISE EXCEPTION 'FALLO: jerarquia total'; END IF;
  RAISE NOTICE 'OK: jerarquia total requiere un subtipo';
END $$;

DO $$
DECLARE rechazado BOOLEAN := FALSE;
BEGIN
  BEGIN
    INSERT INTO docente(id_persona,numero_empleado,departamento)
    VALUES(1,'EMP-ERR','Direccion'); -- Persona 1 es ESTUDIANTE.
  EXCEPTION WHEN check_violation OR foreign_key_violation THEN rechazado := TRUE;
  END;
  IF NOT rechazado THEN RAISE EXCEPTION 'FALLO: jerarquia disjunta'; END IF;
  RAISE NOTICE 'OK: jerarquia disjunta';
END $$;

DO $$
DECLARE rechazado BOOLEAN := FALSE;
BEGIN
  BEGIN
    INSERT INTO libro(isbn,titulo,anio_publicacion)
    VALUES('9786070000002','Libro sin autoria',2020);
    SET CONSTRAINTS ALL IMMEDIATE;
  EXCEPTION WHEN check_violation THEN rechazado := TRUE;
  END;
  IF NOT rechazado THEN RAISE EXCEPTION 'FALLO: libro sin autor'; END IF;
  RAISE NOTICE 'OK: libro requiere al menos un autor';
END $$;

-- Confirmacion de que las pruebas negativas no alteraron el conjunto valido.
SELECT (SELECT count(*) FROM biblioteca.persona) AS personas,
       (SELECT count(*) FROM biblioteca.libro) AS libros,
       (SELECT count(*) FROM biblioteca.prestamo) AS prestamos,
       (SELECT count(*) FROM biblioteca.incidencia) AS incidencias;
