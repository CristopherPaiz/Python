import pandas as pd
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, legal, portrait, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.units import inch
from datetime import datetime
import calendar

# Diccionario de traducción para los encabezados
TRANSLATIONS = {
    'account': 'Cuenta',
    'amount': 'Monto',
    'currency': 'Moneda',
    'title': 'Título',
    'note': 'Nota',
    'date': 'Fecha',
    'income': 'Ingreso',
    'category name': 'Categoría',
    'balance': 'Balance'
}

# Nombres de los meses en español
MONTH_NAMES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

# Función para formatear fecha
def format_date(date_str):
    try:
        if pd.isna(date_str):
            return ""
        # Parsear la fecha
        dt = datetime.strptime(str(date_str).split('.')[0], '%Y-%m-%d %H:%M:%S')
        # Formatear a DD/MM/YYYY HH:MM:SS AM/PM
        return dt.strftime('%d/%m/%Y  -   %I:%M%p')
    except Exception as e:
        print(f"Error al formatear fecha {date_str}: {e}")
        return str(date_str)  # Devolver original si hay error

# Función para extraer mes y año de una fecha
def extract_month_year(date_str):
    try:
        if pd.isna(date_str):
            return None
        # Parsear la fecha
        dt = datetime.strptime(str(date_str).split('.')[0], '%Y-%m-%d %H:%M:%S')
        # Devolver un tuple (año, mes)
        return (dt.year, dt.month)
    except Exception as e:
        print(f"Error al extraer mes/año de {date_str}: {e}")
        return None

# Función para crear PDF desde datos CSV
def create_pdf_from_csv(csv_file, output_pdf):
    # Leer archivo CSV
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error al leer archivo CSV: {e}")
        return

    # Verificar columnas requeridas
    required_cols = ['account', 'title', 'category name', 'note', 'date','currency', 'amount']
    # Filtrar columnas que existen en el CSV
    existing_cols = [col for col in required_cols if col in df.columns]

    if not existing_cols:
        print(f"No se encontraron columnas requeridas en {csv_file}")
        return

    # Seleccionar solo las columnas que necesitamos
    df = df[existing_cols]

    # Convertir 'amount' a numérico, manejando posibles errores
    if 'amount' in existing_cols:
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    # Formatear fecha y extraer mes/año para agrupación
    if 'date' in existing_cols:
        df['formatted_date'] = df['date'].apply(format_date)
        df['month_year'] = df['date'].apply(extract_month_year)
        df['sort_date'] = pd.to_datetime(df['date'], errors='coerce')

        # Ordenar DataFrame por fecha (más antigua primero)
        df = df.sort_values(by='sort_date')

    # Calcular balance acumulado
    df['balance'] = df['amount'].cumsum()

    # Crear documento PDF
    doc = SimpleDocTemplate(output_pdf, pagesize=landscape(legal),
                           rightMargin=35, leftMargin=35,
                           topMargin=35, bottomMargin=35)

    # Definir estilos
    styles = getSampleStyleSheet()
    left_style = ParagraphStyle(
        'LeftStyle',
        parent=styles['Normal'],
        alignment=TA_LEFT,
        wordWrap='CJK',  # Asegura correcto ajuste de texto
        fontSize=8,
        leading=10  # Espaciado de línea
    )

    center_style = ParagraphStyle(
        'CenterStyle',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        wordWrap='CJK',
        fontSize=8,
        leading=10
    )

    right_style = ParagraphStyle(
        'RightStyle',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        wordWrap='CJK',
        fontSize=8,
        leading=10
    )

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=18,
        spaceAfter=12
    )

    month_header_style = ParagraphStyle(
        'MonthHeaderStyle',
        parent=styles['Heading2'],
        alignment=TA_LEFT,
        fontSize=10,
        textColor=colors.black,
        leading=12
    )

    # Definir anchos de columna (porcentajes del ancho de página)
    width_percentages = {
        '#': 0.03,            # Columna para numeración
        'account': 0.06,
        'amount': 0.08,
        'currency': 0.05,
        'title': 0.15,
        'note': 0.28,         # Reducido de 0.29 a 0.22
        'date': 0.12,
        'income': 0.04,
        'category name': 0.14,
        'balance': 0.07       # Nueva columna para balance acumulado
    }

    # Añadimos # al inicio de la lista de columnas y balance al final
    display_cols = ['#'] + existing_cols + ['balance']

    # Calcular anchos reales basados en tamaño de página
    page_width = landscape(legal)[0] - 40  # Considerando márgenes
    col_widths = [width_percentages.get(col, 0.1) * page_width for col in display_cols]

    # Crear encabezado para tabla (traducido)
    header = [Paragraph("<b>#</b>", center_style)]  # Columna de numeración
    header.extend([Paragraph(f"<b>{TRANSLATIONS.get(col, col)}</b>", left_style) for col in existing_cols])
    header.append(Paragraph(f"<b>{TRANSLATIONS.get('balance', 'Balance')}</b>", right_style))  # Columna de balance

    # Formatear datos para tabla
    table_data = [header]

    # Variable para rastrear cambios de mes y contador de filas
    current_month_year = None
    month_header_indexes = []  # Para rastrear índices donde están los encabezados de mes
    row_counter = 1  # Contador para numerar filas

    # Procesar cada fila y agregar encabezados de mes
    for idx, row in df.iterrows():
        # Detectar cambio de mes
        if 'month_year' in df.columns:
            row_month_year = row['month_year']
            if current_month_year != row_month_year and row_month_year is not None:
                current_month_year = row_month_year
                year, month = row_month_year
                month_name = MONTH_NAMES.get(month, str(month))

                # Crear fila de encabezado de mes
                month_title = f"<b>{month_name} {year}</b>"
                month_header_row = ['']  # Celda vacía para la columna de numeración
                month_header_row.append(Paragraph(month_title, month_header_style))
                # Extender con celdas vacías para completar la fila (incluyendo balance)
                month_header_row.extend(['' for _ in range(len(existing_cols) + 1 - 1)])

                # Agregar esta fila a la tabla
                table_data.append(month_header_row)
                # Guardar el índice para aplicar estilos después
                month_header_indexes.append(len(table_data) - 1)

        # Crear fila regular para la tabla
        table_row = [Paragraph(f"<b>{row_counter}</b>", center_style)]  # Número de fila centrado y en negrita
        for col in existing_cols:
            # Para la columna date, usar la versión formateada
            if col == 'date' and 'formatted_date' in df.columns:
                cell_value = str(row['formatted_date']) if pd.notna(row['formatted_date']) else ""
            else:
                cell_value = str(row[col]) if pd.notna(row[col]) else ""

            # Manejar saltos de línea en texto
            cell_value = cell_value.replace("\n", "<br/>")
            # Crear párrafo con estilo adecuado para cada celda
            para = Paragraph(cell_value, left_style)
            table_row.append(para)

        # Añadir balance acumulado (alineado a la derecha)
        balance_value = float(row['balance']) if pd.notna(row['balance']) else 0
        balance_cell = f"Q{balance_value:.2f}"
        table_row.append(Paragraph(balance_cell, right_style))

        table_data.append(table_row)
        row_counter += 1  # Incrementar contador de filas

    # Crear tabla
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Aplicar estilos a la tabla
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.steelblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Alinear columna de numeración al centro
        ('ALIGN', (1, 0), (-2, -1), 'LEFT'),   # Alinear columnas intermedias a la izquierda
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),  # Alinear columna de balance a la derecha
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centrado verticalmente
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ])

    # Aplicar estilos especiales a los encabezados de mes
    for idx in month_header_indexes:
        # Fondo azul claro para los encabezados de mes
        style.add('BACKGROUND', (0, idx), (-1, idx), colors.mintcream)
        # Unir celdas desde la segunda columna (después de #) hasta el final
        style.add('SPAN', (1, idx), (-1, idx))
        # Quitar bordes internos
        style.add('GRID', (0, idx), (-1, idx), 0.5, colors.black)
        # Borde superior e inferior más gruesos
        style.add('LINEABOVE', (0, idx), (-1, idx), 1.5, colors.black)
        style.add('LINEBELOW', (0, idx), (-1, idx), 1.5, colors.black)
        # Mayor espacio antes del encabezado de mes
        style.add('TOPPADDING', (0, idx), (-1, idx), 12)
        # Mayor espacio después del encabezado de mes
        style.add('BOTTOMPADDING', (0, idx), (-1, idx), 12)

    # Añadir formato condicional basado en 'amount' para las filas regulares
    if 'amount' in existing_cols:
        for i in range(1, len(table_data)):
            # Saltar las filas de encabezado de mes
            if i in month_header_indexes:
                continue

            try:
                # Calcular el índice correspondiente en el DataFrame
                # Restando los encabezados de mes que se hayan insertado antes de esta fila
                df_idx = i - 1 - sum(1 for idx in month_header_indexes if idx < i)

                if df_idx < len(df):
                    amount_val = float(df.iloc[df_idx]['amount']) if pd.notna(df.iloc[df_idx]['amount']) else 0
                    balance_val = float(df.iloc[df_idx]['balance']) if pd.notna(df.iloc[df_idx]['balance']) else 0
                    bg_color = colors.palegreen if amount_val >= 0 else colors.salmon

                    # Aplicar color de fondo según el valor
                    style.add('BACKGROUND', (0, i), (-2, i), bg_color)

                    # Aplicar color al balance según sea positivo o negativo
                    balance_color = colors.palegreen if balance_val >= 0 else colors.salmon
                    style.add('BACKGROUND', (-1, i), (-1, i), balance_color)
            except Exception as e:
                print(f"Error al aplicar color a fila {i}: {e}")

    table.setStyle(style)

    # Elementos para el PDF
    elements = []

    # Agregar título principal
    title = Paragraph("Reporte de Transacciones", title_style)
    elements.append(title)
    elements.append(Spacer(1, 10))

    # Agregar la tabla principal
    elements.append(table)
    elements.append(Spacer(1, 30))

    # RESUMEN POR MESES
    if 'month_year' in df.columns and 'amount' in df.columns:
        # Agrupar por mes y año
        monthly_data = []

        for month_year in sorted(df['month_year'].dropna().unique()):
            if month_year is None:
                continue

            year, month = month_year
            month_filter = df['month_year'] == month_year

            # Calcular totales para este mes
            month_income = df[month_filter & (df['amount'] > 0)]['amount'].sum()
            month_expense = df[month_filter & (df['amount'] < 0)]['amount'].sum()
            month_net = month_income + month_expense

            monthly_data.append({
                'year': year,
                'month': month,
                'month_name': MONTH_NAMES.get(month, str(month)),
                'income': month_income,
                'expense': month_expense,
                'net': month_net
            })

        # Ordenar por fecha (más antigua primero)
        monthly_data = sorted(monthly_data, key=lambda x: (x['year'], x['month']))

        if monthly_data:
            # Crear título para el resumen mensual
            monthly_title = Paragraph("Resumen por Meses", title_style)
            elements.append(monthly_title)
            infobox = Paragraph("Este resumen muestra los ingresos, egresos y balance de cada mes de forma independiente, sin considerar acumulados o saldos previos. Es decir, solo refleja el dinero que entró y salió en ese mes específico.", center_style)
            elements.append(infobox)
            infobox2 = Paragraph("Ejemplo: Si en enero tuviste un ingreso de Q1,000 y un gasto de Q200, el balance del mes será Q800. Luego, si en febrero no ingresó nada y gastaste Q300, el balance de febrero será -Q300, aunque todavía tengas dinero de enero.", center_style)
            elements.append(infobox2)
            elements.append(Spacer(1, 15))

            # Crear tablas mensuales - 5 por fila
            max_tables_per_row = 5
            tables_in_current_row = 0
            current_row_tables = []

            for month_data in monthly_data:
                # Crear datos para la tabla de este mes
                month_table_data = [
                    [f"{month_data['month_name']} {month_data['year']}"],
                    ["Ingresos:", f"Q{month_data['income']:.2f}"],
                    ["Egresos:", f"Q{month_data['expense']:.2f}"],
                    ["Balance:", f"Q{month_data['net']:.2f}"]
                ]

                # Crear tabla para este mes
                month_table = Table(month_table_data, colWidths=[1.1*inch, 1.1*inch])
                month_style = TableStyle([
                    ('BACKGROUND', (0, 0), (1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
                    ('SPAN', (0, 0), (1, 0)),  # Unir celdas para el título
                    ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                    ('GRID', (0, 0), (1, -1), 0.5, colors.black),
                    ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (1, -1), 4),
                    ('TOPPADDING', (0, 0), (1, -1), 4),
                    ('BACKGROUND', (0, -1), (1, -1), colors.limegreen if month_data['net'] >= 0 else colors.tomato),
                ])
                month_table.setStyle(month_style)

                # Agregar la tabla y un espaciador para separación
                current_row_tables.append(month_table)
                tables_in_current_row += 1

                # Si completamos la fila o es el último mes, agregar la fila al PDF
                if tables_in_current_row == max_tables_per_row or month_data == monthly_data[-1]:
                    # Si no llenamos la fila, agregar tablas vacías
                    while tables_in_current_row < max_tables_per_row:
                        current_row_tables.append(Spacer(1, 1))
                        tables_in_current_row += 1

                    # Crear una tabla que contenga las tablas de la fila actual
                    row_table = Table([current_row_tables],
                                     colWidths=[2.2*inch] * max_tables_per_row)

                    # Mayor espaciado entre tablas mensuales
                    row_table_style = TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 15),  # Más espacio entre tablas
                        ('RIGHTPADDING', (0, 0), (-1, -1), 15), # Más espacio entre tablas
                    ])
                    row_table.setStyle(row_table_style)

                    elements.append(row_table)
                    elements.append(Spacer(1, 15))

                    # Reiniciar para la siguiente fila
                    current_row_tables = []
                    tables_in_current_row = 0

            elements.append(Spacer(1, 20))

    # Calcular totales generales
    income_total = df[df['amount'] > 0]['amount'].sum() if 'amount' in df.columns else 0
    expense_total = df[df['amount'] < 0]['amount'].sum() if 'amount' in df.columns else 0
    net_total = income_total + expense_total  # expense_total ya es negativo
    final_balance = df['balance'].iloc[-1] if not df.empty and 'balance' in df.columns else 0

    # Crear tabla de totales generales (más grande)
    totals_title = Paragraph("Resumen General", title_style)
    elements.append(totals_title)
    infobox3 = Paragraph("Este resumen muestra los totales de ingresos, egresos y el balance final de todas las transacciones de todas las fechas, desde la primera transacción hasta la última.", center_style)
    elements.append(infobox3)
    infobox4 = Paragraph("El balance final es el resultado de sumar todos los ingresos y egresos, reflejando cuánto dinero tienes en total después de todas las transacciones.", center_style)
    elements.append(infobox4)
    elements.append(Spacer(1, 15))

    totals_data = [
        ["RESUMEN", ""],
        ["Total Ingresos:", f"Q{income_total:.2f}"],
        ["Total Egresos:", f"Q{expense_total:.2f}"],
        ["Balance Final:", f"Q{final_balance:.2f}"]
    ]

    totals_table = Table(totals_data, colWidths=[3*inch, 2*inch])
    totals_style = TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, -1), (1, -1), colors.lightgreen if final_balance >= 0 else colors.lightcoral),
        ('BOTTOMPADDING', (0, 0), (1, -1), 8),
        ('TOPPADDING', (0, 0), (1, -1), 8),
        ('FONTSIZE', (0, 0), (1, -1), 12),  # Texto más grande
    ])

    totals_table.setStyle(totals_style)

    elements.append(totals_table)

    # Construir el PDF
    doc.build(elements)
    print(f"PDF creado: {output_pdf}")

# Función principal para procesar todos los archivos CSV
def process_all_csvs(directory):
    # Obtener todos los archivos CSV en el directorio
    csv_files = [f for f in os.listdir(directory) if f.lower().endswith('.csv')]

    if not csv_files:
        print(f"No se encontraron archivos CSV en {directory}")
        return

    print(f"Se encontraron {len(csv_files)} archivos CSV para procesar.")

    for csv_file in csv_files:
        input_path = os.path.join(directory, csv_file)
        output_pdf = os.path.join(directory, os.path.splitext(csv_file)[0] + '.pdf')

        print(f"Procesando {csv_file}...")
        try:
            create_pdf_from_csv(input_path, output_pdf)
            print(f"PDF creado exitosamente: {output_pdf}")
        except Exception as e:
            print(f"Error al procesar {csv_file}: {str(e)}")

if __name__ == "__main__":
    download_folder = r"C:\Users\crist\Downloads"
    print(f"Iniciando procesamiento de archivos CSV en: {download_folder}")
    process_all_csvs(download_folder)
    print("Proceso completado.")