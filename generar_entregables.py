#!/usr/bin/env python3
"""Recrea los diagramas y reportes de la Unidad 3 a partir del modelo Unidad 2."""
from pathlib import Path
import re, os, html, zipfile, subprocess, tempfile, xml.etree.ElementTree as ET
from collections import Counter
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape, A3
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer, KeepTogether, HRFlowable, Image
from reportlab.pdfgen.canvas import Canvas
import fitz

ROOT=Path(__file__).resolve().parent
DIA=ROOT/'Diagramas_Exportados'; EDIT=ROOT/'Diagramas_Editables'; SQL=ROOT/'SQL'
for d in (DIA,EDIT,ROOT/'Tarea_3_1',ROOT/'Tarea_3_2',ROOT/'Validacion',ROOT/'Guias'): d.mkdir(exist_ok=True)
navy=colors.HexColor('#102740'); teal=colors.HexColor('#007B83'); grey=colors.HexColor('#596A78'); pale=colors.HexColor('#EFF5F7'); bluegrey=colors.HexColor('#DDE7EE'); white=colors.white
pdfmetrics.registerFont(TTFont('DejaVu','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Oblique','/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf'))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold',italic='DejaVu-Oblique',boldItalic='DejaVu-Bold')

# (nombre, tipo PostgreSQL, marcas, definicion)
C={
'persona':[
('id_persona','BIGINT IDENTITY','PK','Identificador general de la persona'),('nombres','VARCHAR(80)','NN','Nombre o nombres'),('apellido_paterno','VARCHAR(80)','NN','Primer apellido'),('apellido_materno','VARCHAR(80)','opcional','Segundo apellido'),('correo','VARCHAR(254)','UQ, NN','Correo unico'),('tipo_persona','VARCHAR(12)','NN, CK','ESTUDIANTE o DOCENTE')],
'estudiante':[
('id_persona','BIGINT','PK, FK, NN','Identidad heredada de Persona'),('tipo_persona','VARCHAR(12)','FK, CK, NN','Discriminador fijo ESTUDIANTE'),('matricula','VARCHAR(20)','UQ, NN','Matricula institucional'),('semestre','SMALLINT','CK, NN','Valor de 1 a 16')],
'docente':[
('id_persona','BIGINT','PK, FK, NN','Identidad heredada de Persona'),('tipo_persona','VARCHAR(12)','FK, CK, NN','Discriminador fijo DOCENTE'),('numero_empleado','VARCHAR(20)','UQ, NN','Numero unico de empleado'),('departamento','VARCHAR(100)','CK, NN','Area de adscripcion')],
'persona_telefono':[
('id_persona','BIGINT','PK, FK, NN','Persona titular del telefono'),('telefono','VARCHAR(20)','PK, CK, NN','Numero telefonico; varias filas por persona')],
'libro':[
('isbn','VARCHAR(17)','PK, CK','ISBN-10 o ISBN-13, sin guiones'),('titulo','VARCHAR(200)','NN, CK','Titulo bibliografico'),('anio_publicacion','SMALLINT','NN, CK','Anio de edicion publicado')],
'autor':[
('id_autor','BIGINT IDENTITY','PK','Identificador de autor'),('nombre','VARCHAR(160)','NN, CK','Nombre de autor')],
'libro_autor':[
('isbn','VARCHAR(17)','PK, FK, NN','Libro coescrito'),('id_autor','BIGINT','PK, FK, NN','Autor coautor')],
'coleccion':[
('id_coleccion','BIGINT IDENTITY','PK','Identificador de agrupacion'),('nombre','VARCHAR(100)','UQ, NN, CK','Nombre unico de la coleccion')],
'libro_coleccion':[
('isbn','VARCHAR(17)','PK, FK, NN','Libro incluido'),('id_coleccion','BIGINT','PK, FK, NN','Coleccion que lo agrupa')],
'ejemplar':[
('id_ejemplar','BIGINT IDENTITY','PK','Copia fisica individual'),('isbn','VARCHAR(17)','FK, NN','Libro correspondiente'),('codigo_inventario','VARCHAR(30)','UQ, NN','Etiqueta de inventario unica'),('estado','VARCHAR(20)','NN, CK','DISPONIBLE/EN_REPARACION/BAJA')],
'prestamo':[
('id_prestamo','BIGINT IDENTITY','PK','Identificador del evento'),('id_persona','BIGINT','FK, NN','Lector responsable'),('id_ejemplar','BIGINT','FK, NN','Copia prestada'),('fecha_salida','DATE','NN','Inicio del prestamo'),('fecha_limite','DATE','NN, CK','Vencimiento no anterior al inicio'),('fecha_devolucion','DATE','opcional, CK','NULL indica prestamo activo')],
'incidencia':[
('id_incidencia','BIGINT IDENTITY','PK','Identificador del reporte'),('id_prestamo','BIGINT','FK, NN','Prestamo que origina el reporte'),('tipo','VARCHAR(12)','NN, CK','DANO, PERDIDA, RETRASO u OTRA'),('fecha','DATE','NN','Fecha de registro'),('observacion','TEXT','NN, CK','Descripcion de la incidencia')]
}
# Parent, child, relationship, multiplicity child
FK=[('persona','estudiante','ISA','0..1'),('persona','docente','ISA','0..1'),('persona','persona_telefono','telefono','0..*'),('persona','prestamo','realiza','0..*'),('libro','ejemplar','tiene','0..*'),('autor','libro_autor','coautoria','0..*'),('libro','libro_autor','coautoria','1..*'),('coleccion','libro_coleccion','agrupa','0..*'),('libro','libro_coleccion','agrupa','0..*'),('ejemplar','prestamo','sobre','0..*'),('prestamo','incidencia','genera','0..*')]
# Display order: purposeful grouping
ORDER=['persona','estudiante','docente','persona_telefono','autor','libro','libro_autor','coleccion','libro_coleccion','ejemplar','prestamo','incidencia']
assert len(C)==12 and len(FK)==11

# Read real schema and verify each conceptual relation has its expected DDL table/FK.
sql=(SQL/'schema.sql').read_text()
errors=[]
for t,cols in C.items():
 m=re.search(r'CREATE TABLE\s+'+t+r'\s*\((.*?)\n\);',sql,re.S)
 if not m: errors.append('No CREATE TABLE: '+t); continue
 section=m.group(1)
 for col,*_ in cols:
  if not re.search(r'^\s*'+col+r'\s+', section, re.M): errors.append('No atributo '+t+'.'+col)
 if not re.search(r'CONSTRAINT pk_'+t+r'\s+PRIMARY KEY',section): errors.append('PK ausente '+t)
for parent,child,*_ in FK:
 part=re.search(r'CREATE TABLE\s+'+child+r'\s*\((.*?)\n\);',sql,re.S)
 if not part or not re.search(r'REFERENCES\s+'+parent+r'\s*\(',part.group(1)):
  errors.append('FK ausente '+child+' -> '+parent)
for needle in ['CREATE UNIQUE INDEX ux_prestamo_ejemplar_activo','WHERE fecha_devolucion IS NULL','DEFERRABLE INITIALLY DEFERRED','CREATE VIEW vw_disponibilidad','ON DELETE CASCADE','ON DELETE RESTRICT','CREATE TABLE libro_autor','CREATE TABLE libro_coleccion']:
 if needle not in sql: errors.append('No incluye '+needle)
(SQL/'schema.sql').read_text()
result='VALIDACION ESTATICA DE COHERENCIA (NO EQUIVALE A EJECUCION EN POSTGRESQL)\n'
result+='Modelado: '+str(len(C))+' tablas, '+str(sum(map(len,C.values())))+' columnas, '+str(len(FK))+' relaciones FK.\n'
result+='Validado: existencia de CREATE TABLE, PK por tabla, nombres de columnas, 11 destinos FK, indice parcial, vistas, triggers diferibles.\n'
result+='Estado: '+('SIN ERRORES DETECTADOS' if not errors else 'ERRORES: '+', '.join(errors))+'\n'
result+='Pendiente: ejecucion real con PostgreSQL/pgAdmin para verificaciones funcionales y capturas propias.\n'
(ROOT/'Validacion'/'resultado_validacion_estatica.txt').write_text(result)
if errors: raise ValueError(errors)

# Diagramas vectoriales generados desde metadatos de esquema.
def graphfile(physical):
 import graphviz
 g=graphviz.Digraph('Esquema',engine='dot')
 g.attr(rankdir='LR',bgcolor='white',pad='0.26',nodesep='0.35',ranksep='0.8',splines='spline',fontname='DejaVu Sans',compound='true',label=('ESQUEMA FISICO POSTGRESQL | BIBLIOTECA ESCOLAR' if physical else 'ESQUEMA RELACIONAL LOGICO | BIBLIOTECA ESCOLAR'),labelloc='t',fontsize='20',fontcolor='#102740')
 g.attr('node',shape='plain',fontname='DejaVu Sans')
 for t in ORDER:
  r=C[t]
  rows=[]
  for name,typ,marks,desc in r:
   if not physical and 'PK' not in marks and 'FK' not in marks: continue
   name_view=html.escape(name)
   ty=html.escape(typ) if physical else ''
   prefix= ('<B>PK</B> ' if 'PK' in marks else '') + ('<B>FK</B> ' if 'FK' in marks else '')
   rows.append('<TR><TD ALIGN="LEFT" BALIGN="LEFT" CELLPADDING="5"><FONT FACE="DejaVu Sans" POINT-SIZE="10">'+prefix+name_view+'</FONT></TD>'+('<TD ALIGN="LEFT" CELLPADDING="5"><FONT FACE="DejaVu Sans" POINT-SIZE="9">'+ty+'</FONT></TD>' if physical else '')+'</TR>')
  label='<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0" COLOR="#BFCFD8" BGCOLOR="#FFFFFF"><TR><TD BGCOLOR="#0B6572" '+('COLSPAN="2"' if physical else '')+' CELLPADDING="8"><FONT FACE="DejaVu Sans" COLOR="white" POINT-SIZE="12"><B>'+t.upper()+'</B></FONT></TD></TR>'+''.join(rows)+'</TABLE>>'
  g.node(t,label=label)
 for p,c,rel,multi in FK:
  g.edge(p,c,arrowhead='crow',arrowsize='0.55',color='#607C8C',penwidth='1.2',label=rel+' '+multi,fontsize='9',fontname='DejaVu Sans',fontcolor='#496A76')
 name='Esquema_Fisico_PostgreSQL' if physical else 'Esquema_Relacional'
 for f in ('svg','pdf','png'):
  g.render(filename=name, directory=str(DIA), format=f, cleanup=True, quiet=True)
  original=DIA/(name+'.'+f)
  generated=DIA/(name+'.'+f)
  assert generated.exists(),generated
 (DIA/(name+'.dot')).write_text(g.source,encoding='utf8')
 return name

# editable draw.io chart using the same nodes and links.
def drawio(physical):
 name='Esquema_Fisico_PostgreSQL' if physical else 'Esquema_Relacional'
 mx=ET.Element('mxfile',host='app.diagrams.net',modified='2026-11-07T00:00:00.000Z',agent='ChatGPT',version='24.7.17',type='device')
 d=ET.SubElement(mx,'diagram',id='unit3',name=name)
 model=ET.SubElement(d,'mxGraphModel',dx='1600',dy='950',grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='1',pageScale='1',pageWidth='2000',pageHeight='1800',math='0',shadow='0')
 rt=ET.SubElement(model,'root'); ET.SubElement(rt,'mxCell',id='0'); ET.SubElement(rt,'mxCell',id='1',parent='0')
 placement={
 'persona':(80,90),'estudiante':(80,425),'docente':(420,425),'persona_telefono':(420,90),
 'autor':(750,90),'libro_autor':(1050,90),'libro':(1350,90),
 'coleccion':(750,520),'libro_coleccion':(1050,520),
 'ejemplar':(1350,520),'prestamo':(1350,970),'incidencia':(1050,970)
 }
 for t in ORDER:
  cols=C[t]
  listed=cols if physical else [c for c in cols if 'PK' in c[2] or 'FK' in c[2]]
  lines=[f'<b>{html.escape(t.upper())}</b>']
  for col,typ,marks,desc in listed:
   lines.append(html.escape(('PK ' if 'PK' in marks else '')+('FK ' if 'FK' in marks else '')+col+((' : '+typ) if physical else '')))
  txt='<div style="text-align:left;line-height:1.65">'+'<br>'.join(lines)+'</div>'
  x,y=placement[t]; h=45+len(listed)*27
  cell=ET.SubElement(rt,'mxCell',id=t,value=txt,style='rounded=0;whiteSpace=wrap;html=1;fillColor=#F5FAFC;strokeColor=#6E9AA7;strokeWidth=1.4;fontColor=#15354B;fontSize=13;align=left;verticalAlign=middle;spacingLeft=14;',vertex='1',parent='1')
  ET.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width='285',height=str(h),attrib={'as':'geometry'})
 for i,(p,c,rel,m) in enumerate(FK):
  edge=ET.SubElement(rt,'mxCell',id='edge'+str(i),value=rel+' (1:'+m+')',style='edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#6B8795;strokeWidth=1.3;endArrow=block;endFill=1;fontSize=11;fontColor=#385665;labelBackgroundColor=#FFFFFF;',edge='1',parent='1',source=p,target=c)
  ET.SubElement(edge,'mxGeometry',relative='1',attrib={'as':'geometry'})
 ET.ElementTree(mx).write(EDIT/(name+'.drawio'),encoding='utf-8',xml_declaration=True)

for phys in (False,True): graphfile(phys);drawio(phys)

S=getSampleStyleSheet()
S.add(ParagraphStyle(name='SectionU3',fontName='DejaVu-Bold',fontSize=11.4,textColor=navy,spaceBefore=13,spaceAfter=6,leading=15))
S.add(ParagraphStyle(name='SubU3',fontName='DejaVu-Bold',fontSize=9.1,textColor=teal,spaceBefore=8,spaceAfter=4,leading=13))
S.add(ParagraphStyle(name='BodyU3',fontName='DejaVu',fontSize=8.4,leading=13,spaceAfter=7,textColor=navy))
S.add(ParagraphStyle(name='MiniU3',fontName='DejaVu',fontSize=7.2,leading=11,spaceAfter=4,textColor=navy))
S.add(ParagraphStyle(name='TableU3',fontName='DejaVu',fontSize=6.85,leading=10,textColor=navy))
S.add(ParagraphStyle(name='SmallU3',fontName='DejaVu',fontSize=7.4,leading=11.2,textColor=navy))
S.add(ParagraphStyle(name='RefU3',fontName='DejaVu',fontSize=7.2,leading=11,textColor=grey,spaceAfter=6,wordWrap='CJK'))

P=lambda txt,style='BodyU3':Paragraph(txt,S[style])
def b(txt):return '<b>'+html.escape(txt)+'</b>'
def para(txt):return P(txt)
def heading(t):return P(html.escape(t),'SectionU3')
def sub(t):return P(html.escape(t),'SubU3')
def bullet(t):return P('•  '+t,'SmallU3')
def tb(headers,rows,widths=None,small=True):
 data=[[Paragraph(html.escape(str(c)),ParagraphStyle('head'+str(i),parent=S['TableU3'],fontName='DejaVu-Bold',textColor=white)) for i,c in enumerate(headers)]]+[[P(str(c),'TableU3') for c in r] for r in rows]
 table=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1)
 table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('TEXTCOLOR',(0,0),(-1,0),white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,pale]),('LINEBELOW',(0,0),(-1,0),1,teal),('LINEBELOW',(0,1),(-1,-1),0.28,bluegrey),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
 return table

def cover(c,title,subtitle):
 w,h=A4
 c.setFillColor(navy); c.rect(0,h-118*mm,w,118*mm,fill=1,stroke=0)
 c.setFillColor(teal); c.rect(0,h-121*mm,w,3*mm,fill=1,stroke=0)
 c.setFont('DejaVu-Bold',15); c.setFillColor(white); c.drawCentredString(w/2,h-32*mm,'TECNOLÓGICO NACIONAL DE MÉXICO')
 c.setFont('DejaVu',12);c.drawCentredString(w/2,h-44*mm,'INSTITUTO TECNOLÓGICO SUPERIOR DE MONCLOVA')
 c.setFont('DejaVu-Bold',17);c.drawCentredString(w/2,h-79*mm,title)
 c.setFont('DejaVu',10);c.drawCentredString(w/2,h-89*mm,subtitle)
 c.setFillColor(navy)
 info=[('ASIGNATURA','Fundamentos de Bases de Datos'),('UNIDAD','Unidad 3. Modelo relacional'),('ALUMNO','Aldo Alberto Barajas Ancira'),('NÚMERO DE CONTROL','I24050397'),('DOCENTE','Rubén Riojas'),('FECHA','7 de noviembre de 2026')]
 top=h-148*mm
 for i,(a,v) in enumerate(info):
  yy=top-i*18*mm
  c.setFont('DejaVu-Bold',8);c.setFillColor(teal);c.drawString(25*mm,yy,a)
  c.setFont('DejaVu',11);c.setFillColor(navy);c.drawString(25*mm,yy-7*mm,v)
 c.setStrokeColor(bluegrey);c.line(25*mm,29*mm,w-25*mm,29*mm)
 c.setFont('DejaVu-Oblique',8);c.setFillColor(grey);c.drawCentredString(w/2,19*mm,'Caso académico ficticio: biblioteca escolar · Continuidad con la Unidad 2')

def footer(c,doc):
 c.saveState();w,h=A4
 c.setStrokeColor(bluegrey);c.line(19*mm,19*mm,w-19*mm,19*mm)
 c.setFont('DejaVu',7.2);c.setFillColor(grey)
 c.drawString(19*mm,13.2*mm,'TecNM · Fundamentos de Bases de Datos · Unidad 3')
 c.drawRightString(w-19*mm,13.2*mm,f'Página {doc.page}')
 c.restoreState()

def make_pdf(filename,cover_title,subtitle,story,annex_pdf):
 out=ROOT/filename
 with tempfile.TemporaryDirectory() as tmp:
  coverpdf=Path(tmp)/'cover.pdf'; bc=Canvas(str(coverpdf),pagesize=A4);cover(bc,cover_title,subtitle);bc.save()
  inner=Path(tmp)/'content.pdf'
  doc=SimpleDocTemplate(str(inner),pagesize=A4,leftMargin=19*mm,rightMargin=19*mm,topMargin=21*mm,bottomMargin=25*mm,title=cover_title,author='Aldo Alberto Barajas Ancira',subject='Unidad 3 Modelo relacional Biblioteca escolar')
  doc.build(story,onFirstPage=footer,onLaterPages=footer)
  z=fitz.open()
  for part in (coverpdf,inner,DIA/annex_pdf):
   inp=fitz.open(part);z.insert_pdf(inp);inp.close()
  z.save(out,garbage=4,deflate=True);z.close()
 return out

# ----------- Tarea 3.1 -----------
story=[]
story+=[heading('1. Introducción, alcance y trazabilidad'),para('La Unidad 2 definió un caso de estudio de biblioteca escolar con entidades Persona, Estudiante, Docente, Libro, Ejemplar, Autor, Colección, Préstamo e Incidencia. La conversión relacional conserva su identidad, relaciones, atributos especiales, mínimos de participación y el historial. Se formalizan 12 relaciones base (tablas), con dos N:M descompuestas, un atributo multivalorado y una especialización total/disjunta.'),para('La propuesta corresponde a un <b>modelo lógico relacional</b> independiente del código de aplicación. Su materialización específica en PostgreSQL se entrega en la Tarea 3.2. La agregación conceptual E-RE «hecho de préstamo» se implementa mediante el registro de Préstamo; no origina una tabla redundante.'),
 heading('2. Componentes formales del modelo relacional')]
concepts=[('Relación','Conjunto de tuplas con un mismo encabezado de atributos; en la práctica, una tabla lógica sin depender del orden de filas.'),('Atributo','Propiedad nombrada de la relación, por ejemplo Libro.isbn o Prestamo.fecha_limite.'),('Tupla','Asignación de valores a los atributos; una fila de Prestamo representa un evento de préstamo.'),('Dominio','Conjunto de valores permitidos para un atributo, delimitado por tipo, NULL/NOT NULL y CHECK.'),('Grado / cardinalidad','Número de atributos de una relación / número de tuplas que contiene en un estado determinado.'),('Clave candidata / primaria','Superclave mínima / clave candidata elegida para identificar cada tupla.'),('Clave foránea','Atributo(s) que referencian una clave candidata de otra relación para preservar integridad referencial.')]
story.append(tb(['Concepto','Definición y aplicación'],concepts,[48*mm,124*mm]))
story.extend([heading('3. Restricciones de integridad'),tb(['Categoría','Implementación y objetivo'],[
 ('Entidad','Toda clave primaria es única y no admite NULL; identidad compuesta en Persona_telefono y tablas puente.'),
 ('Referencial','FKs entre Persona/Préstamo, Libro/Ejemplar, Préstamo/Incidencia, etc. ON DELETE RESTRICT en historial, CASCADE en asociaciones dependientes.'),
 ('Dominio','Tipos SQL, NOT NULL y CHECK para semestre, fecha_límite, tipo de incidencia y estado de ejemplar.'),
 ('Negocio temporal','Índice único parcial en ejemplar con fecha_devolucion NULL: a lo sumo un préstamo activo.'),
 ('Participación mínima','Al menos un autor por Libro, y todo Persona con exactamente un subtipo. Requieren validación diferible, no solo PK/FK.')
],[45*mm,127*mm]),heading('4. Reglas de transformación del E-R de la Unidad 2')])
maprows=[
('Entidad fuerte','Persona → PERSONA; Libro → LIBRO; Autor → AUTOR; cada identidad pasa a PRIMARY KEY.'),
('Relación 1:1 / ISA','Persona–Estudiante/Docente: dos tablas hijas con PK = FK a Persona; discriminador y control total/disjunto.'),
('Relación 1:N','LIBRO.isbn → EJEMPLAR.isbn; PERSONA.id_persona → PRESTAMO.id_persona; EJEMPLAR → PRESTAMO; PRESTAMO → INCIDENCIA.'),
('Relación N:M','Autor–Libro → LIBRO_AUTOR(isbn,id_autor); Libro–Colección → LIBRO_COLECCION(isbn,id_coleccion); ambas PK compuestas.'),
('Multivalorado','Persona.{telefonos} → PERSONA_TELEFONO(id_persona,telefono), PK compuesta.'),
('Compuesto','Persona.nombre → nombres, apellido_paterno, apellido_materno, atributos atómicos.'),
('Derivado','edad_obra y dias_atraso no se almacenan; se calculan en consultas/vistas SQL.'),
('Agregación E-RE','Evento de préstamo: PRESTAMO existe una sola vez; INCIDENCIA referencia PRESTAMO, sin duplicar evento.')]
story.append(tb(['Regla','Resultado del mapeo'],maprows,[44*mm,128*mm]))
story.append(heading('5. Formulación relacional formal'))
for t in ORDER:
 pk=[name for name,typ,mark,desc in C[t] if 'PK' in mark]
 fields=', '.join(name for name,*_ in C[t])
 story.append(P('<b>'+t.upper()+'</b> ('+html.escape(fields)+'). <font color="#007B83">PK = {'+', '.join(pk)+'}</font>.','SmallU3'))
story.extend([heading('6. Esquema tabular de PK, FK y asociaciones')])
keyrows=[]
for t in ORDER:
 pk=', '.join(x[0] for x in C[t] if 'PK' in x[2])
 parents=', '.join(p for p,c,*_ in FK if c==t) or '—'
 keyrows.append((t,pk,parents))
story.append(tb(['Relación','PK','Tablas padre (FK)'],keyrows,[43*mm,64*mm,65*mm]))
story.append(heading('7. Preservación de reglas de negocio de la Unidad 2'))
story.append(tb(['Reglas','Solución lógica / física'],[
('RN01 / RN12','ISBN identifica Libro; Ejemplar contiene FK a Libro. Disponibilidad calculada, no columna editable.'),
('RN02 / RN03','N:M con relaciones puente; al menos un autor mediante trigger diferible; colecciones con mínimo cero.'),
('RN04 / RN05','PERSONA + ESTUDIANTE/DOCENTE; PK compartidas, discriminador, UNIQUE matrícula/número de empleado y verificación total/disjunta.'),
('RN06 / RN07','PRESTAMO enlaza Persona y Ejemplar; índice parcial prohíbe doble préstamo activo.'),
('RN08','CHECK de fechas; fecha_devolucion puede ser NULL.'),
('RN09 / RN10','INCIDENCIA tiene FK obligatoria; RESTRICT en eventos de préstamo e incidencias para preservar historial.'),
('RN11','Nombre descompuesto; teléfonos en tabla propia; derivados mediante vistas.')
],[39*mm,133*mm]))
story.extend([heading('8. Análisis crítico y decisiones de diseño'),para('Se prioriza la tercera forma normal (3FN) mediante entidades con dependencia funcional identificable: libro determina título/año, ejemplar determina ISBN/estado/código, préstamo determina sus fechas y participantes. Los N:M son relaciones con PK compuesta y cada teléfono ocupa una tupla independiente. Esto evita grupos repetidos y anomalías de modificación.'),para('No toda regla semántica es expresable con restricciones relacionales estándar simples. La participación mínima de Libro en Autor y la totalidad de subtipos se validan con triggers de restricción diferibles en PostgreSQL. La necesidad de transacciones para crear Libro+Autor y Persona+Subtipo está documentada. El estado DISPONIBLE no sustituye la consulta del préstamo activo; el sistema de préstamo debe además impedir operaciones en ejemplares no habilitados mediante lógica transaccional.'),para('La integridad referencial protege contra referencias inexistentes; la unicidad condicional protege contra doble préstamo activo, aun bajo concurrencia. Una vista calcula la disponibilidad sin duplicar un campo mutable. La eliminación física de eventos se restringe, mientras que se permiten cascadas solo en relaciones dependientes cuando no comprometen ese historial.'),heading('9. Conclusiones'),para('El mapeo de la Unidad 2 conduce a 12 relaciones base y 11 referencias estructurales, preservando las cardinalidades y las dependencias de identidad. Su valor no consiste solamente en crear tablas, sino en explicar qué invariante se resuelve con PK, FK, CHECK, UNIQUE, un índice condicional o una validación diferida. El diagrama relacional anexo es una representación lógica editable que se corresponde con el SQL de la siguiente tarea.'),heading('10. Referencias'),P('Silberschatz, Korth y Sudarshan. <i>Database System Concepts</i>. McGraw-Hill.','RefU3'),P('PostgreSQL Global Development Group. Documentación oficial de restricciones de integridad: https://www.postgresql.org/docs/current/ddl-constraints.html','RefU3'),P('Unidad 2: Reporte técnico E-R/E-RE de biblioteca escolar, elaborado previamente (2026).','RefU3'),P('ANEXO A. Esquema relacional lógico en página vectorial de alta resolución.','RefU3')])
p1=make_pdf('Tarea_3_1/Tarea_3_1_Transformacion_ER_a_Relacional.pdf','TAREA 3.1','Modelo E-R a esquema relacional e integridad',story,'Esquema_Relacional.pdf')

# ----------- Tarea 3.2 -----------
story2=[heading('1. Objetivo y plataforma'),para('Se implementa el modelo lógico de biblioteca escolar en <b>PostgreSQL 14 o posterior</b> mediante el archivo <b>SQL/schema.sql</b>. Contiene 12 tablas base, 11 referencias FK, claves PK y UNIQUE, restricciones de dominio CHECK / NOT NULL, un índice único parcial, dos validadores diferibles y tres vistas de atributos calculados.'),para('<b>Alcance de evidencia:</b> el código SQL fue revisado mediante un verificador estático de nombres, columnas, PK y FK; no se dispone en este entorno de un servidor PostgreSQL al que conectarse. Por tanto, los resultados esperados se distinguen explícitamente de capturas reales de pgAdmin/psql, que deben incorporarse tras ejecutar el script en tu equipo.'),heading('2. Transformación lógica a objetos físicos'),tb(['Objeto','Implementación'],[
('Tablas','12 CREATE TABLE con columnas de tipos BIGINT, VARCHAR, SMALLINT, DATE o TEXT.'),
('Identidad','GENERATED BY DEFAULT AS IDENTITY en identificadores numéricos autónomos.'),
('PK y FK','PK por tabla, varias compuestas; FK con acciones ON UPDATE/DELETE expresas.'),
('Atributos derivados','Tres CREATE VIEW: antigüedad del libro, atraso y disponibilidad del ejemplar.'),
('Reglas especiales','Índice único parcial: ejemplar activo. Triggers DEFERRABLE INITIALLY DEFERRED: subtipo obligatorio y libro con autor.'),
('Índices secundarios','Índices de apoyo para FK muy consultadas; no se duplican PK.')
],[48*mm,124*mm]),heading('3. Diccionario de datos completo')]
for t in ORDER:
 story2.append(sub(f'3. Diccionario · {t.upper()}'))
 story2.append(tb(['Campo','Tipo','Restricción','Significado'],[
 (html.escape(name),html.escape(typ),html.escape(marks),html.escape(desc)) for name,typ,marks,desc in C[t]
 ],[40*mm,35*mm,29*mm,68*mm]))
story2.extend([heading('4. Política de integridad y cascadas'),tb(['Relación','ON UPDATE','ON DELETE','Motivo'],[
 ('Persona → Estudiante/Docente','RESTRICT','CASCADE','Subtipo dependiente; impide actualizar el discriminador sin migración explícita.'),
 ('Persona → Teléfono','CASCADE','CASCADE','El teléfono no es un registro histórico independiente.'),
 ('Libro/Autor → Libro_autor','CASCADE','CASCADE','Tabla puente; trigger impide dejar un libro sin autores.'),
 ('Libro/Colección → Libro_coleccion','CASCADE','CASCADE','Agrupación opcional, sin destrucción del libro.'),
 ('Libro → Ejemplar','CASCADE','RESTRICT','No borrar un libro mientras existan copias.'),
 ('Persona/Ejemplar → Préstamo','CASCADE','RESTRICT','No borrar un historial vinculado.'),
 ('Préstamo → Incidencia','CASCADE','RESTRICT','No borrar préstamo con incidencia.')
],[56*mm,25*mm,25*mm,66*mm]),heading('5. Ejecución reproducible en PostgreSQL / pgAdmin'),bullet('<b>Paso 1.</b> Crear una base de pruebas vacía, por ejemplo <b>biblioteca_unidad3</b> (sin datos reales).'),bullet('<b>Paso 2.</b> En pgAdmin, abrir Query Tool y ejecutar <b>SQL/schema.sql</b>. Debe terminar con COMMIT sin errores.'),bullet('<b>Paso 3.</b> En el árbol de la base actualizar Schemas → biblioteca → Tables, y verificar 12 tablas.'),bullet('<b>Paso 4.</b> Ejecutar <b>SQL/verificacion_esquema.sql</b> y capturar la lista de tablas, FK, índices y vistas.'),bullet('<b>Paso 5.</b> Ejecutar <b>SQL/datos_ejemplo.sql</b>; después <b>SQL/pruebas_integridad.sql</b> y capturar mensajes NOTICE de pruebas negativas controladas.'),bullet('<b>Paso 6.</b> Generar el ERD desde pgAdmin o una herramienta CASE conectada al SGBD; compararlo con el anexo físico, y añadir captura propia al reporte final.'),para('<b>Alternativa por consola:</b> <font face="DejaVu">psql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/schema.sql</font>. Repetir para los scripts siguientes. No ejecutar el reset de laboratorio si existe información importante.'),heading('6. Consultas de inspección y validación'),para('Para obtener evidencias, <b>verificacion_esquema.sql</b> consulta information_schema.tables, information_schema.table_constraints, information_schema.key_column_usage, information_schema.constraint_column_usage y pg_indexes. Se espera observar 12 tablas base y relaciones como FK de PRESTAMO a PERSONA y EJEMPLAR. También incluye consultas sobre las tres vistas.'),heading('7. Matriz de pruebas de integridad'),tb(['ID','Caso','Resultado esperado'],[
 ('P01','Insertar ejemplar con ISBN inexistente','RECHAZO por FK'),
 ('P02','Registrar estado de ejemplar no permitido','RECHAZO por CHECK'),
 ('P03','Duplicar préstamo activo de un ejemplar','RECHAZO por UNIQUE parcial'),
 ('P04','Fecha límite anterior a salida','RECHAZO por CHECK'),
 ('P05','Eliminar préstamo con incidencia','RECHAZO por FK RESTRICT'),
 ('P06','Crear Persona sin subtipo','RECHAZO diferido al forzar restricciones'),
 ('P07','Insertar Docente para Persona ESTUDIANTE','RECHAZO por FK/CK'),
 ('P08','Crear Libro sin autor','RECHAZO diferido al forzar restricciones')
],[18*mm,86*mm,68*mm]),para('<b>Estado de resultados:</b> la tabla presenta <b>resultados esperados</b>. El archivo de pruebas automatizadas imprime «OK» cuando PostgreSQL rechaza cada operación inválida, y falla explícitamente si una de esas operaciones es aceptada. No se presentan capturas fabricadas ni se afirma una ejecución contra un servidor no disponible.'),heading('8. Consideraciones y limitaciones'),para('Los disparadores diferibles permiten registrar en una misma transacción Persona+subtipo y Libro+autor. La eliminación de una fila histórica queda restringida si existen dependencias; para políticas de borrado más rigurosas se recomienda revocar DELETE sobre tablas históricas a los roles de la aplicación y utilizar bajas lógicas. No se implementó la prohibición transaccional de prestar un ejemplar EN_REPARACION o BAJA: la vista muestra la indisponibilidad, pero la aplicación deberá bloquear altas o se podrá incorporar un trigger específico con bloqueo de ejemplar.'),para('No se valida dígito de control matemático de ISBN (solo formato 10/13); ni se obliga una fecha de incidencia no anterior al préstamo, porque estas reglas no figuraban como restricciones explicitadas de entrada. Se documentan como posibles extensiones. Las restricciones total/disjunta y la autoría mínima requieren confirmar transacciones, no pueden demostrarse únicamente por la existencia de FK simples.'),heading('9. Registro de evidencias pendientes'),tb(['Evidencia','Cómo obtenerla','Estado'],[
 ('E01: CREATE TABLE','Captura Query Tool con script ejecutado sin errores','Pendiente de pgAdmin'),
 ('E02: tabla/fks','Captura árbol Schemas/biblioteca/Tables + Constraints','Pendiente de pgAdmin'),
 ('E03: resultados','Captura de consultas y notices de pruebas_integridad.sql','Pendiente de pgAdmin'),
 ('E04: ERD del SGBD','Exportar diagrama generado mediante pgAdmin/CASE conectado','Pendiente de pgAdmin'),
 ('E05: validación estática','Archivo resultado_validacion_estatica.txt incluido','Completada (no ejecución)')
],[43*mm,92*mm,37*mm]),heading('10. Conclusiones'),para('El DDL reproduce las relaciones del E-R anterior con claves, restricciones y acciones de actualización/eliminación justificadas por la semántica de cada asociación. Los controles más importantes son la protección de registros históricos, la no duplicación de préstamos activos y la conservación de las cardinalidades mínimas de autoría y especialización. El esquema está preparado para una ejecución reproducible en PostgreSQL; la evidencia definitiva exige capturas reales de la herramienta de gestión.'),heading('11. Fuentes técnicas'),P('PostgreSQL Global Development Group. <i>CREATE TABLE</i>: https://www.postgresql.org/docs/current/sql-createtable.html','RefU3'),P('PostgreSQL Global Development Group. <i>Constraints</i>: https://www.postgresql.org/docs/current/ddl-constraints.html','RefU3'),P('PostgreSQL Global Development Group. <i>CREATE TRIGGER</i>: https://www.postgresql.org/docs/current/sql-createtrigger.html','RefU3'),P('PostgreSQL Global Development Group. <i>Indexes on Expressions and Partial Indexes</i>: https://www.postgresql.org/docs/current/indexes-partial.html','RefU3'),P('Unidad 2. Reporte conceptual E-R/E-RE de Biblioteca escolar (2026).','RefU3'),P('ANEXO B. Esquema físico documentado desde el DDL, vectorial. No equivale a la captura de un ERD obtenido directamente de un servidor.','RefU3')])
p2=make_pdf('Tarea_3_2/Tarea_3_2_Esquema_Fisico_y_DDL.pdf','TAREA 3.2','Esquema físico, diccionario y script DDL',story2,'Esquema_Fisico_PostgreSQL.pdf')

README='''# Unidad 3 · Modelo relacional | Biblioteca escolar\n\n**Alumno:** Aldo Alberto Barajas Ancira · **No. control:** I24050397  \n**Asignatura:** Fundamentos de Bases de Datos · **Docente:** Rubén Riojas  \n**Fecha:** 7 de noviembre de 2026\n\n## Relación con Unidad 2\nLa misma biblioteca escolar del modelo E-R/E-RE anterior, sin cambiar el caso de estudio ni el proyecto integrador de ferretería.\n\n## Entregables\n- `Tarea_3_1/Tarea_3_1_Transformacion_ER_a_Relacional.pdf`: reporte formal de tuplas, atributos, dominios, integridad y mapeo E-R a 12 tablas.\n- `Tarea_3_2/Tarea_3_2_Esquema_Fisico_y_DDL.pdf`: reporte técnico, diccionario completo, política de cascadas y protocolo de validación.\n- `SQL/schema.sql`: DDL para **PostgreSQL 14+**, crea esquema `biblioteca`, 12 tablas, 11 FK, CHECK, UNIQUE, triggers e índices y vistas.\n- `SQL/datos_ejemplo.sql`: datos mínimos ficticios, ejecutarlos en BD recién creada.\n- `SQL/verificacion_esquema.sql`: consultas para inventario de tablas, FKs, índices y vistas.\n- `SQL/pruebas_integridad.sql`: 8 pruebas negativas con resultados verificables.\n- `SQL/reset_SOLO_LABORATORIO.sql`: elimina todo el esquema; úsalo **solo** si es un entorno desechable.\n- `Diagramas_Editables/*.drawio`: editables en https://app.diagrams.net.\n- `Diagramas_Exportados`: SVG, PNG, PDF vectorial y DOT.\n- `Validacion/resultado_validacion_estatica.txt`: controles estructurales realizados durante la preparación.\n- `Guias/GUIA_GITHUB_YOUTUBE_Y_EVIDENCIAS.md`: cómo entregar los enlaces y grabar los videos.\n\n## Orden de ejecución\n1. Crear una base PostgreSQL vacía: `biblioteca_unidad3`.\n2. Ejecutar `schema.sql` una sola vez.\n3. Ejecutar `verificacion_esquema.sql` y comprobar 12 tablas.\n4. Ejecutar `datos_ejemplo.sql`.\n5. Ejecutar `pruebas_integridad.sql` y conservar los mensajes `NOTICE: OK`.\n6. Generar un ERD desde pgAdmin (o CASE conectado a PostgreSQL), obtener las capturas y completar las evidencias del reporte 3.2.\n\nEn `psql` (desde la carpeta de repositorio):\n```shell\npsql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/schema.sql\npsql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/verificacion_esquema.sql\npsql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/datos_ejemplo.sql\npsql -X -v ON_ERROR_STOP=1 -d biblioteca_unidad3 -f SQL/pruebas_integridad.sql\n```\n\n**Sobre el estado de verificación:** el DDL fue revisado con un validador estático propio; **no ha sido ejecutado contra un servidor PostgreSQL en este entorno**. No se fabricaron capturas de ejecución. La ejecución y el ERD del SGBD deben hacerse en tu computadora para satisfacer el criterio de evidencias.\n\n**Pendiente del alumno:** publicar el proyecto en su repositorio público GitHub y grabar dos videos públicos en el mismo canal YouTube con pantalla y webcam inferior derecha.\n'''
(ROOT/'README.md').write_text(README,encoding='utf-8')

GUIDE='''# Guía para GitHub, evidencias reales y YouTube\n\n## GitHub (un repositorio público)\n1. En github.com crea un repositorio público, por ejemplo `biblioteca-escolar-unidad3`.\n2. Sube todo el contenido de esta carpeta (no hace falta subir ZIP dentro del repositorio).\n3. Comprueba que los dos PDFs, el `schema.sql`, los `.drawio` y los diagramas exportados se ven en el repositorio.\n4. Copia su URL y pégala como enlace de ambas tareas en Teams.\n\n## Evidencias en PostgreSQL/pgAdmin para Tarea 3.2\n1. Crea una base **vacía** para la práctica; no uses base productiva.\n2. Ejecuta `SQL/schema.sql` desde Query Tool; captura la ejecución sin errores.\n3. Refresca el árbol `Schemas > biblioteca > Tables`; captura las 12 tablas.\n4. Abre propiedades/constraints de `prestamo` y de `libro_autor` para mostrar FKs.\n5. Ejecuta `SQL/verificacion_esquema.sql`, captura total de tablas, FKs, índices.\n6. Ejecuta `SQL/datos_ejemplo.sql` y `SQL/pruebas_integridad.sql`; captura los mensajes `NOTICE: OK` y la consulta final de conteos.\n7. Genera el ERD desde pgAdmin u otra herramienta conectada al SGBD y guárdalo como PNG/PDF. Esta evidencia debe sustituir al diagrama documental cuando el profesor exija que provenga del SGBD.\n8. Para anexar evidencias al PDF, inserta páginas o capturas en un editor de PDF y guarda versión final. No presentes las cifras esperadas como observadas.\n\n## Video 3.1 (6 a 9 minutos)\n- Pantalla: muestra Unidad 2 y el PDF Tarea 3.1. Webcam visible en la esquina inferior derecha.\n- 0:00 Introducción: mismo caso biblioteca, objetivo y entidades.\n- 1:00 Definir tupla, atributo, dominio, PK y FK con un ejemplo concreto.\n- 2:30 Describir 1:1 (ISA Persona-Estudiante/Docente) y 1:N Libro-Ejemplar.\n- 4:00 Mostrar N:M Autor-Libro y Libro-Colección convertidas a tablas puente.\n- 5:20 Mostrar telefonos como tabla propia y derivados como vistas.\n- 6:20 Explicar cardinalidades mínimas, prestamo activo e integridad.\n- 7:20 Conclusión e invitación a consultar repositorio.\n\n## Video 3.2 (6 a 10 minutos)\n- Captura de pantalla de pgAdmin (o psql) + webcam en esquina inferior derecha.\n- Presenta base de pruebas vacía; explica por qué no se emplea DROP en schema.sql.\n- Ejecuta schema.sql; confirma creación limpia de 12 tablas.\n- Muestra claves PK y FK; distingue CASCADE estructural de RESTRICT histórico.\n- Localiza índice único parcial y triggers diferibles.\n- Ejecuta verificacion_esquema.sql, datos_ejemplo.sql y pruebas_integridad.sql.\n- Muestra ERD **generado por la herramienta conectada a PostgreSQL**, compara con diagrama adjunto.\n- Concluye mostrando repositorio y rutas de archivos.\n\nPublica ambos videos en **el mismo canal** y en modo **Público**, verifica sus enlaces y pégalos en Teams. Si usas OBS, combina captura de pantalla con la fuente de webcam encima en la esquina inferior derecha.\n'''
(ROOT/'Guias'/'GUIA_GITHUB_YOUTUBE_Y_EVIDENCIAS.md').write_text(GUIDE,encoding='utf-8')

# ZIP limpio; no se incluyen archivos intermedios de renderizado.
for f in (ROOT/'Validacion').glob('*.png'): f.unlink()
for f in DIA.iterdir():
 if f.is_file() and f.suffix=='': f.unlink()
zipfile_path=ROOT.parent/'Unidad_3_Entregables_Completos.zip'
with zipfile.ZipFile(zipfile_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for f in sorted(ROOT.rglob('*')):
  if f.is_file() and not (f.suffix=='.dot' and f.name.startswith('tmp')):
   z.write(f,arcname=str(f.relative_to(ROOT.parent)))
print(result)
print('PDFs:',p1,p2)
print('ZIP:',zipfile_path,'size',zipfile_path.stat().st_size)
