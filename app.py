from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = "secret_key"  # Clave secreta para manejar las sesiones y los mensajes flash

load_dotenv()  # Cargar variables de entorno

db_config = {
    'host': os.getenv("HOST"),
    'user': os.getenv("USER"),
    'password': os.getenv("PASSWORD"),
    'database': os.getenv("DATABASE"),
    'port': 3306  # Asegúrate de convertir el puerto a entero
}

# Crear una función de conexión
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Ruta principal para mostrar el menú principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para manejar la inserción de nuevas entradas
@app.route('/add_entry', methods=['POST'])
def add_entry():
    if request.method == 'POST':
        id_producto = request.form.get('producto_id')
        cantidad = request.form.get('cantidad')
        ubicacion = request.form.get('ubicacion')  # Nuevo campo para ubicación

        # Validar que los campos no estén vacíos y que cantidad sea un número
        if not id_producto or not cantidad or not ubicacion:
            flash('Todos los campos son obligatorios.')
            return redirect(url_for('add_entrada'))

        try:
            cantidad = int(cantidad)  # Convertir cantidad a entero
        except ValueError:
            flash('Cantidad inválida.')
            return redirect(url_for('add_entrada'))

        db = get_db_connection()  # Obtén la conexión
        cursor = db.cursor()
        cursor.execute("INSERT INTO entradas (id_producto, cantidad, ubicacion) VALUES (%s, %s, %s)",
                       (id_producto, cantidad, ubicacion))
        db.commit()
        cursor.close()
        db.close()  # Cierra la conexión
        flash('Entrada añadida correctamente!')
        return redirect(url_for('add_entrada'))

# Ruta para agregar nuevos productos
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        categoria = request.form['categoria']  # Captura la categoría del formulario

        # Validar que los campos no estén vacíos
        if not nombre or not descripcion or not precio or not categoria:
            flash('Todos los campos son obligatorios.')
            return redirect(url_for('add_product'))

        # Validar que el precio sea un número decimal válido
        try:
            precio = float(precio)
        except ValueError:
            flash('Precio inválido.')
            return redirect(url_for('add_product'))

        db = get_db_connection()  # Obtén la conexión
        cursor = db.cursor()
        cursor.execute("INSERT INTO productos (nombre, descripcion, precio, categoria) VALUES (%s, %s, %s, %s)",
                       (nombre, descripcion, precio, categoria))
        db.commit()
        cursor.close()
        db.close()  # Cierra la conexión
        flash('Producto agregado correctamente!')
        return redirect(url_for('add_product'))
    return render_template('add_product.html')

# Ruta para mostrar todas las entradas
@app.route('/entradas')
def show_entries():
    db = get_db_connection()  # Obtén la conexión
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.id_entrada, p.nombre AS producto, e.cantidad, e.ubicacion, e.fecha_entrada 
        FROM entradas e 
        INNER JOIN productos p ON e.id_producto = p.id_producto
    """)
    entradas = cursor.fetchall()
    cursor.close()
    db.close()  # Cierra la conexión
    return render_template('entradas.html', entradas=entradas)

# Ruta para registrar salidas de productos
@app.route('/add_salida', methods=['GET', 'POST'])
def add_salida():
    if request.method == 'POST':
        id_producto = request.form.get('producto_id')
        cantidad = request.form.get('cantidad')

        # Validar que los campos no estén vacíos y que cantidad sea un número
        if not id_producto or not cantidad:
            flash('Todos los campos son obligatorios.')
            return redirect(url_for('add_salida'))

        try:
            cantidad = int(cantidad)  # Convertir cantidad a entero
        except ValueError:
            flash('Cantidad inválida.')
            return redirect(url_for('add_salida'))

        db = get_db_connection()  # Obtén la conexión
        cursor = db.cursor()
        cursor.execute("SELECT COALESCE(SUM(cantidad), 0) FROM entradas WHERE id_producto = %s", (id_producto,))
        total_entradas = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(cantidad), 0) FROM salidas WHERE id_producto = %s", (id_producto,))
        total_salidas = cursor.fetchone()[0]

        stock_actual = total_entradas - total_salidas

        if cantidad > stock_actual:
            flash(f'La cantidad solicitada supera el stock disponible ({stock_actual} unidades).')
            cursor.close()
            db.close()  # Cierra la conexión
            return redirect(url_for('add_salida'))

        cursor.execute("INSERT INTO salidas (id_producto, cantidad) VALUES (%s, %s)", (id_producto, cantidad))
        db.commit()
        cursor.close()
        db.close()  # Cierra la conexión
        flash('Salida registrada correctamente!')
        return redirect(url_for('add_salida'))

    db = get_db_connection()  # Obtén la conexión
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id_producto, nombre FROM productos")
    productos = cursor.fetchall()
    cursor.close()
    db.close()  # Cierra la conexión
    return render_template('add_salida.html', productos=productos)

# Ruta para mostrar todas las salidas
@app.route('/salidas')
def show_salidas():
    db = get_db_connection()  # Obtén la conexión
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id_salida, p.nombre AS producto, s.cantidad, s.fecha_salida 
        FROM salidas s 
        INNER JOIN productos p ON s.id_producto = p.id_producto
    """)
    salidas = cursor.fetchall()
    cursor.close()
    db.close()  # Cierra la conexión
    return render_template('salidas.html', salidas=salidas)

# Nueva ruta para agregar entradas de productos
@app.route('/add_entrada')
def add_entrada():
    db = get_db_connection()  # Obtén la conexión
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id_producto, nombre FROM productos")
    productos = cursor.fetchall()
    cursor.close()
    db.close()  # Cierra la conexión
    return render_template('add_entrada.html', productos=productos)

@app.route('/stock_por_ubicacion')
def stock_por_ubicacion():
    filtro_ubicacion = request.args.get('ubicacion')  # Obtener el valor del filtro
    db = get_db_connection()  # Obtén la conexión
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT DISTINCT ubicacion FROM entradas")
    ubicaciones = [row['ubicacion'] for row in cursor.fetchall()]
    
    query = """
        SELECT p.nombre AS producto, e.ubicacion, 
               (COALESCE(SUM(e.cantidad), 0) - COALESCE((SELECT COALESCE(SUM(s.cantidad), 0) 
                                                          FROM salidas s 
                                                          WHERE s.id_producto = e.id_producto), 0)) AS stock
        FROM entradas e
        INNER JOIN productos p ON e.id_producto = p.id_producto
    """
    
    if filtro_ubicacion:
        query += " WHERE e.ubicacion = %s GROUP BY e.id_producto, e.ubicacion HAVING stock > 0"
        cursor.execute(query, (filtro_ubicacion,))
    else:
        query += " GROUP BY e.id_producto, e.ubicacion HAVING stock > 0"
        cursor.execute(query)
    
    stock_data = cursor.fetchall()
    cursor.close()
    db.close()  # Cierra la conexión
    
    return render_template('stock_por_ubicacion.html', stock_data=stock_data, ubicaciones=ubicaciones, filtro_ubicacion=filtro_ubicacion)

@app.route('/descargar_plantilla')
def descargar_plantilla():
    return send_file('templates/plantilla_productos.xlsx', as_attachment=True)

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    if 'excel_file' not in request.files:
        flash('No se seleccionó ningún archivo.')
        return redirect(url_for('add_product'))
    
    file = request.files['excel_file']
    
    try:
        data = pd.read_excel(file)
        required_columns = {'Nombre', 'Descripción', 'Precio', 'Categoría'}
        if not required_columns.issubset(data.columns):
            flash('La plantilla Excel no tiene las columnas requeridas.')
            return redirect(url_for('add_product'))
        
        db = get_db_connection()  # Obtén la conexión
        cursor = db.cursor()
        for _, row in data.iterrows():
            cursor.execute(
                "INSERT INTO productos (nombre, descripcion, precio, categoria) VALUES (%s, %s, %s, %s)",
                (row['Nombre'], row['Descripción'], float(row['Precio']), row['Categoría'])
            )
        db.commit()
        cursor.close()
        db.close()  # Cierra la conexión
        
        flash('Productos cargados exitosamente desde Excel.')
    except Exception as e:
        flash(f'Error al procesar el archivo: {str(e)}')
    
    return redirect(url_for('add_product'))

if __name__ == '__main__':
    app.run(debug=True)
    

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 
