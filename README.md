# Unidad 3 · Modelo relacional | Biblioteca escolar

**Alumno:** Aldo Alberto Barajas Ancira · **No. control:** I24050397  
**Asignatura:** Fundamentos de Bases de Datos · **Docente:** Rubén Riojas  
**Fecha:** 7 de noviembre de 2026

## Relación con Unidad 2
La misma biblioteca escolar del modelo E-R/E-RE anterior, sin cambiar el caso de estudio ni el proyecto integrador de ferretería.

## Entregables
- `Tarea_3_1/Tarea_3_1_Transformacion_ER_a_Relacional.pdf`: reporte formal de tuplas, atributos, dominios, integridad y mapeo E-R a 12 tablas.
- `Tarea_3_2/Tarea_3_2_Esquema_Fisico_y_DDL.pdf`: reporte técnico, diccionario completo, política de cascadas y protocolo de validación.
- `SQL/schema.sql`: DDL para **PostgreSQL 14+**, crea esquema `biblioteca`, 12 tablas, 11 FK, CHECK, UNIQUE, triggers e índices y vistas.
- `SQL/datos_ejemplo.sql`: datos mínimos ficticios, ejecutarlos en BD recién creada.
- `SQL/verificacion_esquema.sql`: consultas para inventario de tablas, FKs, índices y vistas.
- `SQL/pruebas_integridad.sql`: 8 pruebas negativas con resultados verificables.
- `SQL/reset_SOLO_LABORATORIO.sql`: elimina todo el esquema; úsalo **solo** si es un entorno desechable.
- `Diagramas_Editables/*.drawio`: editables en https://app.diagrams.net.
- `Diagramas_Exportados`: SVG, PNG, PDF vectorial y DOT.
- `Validacion/resultado_validacion_estatica.txt`: controles estructurales realizados durante la preparación.
- `Guias/GUIA_GITHUB_YOUTUBE_Y_EVIDENCIAS.md`: cómo entregar los enlaces y grabar los videos.

## Orden de ejecución
1. Crear una base PostgreSQL vacía: `biblioteca_unidad3`.
2. Ejecutar `schema.sql` una sola vez.
3. Ejecutar `verificacion_esquema.sql` y comprobar 12 tablas.
4. Ejecutar `datos_ejemplo.sql`.
5. Ejecutar `pruebas_integridad.sql` y conservar los mensajes `NOTICE: OK`.
6. Generar un ERD desde pgAdmin (o CASE conectado a PostgreSQL), obtener las capturas y completar las evidencias del reporte 3.2.

En `psql` (desde la carpeta de repositorio):
```shell
psql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/schema.sql
psql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/verificacion_esquema.sql
psql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/datos_ejemplo.sql
psql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/pruebas_integridad.sql
```

**Sobre el estado de verificación:** el DDL fue revisado con un validador estático propio; **no ha sido ejecutado contra un servidor PostgreSQL en este entorno**. No se fabricaron capturas de ejecución. La ejecución y el ERD del SGBD deben hacerse en tu computadora para satisfacer el criterio de evidencias.

**Pendiente del alumno:** publicar el proyecto en su repositorio público GitHub y grabar dos videos públicos en el mismo canal YouTube con pantalla y webcam inferior derecha.
