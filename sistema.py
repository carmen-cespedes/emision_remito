import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import webbrowser

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import mm
from datetime import datetime


# ---------------------------------------------------------
#  BASE DE DATOS
# ---------------------------------------------------------

def crear_base():
    conn = sqlite3.connect("facturas.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT,
            fecha TEXT,
            total REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_factura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER,
            cantidad INTEGER,
            producto TEXT,
            precio_unitario REAL,
            subtotal REAL,
            FOREIGN KEY(factura_id) REFERENCES facturas(id)
        )
    """)

    conn.commit()
    conn.close()


def obtener_siguiente_numero():
    conn = sqlite3.connect("facturas.db")
    cursor = conn.cursor()

    cursor.execute("SELECT numero FROM facturas ORDER BY id DESC LIMIT 1")
    ultima = cursor.fetchone()

    conn.close()

    if ultima is None:
        return "0001"

    ultimo_num = int(ultima[0])
    nuevo = str(ultimo_num + 1).zfill(4)
    return nuevo


def guardar_factura(numero, fecha, total, items):
    conn = sqlite3.connect("facturas.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO facturas (numero, fecha, total) VALUES (?, ?, ?)",
                   (numero, fecha, total))

    factura_id = cursor.lastrowid

    # Guardar detalle
    for cant, prod, precio, subtotal in items:
        cursor.execute("""
            INSERT INTO detalle_factura (factura_id, cantidad, producto, precio_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """, (factura_id, cant, prod, precio, subtotal))

    conn.commit()
    conn.close()


# ---------------------------------------------------------
#  PDF — DISEÑO
# ---------------------------------------------------------

rojo = colors.Color(0.72, 0.22, 0.16)
beige = colors.Color(0.93, 0.86, 0.82)

def marco(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(rojo)
    canvas.setLineWidth(2)
    canvas.rect(20, 20, A4[0] - 40, A4[1] - 40)
    canvas.restoreState()


def generar_remito(numero, nombre_archivo, items, total):

    doc = SimpleDocTemplate(
        nombre_archivo,
        pagesize=A4,
        leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    story = []

    # Encabezado
    from reportlab.lib.styles import ParagraphStyle

    # Estilos personalizados
    estilo_titulo = ParagraphStyle(
        name="Titulo",
        alignment=1,  # 1 = centrado
        fontSize=22,
        textColor=rojo,
        leading=26,
        spaceAfter=6
    )
    
    estilo_subtitulo = ParagraphStyle(
        name="Subtitulo",
        alignment=1,
        fontSize=14,
        textColor=rojo,
        leading=18,
        spaceAfter=14
    )

# Encabezado corregido
    titulo = Paragraph("<b>Ferretería San Miguel</b>", estilo_titulo)
    subtitulo = Paragraph(f"<b>Remito N° {numero}</b>", estilo_subtitulo)
    fecha = Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"])

    story.append(titulo)
    story.append(subtitulo)
    story.append(fecha)
    story.append(Spacer(1, 15))


    # Tabla
    encabezado = ["Cantidad", "Producto", "Precio Unitario", "Subtotal"]
    filas = [encabezado]

    for cant, prod, precio, subtotal in items:
        filas.append([cant, prod, f"${precio:,}", f"${subtotal:,}"])

    tabla = Table(filas, colWidths=[25*mm, 85*mm, 32*mm, 32*mm])

    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), beige),
        ('GRID', (0, 0), (-1, -1), 1, rojo),
        ('BOX', (0, 0), (-1, -1), 1.5, rojo),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))

    story.append(tabla)
    story.append(Spacer(1, 20))

    total_txt = f"<para align='right'><font size=14 color='{rojo.hexval()}'><b>Total: ${total:,}</b></font></para>"
    story.append(Paragraph(total_txt, styles["Normal"]))

    story.append(Spacer(1, 20))

    pie = "<para align='center'><font size=10 color='gray'>¡Gracias por su compra!</font></para>"
    story.append(Paragraph(pie, styles["Normal"]))

    doc.build(story, onFirstPage=marco, onLaterPages=marco)



# ---------------------------------------------------------
#  TKINTER
# ---------------------------------------------------------

crear_base()
numero_actual = obtener_siguiente_numero()

root = tk.Tk()
root.title("Sistema de Remitos — Ferretería San Miguel")
root.geometry("900x750")

tk.Label(root, text=f"Remito N° {numero_actual}", font=("Arial", 14, "bold"), fg="red").grid(row=0, column=0, columnspan=4, pady=10)


# Entradas
tk.Label(root, text="Cantidad").grid(row=1, column=0)
tk.Label(root, text="Producto").grid(row=1, column=1)
tk.Label(root, text="Precio Unitario").grid(row=1, column=2)

entry_cant = tk.Entry(root, width=10)
entry_prod = tk.Entry(root, width=30)
entry_precio = tk.Entry(root, width=15)

entry_cant.grid(row=2, column=0)
entry_prod.grid(row=2, column=1)
entry_precio.grid(row=2, column=2)


# Tabla
tree = ttk.Treeview(root, columns=("c","p","pu","s"), show="headings", height=20)
tree.grid(row=4, column=0, columnspan=4, padx=10, pady=10)

for col, txt in zip(("c","p","pu","s"), ("Cantidad","Producto","Precio","Subtotal")):
    tree.heading(col, text=txt)

lista_items = []
total_general = tk.StringVar(value="0")


def agregar_item():
    try:
        cant = int(entry_cant.get())
        prod = entry_prod.get()
        precio = int(entry_precio.get())
        subtotal = cant * precio

        tree.insert("", "end", values=(cant, prod, precio, subtotal))
        lista_items.append([cant, prod, precio, subtotal])

        total_general.set(str(int(total_general.get()) + subtotal))

        entry_cant.delete(0, tk.END)
        entry_prod.delete(0, tk.END)
        entry_precio.delete(0, tk.END)

    except:
        messagebox.showerror("Error", "Datos incorrectos")


def borrar_item():
    sel = tree.selection()
    if not sel:
        return

    for item in sel:
        subtotal = tree.item(item)["values"][3]
        total_general.set(str(int(total_general.get()) - int(subtotal)))
        tree.delete(item)


def nueva_factura():
    global numero_actual
    numero_actual = obtener_siguiente_numero()

    lista_items.clear()
    total_general.set("0")

    for item in tree.get_children():
        tree.delete(item)

    tk.Label(root, text=f"Remito N° {numero_actual}", font=("Arial", 14, "bold"), fg="red").grid(row=0, column=0, columnspan=4)

    entry_cant.delete(0, tk.END)
    entry_prod.delete(0, tk.END)
    entry_precio.delete(0, tk.END)

    messagebox.showinfo("Nueva Factura", "Factura reiniciada")


def generar_pdf():
    if not tree.get_children():
        messagebox.showerror("Error", "No hay ítems")
        return

    items_pdf = []
    total = 0

    for item in tree.get_children():
        c, p, pu, s = tree.item(item)["values"]
        items_pdf.append([c, p, pu, s])
        total += s

    fecha = datetime.now().strftime('%d/%m/%Y')

    guardar_factura(numero_actual, fecha, total, items_pdf)

    nombre = f"remito_{numero_actual}.pdf"
    generar_remito(numero_actual, nombre, items_pdf, total)

    messagebox.showinfo("PDF generado", f"Archivo creado: {nombre}")

    webbrowser.open(os.path.abspath(nombre))



tk.Button(root, text="Agregar Ítem", command=agregar_item).grid(row=3, column=0, pady=10)
tk.Button(root, text="Borrar Ítem", command=borrar_item, bg="orange").grid(row=3, column=1)
tk.Button(root, text="Nueva Factura", command=nueva_factura, bg="red", fg="black").grid(row=3, column=2)
tk.Button(root, text="Generar PDF", command=generar_pdf, bg="green", fg="black").grid(row=3, column=3)

tk.Label(root, text="TOTAL: ").grid(row=5, column=0, sticky="e")
tk.Label(root, textvariable=total_general, font=("Arial", 14, "bold")).grid(row=5, column=1, sticky="w")

root.mainloop()
