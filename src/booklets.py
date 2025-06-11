import sys
import os
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter, PageObject, Transformation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape

PAGE_SIZE = landscape(A4)  # tamaño A4 apaisado
#MARGIN_CM = 1.0
MARGIN_CM = 0.0
MARGIN_PT = MARGIN_CM * 28.35  # 1 cm en puntos PDF (~28.35 pts)

def create_blank_half_page(width, height):
    """
    Crea una página en blanco con tamaño dado (se usa para rellenar).
    """
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    can.showPage()
    can.save()
    packet.seek(0)
    blank_pdf = PdfReader(packet)
    return blank_pdf.pages[0]

def crop_page_remove_original_margin(page, original_margin_pts=15 * 28.35 / 10, final_margin_pts=MARGIN_PT):
    """
    Recorta la página para quitar margen original más grande,
    y luego dejar final_margin_pts alrededor.
    original_margin_pts: margen a recortar para eliminar borde original (aprox 1.5 cm)
    final_margin_pts: margen que queremos dejar en el resultado final (1 cm)
    """
    media_box = page.mediabox

    # Primero recortamos margen original (más amplio)
    llx = float(media_box.left) + original_margin_pts
    lly = float(media_box.bottom) + original_margin_pts
    urx = float(media_box.right) - original_margin_pts
    ury = float(media_box.top) - original_margin_pts

    # Luego ajustamos para dejar solo final_margin_pts de margen
    rec_margin = original_margin_pts - final_margin_pts
    if rec_margin < 0:
        rec_margin = 0  # no recortar más si es negativo

    llx += rec_margin
    lly += rec_margin
    urx -= rec_margin
    ury -= rec_margin

    # Evitar que quede inválido
    if urx <= llx or ury <= lly:
        return page

    page.mediabox.lower_left = (llx, lly)
    page.mediabox.upper_right = (urx, ury)

    if page.cropbox:
        page.cropbox.lower_left = (llx, lly)
        page.cropbox.upper_right = (urx, ury)

    return page

def merge_two_pages(page1, page2, page_size=PAGE_SIZE, margin_pts=MARGIN_PT):
    width, height = page_size
    half_width = width / 2

    new_page = PageObject.create_blank_page(width=width, height=height)

    def prepare_page(page):
        # Guardamos caja original
        media_box = page.mediabox
        orig_llx = float(media_box.left)
        orig_lly = float(media_box.bottom)
        orig_urx = float(media_box.right)
        orig_ury = float(media_box.top)

        # Recortamos para eliminar margen original + dejar margen final
        cropped_page = crop_page_remove_original_margin(page, original_margin_pts=15 * 28.35 / 10, final_margin_pts=margin_pts)
        cropped_media_box = cropped_page.mediabox
        crop_llx = float(cropped_media_box.left)
        crop_lly = float(cropped_media_box.bottom)
        crop_urx = float(cropped_media_box.right)
        crop_ury = float(cropped_media_box.top)

        # Tamaño del contenido visible (después de recorte)
        content_width = crop_urx - crop_llx
        content_height = crop_ury - crop_lly

        return cropped_page, content_width, content_height, crop_llx, crop_lly

    # Preparamos ambas páginas
    cpage1, cw1, ch1, cllx1, clly1 = prepare_page(page1)
    cpage2, cw2, ch2, cllx2, clly2 = prepare_page(page2)

    # Calculamos escala para que quepa en mitad de página apaisada
    scale1 = min(half_width / cw1, height / ch1)
    scale2 = min(half_width / cw2, height / ch2)

    # Para centrar cada página en su mitad, calculamos traducción
    tx1 = (half_width - cw1 * scale1) / 2
    ty1 = (height - ch1 * scale1) / 2

    tx2 = half_width + (half_width - cw2 * scale2) / 2
    ty2 = (height - ch2 * scale2) / 2

    # Creamos páginas temporales en blanco para aplicar transformaciones
    temp_page1 = PageObject.create_blank_page(width=width, height=height)
    temp_page1.merge_page(cpage1)
    temp_page1.add_transformation(
        Transformation()
        .translate(tx=-cllx1, ty=-clly1)
        .scale(scale1, scale1)
        .translate(tx=tx1, ty=ty1)
    )

    temp_page2 = PageObject.create_blank_page(width=width, height=height)
    temp_page2.merge_page(cpage2)
    temp_page2.add_transformation(
        Transformation()
        .translate(tx=-cllx2, ty=-clly2)
        .scale(scale2, scale2)
        .translate(tx=tx2, ty=ty2)
    )

    # Mezclamos las dos páginas en la nueva página combinada
    new_page.merge_page(temp_page1)
    new_page.merge_page(temp_page2)

    return new_page

def rotate_booklet_pages(writer):
    for i, page in enumerate(writer.pages):
        if i % 2 == 0:  # rotar páginas con índice par: 0, 2, 4, ...
            page.rotate(180)

def create_booklet(input_path, output_path):
    reader = PdfReader(input_path)
    pages = list(reader.pages)

    if not pages:
        print("❌ El PDF de entrada no contiene páginas.")
        return

    width = float(pages[0].mediabox.width)
    height = float(pages[0].mediabox.height)
    blank = create_blank_half_page(width, height)

    while len(pages) % 4 != 0:
        pages.append(blank)

    total = len(pages)
    print(f"Total páginas (con relleno): {total}")

    booklet_order = []

    for i in range(total // 4):
        left1 = pages[total - 1 - 2 * i]
        right1 = pages[2 * i]
        booklet_order.append((left1, right1))

        left2 = pages[2 * i + 1]
        right2 = pages[total - 2 - 2 * i]
        booklet_order.append((left2, right2))

    print(f"Total pares de páginas combinadas: {len(booklet_order)}")

    writer = PdfWriter()

    for idx, (left, right) in enumerate(booklet_order, 1):
        print(f"Procesando hoja {idx}/{len(booklet_order)}")
        combined = merge_two_pages(left, right, page_size=PAGE_SIZE, margin_pts=MARGIN_PT)
        writer.add_page(combined)

    rotate_booklet_pages(writer)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"✅ Booklet generado correctamente: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python booklet.py entrada.pdf salida.pdf")
        sys.exit(1)

    entrada = sys.argv[1]
    salida = sys.argv[2]

    if not os.path.isfile(entrada):
        print(f"❌ Archivo no encontrado: {entrada}")
        sys.exit(1)

    create_booklet(entrada, salida)

