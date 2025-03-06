from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
import os
import json
import requests
app = Flask(__name__)
app.secret_key = 'clave_secreta'

# Ruta de la carpeta para guardar los PDFs
PDF_FOLDER = os.path.join(os.getcwd(), 'generated_pdfs')
if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

# Lista de usuarios autorizados con contraseñas y nombres predeterminados
USERS_FILE = 'users.txt'
AUTHORIZED_USERS = {}

def load_users():
    global AUTHORIZED_USERS
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as file:
            for line in file.readlines():
                try:
                    user, password, full_name, dni, cargo = [item.strip() for item in line.split(',')]
                    AUTHORIZED_USERS[user] = {
                        'password': password,
                        'full_name': full_name,
                        'dni': dni,
                        'cargo': cargo
                    }
                except ValueError:
                    print(f"Error al cargar la línea: {line.strip()} - Se esperaban 5 valores, pero se encontraron menos.")
    print(f"Usuarios cargados: {AUTHORIZED_USERS}")  # Depuración

load_users()

# Redirigir al login por defecto
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('user')
        password = request.form.get('password')

        if user in AUTHORIZED_USERS and AUTHORIZED_USERS[user]['password'] == password:
            session['user'] = user  # Guardar el usuario en la sesión
            session['user_full_name'] = AUTHORIZED_USERS[user]['full_name']
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
    return render_template('login.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user', None)  # Eliminar el usuario de la sesión
    return redirect(url_for('login'))

# Ruta principal (formulario)
@app.route('/index', methods=['GET', 'POST'])
def index():
    # Verificar si el usuario está autenticado
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Obtener datos del formulario
        name = request.form.get('name')
        last_name = request.form.get('last_name')
        dni = request.form.get('dni')
        tipo_persona = request.form.get('tipo_persona')
        area = request.form.get('area') if tipo_persona == 'Empleado' else ''
        cargo = request.form.get('cargo') if tipo_persona == 'Empleado' else ''
        unidad = request.form.get('unidad')
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')

        # Obtener datos de los dispositivos (JSON)
        dispositivos_raw = request.form.get('dispositivos')
        dispositivos = json.loads(dispositivos_raw)

        # Obtener datos del administrador
        admin_full_name = AUTHORIZED_USERS[session['user']]['full_name']
        admin_dni = AUTHORIZED_USERS[session['user']]['dni']
        admin_cargo = AUTHORIZED_USERS[session['user']]['cargo']

        # Generar el PDF
        pdf_filename = f"{name}_{last_name}.pdf"
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
        generate_pdf(pdf_path, name, last_name, dni, tipo_persona, area, cargo, unidad,
                     fecha_inicio, fecha_fin, dispositivos, admin_full_name, admin_dni, admin_cargo)

        # Responder con el nombre del archivo generado
        return jsonify({'success': True, 'filename': pdf_filename})

    return render_template('form.html')

# Ruta para servir el PDF
@app.route('/pdf/<filename>')
def view_pdf(filename):
    return send_from_directory(PDF_FOLDER, filename)
# Función para generar el PDF
def generate_pdf(output_path, name, last_name, dni, tipo_persona, area, cargo, unidad,
                 fecha_inicio, fecha_fin, dispositivos, admin_full_name, admin_dni, admin_cargo):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # Margen superior e inferior
    top_margin = height - 50
    bottom_margin = 50

    # Encabezado (Logo y Título)
    logo_path = os.path.join(os.getcwd(), 'static', 'logo.png')
    if os.path.exists(logo_path):
        c.drawImage(logo_path, 50, top_margin - 40, width=100, height=50, mask='auto')  # Logo más arriba

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, top_margin - 70, "Formato Permiso de Ingreso o Salida")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, top_margin - 90, "de Materiales, Equipos, Residuos, Material con Restricción y/o Matpel")
    c.line(50, top_margin - 105, width - 50, top_margin - 105)
    # Datos Personales
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, top_margin - 130, "Datos Personales")
    c.setFont("Helvetica", 10)
    c.drawString(50, top_margin - 150, f"Nombre: {name}")
    c.drawString(50, top_margin - 170, f"Apellido: {last_name}")
    c.drawString(50, top_margin - 190, f"DNI: {dni}")
    c.drawString(50, top_margin - 210, f"Tipo de Persona: {tipo_persona}")
    c.drawString(50, top_margin - 230, f"Área: {area if tipo_persona == 'Empleado' else 'N/A'}")
    c.drawString(50, top_margin - 250, f"Cargo: {cargo if tipo_persona == 'Empleado' else 'N/A'}")
    c.drawString(50, top_margin - 270, f"Unidad: {unidad}")

    # Fecha de Vigencia (Resaltada)
    c.setFillColorRGB(0.9, 0.9, 0.9)  # Fondo gris claro
    c.rect(50, top_margin - 300, 400, 20, fill=True, stroke=False)
    c.setFillColorRGB(0, 0, 0)  # Texto negro
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, top_margin - 295, f"Fecha de Vigencia: {fecha_inicio} - {fecha_fin}")

    # Línea divisoria
    c.line(50, top_margin - 320, width - 50, top_margin - 320)

    # Dispositivos Registrados (Tabla Mejorada)
    if dispositivos:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, top_margin - 340, "Dispositivos Registrados")
        data = [["Dispositivo", "Marca", "Modelo", "Número de Serie"]]
        
        # Procesar los datos de los dispositivos
        row_heights = [20]  
        for dispositivo in dispositivos:
            dispositivo_text = split_text(dispositivo['dispositivo'], 20)
            marca_text = split_text(dispositivo['marca'], 20)
            modelo_text = split_text(dispositivo['modelo'], 20)
            serie_text = split_text(dispositivo['numero_serie'], 20)
            max_lines = max(len(dispositivo_text.split('\n')), len(marca_text.split('\n')),
                            len(modelo_text.split('\n')), len(serie_text.split('\n')))
            row_heights.append(max_lines * 12 + 8)  # Altura dinámica basada en el número de líneas
            data.append([dispositivo_text, marca_text, modelo_text, serie_text])
        table_height = sum(row_heights)

        # Ajustar la posición inicial de la tabla
        table_start_y = top_margin - 360 - table_height  # Comenzar más arriba según la altura total

        # Crear la tabla con ajustes automáticos
        table = Table(data, colWidths=[130, 130, 130, 130], rowHeights=None)  # Ancho de columnas ajustado
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.mediumspringgreen),  # Encabezado con fondo verde
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Texto negro en el encabezado
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Alinear todo al centro
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Fuente negrita para el encabezado
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Espaciado inferior en el encabezado
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Fondo blanco para las filas
            ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Bordes claros
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Alinear verticalmente al centro
            ('LEADING', (0, 0), (-1, -1), 12),  # Espaciado entre líneas
        ]))
        table.wrapOn(c, width, height)
        table.drawOn(c, 50, table_start_y)

    # Línea divisoria
    c.line(50, top_margin - 520, width - 50, top_margin - 520)

    # Datos del Administrador
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, top_margin - 540, "AUTORIZADO POR:")
    c.setFont("Helvetica", 13)
    c.drawString(50, top_margin - 560, f"Nombre y Apellidos: {admin_full_name}")
    c.drawString(50, top_margin - 580, f"DNI: {admin_dni}")
    c.drawString(50, top_margin - 600, f"Cargo: {admin_cargo}")

    # Línea divisoria
    c.line(50, top_margin - 630, width - 50, top_margin - 630)

    # Advertencia Completa
    advertencia = ("ADVERTENCIA: Las copias de este documento son Copias No controladas. "
                   "Es responsabilidad del usuario verificar en el prospector de vigencia de este documento antes de uso. "
                   "Esta prohibido modificar, falsificar o manipular el documento.")
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.8, 0, 0)  # Rojo claro para resaltar la advertencia
    c.drawString(50, bottom_margin + 20, advertencia[:120])  # Primera parte del texto
    c.drawString(50, bottom_margin + 10, advertencia[120:])  # Segunda parte del texto

    # Guardar el PDF
    c.save()

# Función auxiliar para dividir texto largo en varias líneas
def split_text(text, max_length):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_length:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())
    return "\n".join(lines)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
