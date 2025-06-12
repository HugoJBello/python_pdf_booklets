import sys
import os
import fitz  # PyMuPDF

# ===== CONFIGURACIÓN =====
MAX_PAGES_PER_SPLIT = 40  # Combiene que sea par para que no se descabalgue. Si es par, se añade una página en blanco en los splits > 1
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "splits")

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_blank_page_like(page):
    """Crea un documento con una sola página en blanco del mismo tamaño que `page`."""
    blank_doc = fitz.open()
    blank_doc.new_page(width=page.rect.width, height=page.rect.height)
    return blank_doc

def needs_extra_page(doc):
    """Verifica si la primera y segunda página tienen distintas dimensiones."""
    if len(doc) < 2:
        return False
    return doc[0].rect != doc[1].rect

def split_pdf(input_pdf_path, add_initial_page_mode='add_if_needed', max_pages_per_split=MAX_PAGES_PER_SPLIT):
    """
    Divide el PDF en partes.

    Parámetros:
    - input_pdf_path: ruta al PDF original
    - add_initial_page_mode: 'add_forcing', 'not_add' o 'add_if_needed' (default)
    """
    if not os.path.isfile(input_pdf_path):
        print(f"Error: El archivo '{input_pdf_path}' no existe.")
        return

    doc = fitz.open(input_pdf_path)
    ensure_output_dir()

    # Determinar si se añade la página inicial extra al primer split
    if add_initial_page_mode == 'add_forcing':
        insert_extra_page_first = True
    elif add_initial_page_mode == 'not_add':
        insert_extra_page_first = False
    else:  # add_if_needed
        insert_extra_page_first = needs_extra_page(doc)

    total_pages = len(doc)
    split_count = 0

    for i in range(0, total_pages, max_pages_per_split):
        split_count += 1
        split = fitz.open()

        from_page = i
        to_page = min(i + max_pages_per_split - 1, total_pages - 1)
        ref_page_index = min(from_page + 1, total_pages - 1)
        ref_page = doc[ref_page_index]

        # Insertar página en blanco al inicio si es necesario
        if split_count == 1:
            if insert_extra_page_first:
                blank_doc = create_blank_page_like(ref_page)
                split.insert_pdf(blank_doc)
                blank_doc.close()
        else:
            if max_pages_per_split % 2 == 0:
                blank_doc = create_blank_page_like(ref_page)
                split.insert_pdf(blank_doc)
                blank_doc.close()

        # Insertar las páginas correspondientes del documento original
        split.insert_pdf(doc, from_page=from_page, to_page=to_page)

        output_path = os.path.join(OUTPUT_DIR, f"split{split_count:02}.pdf")
        split.save(output_path)
        split.close()

        print(f"Guardado: {output_path}")

    doc.close()
    print(f"✅ Se dividió el PDF en {split_count} parte(s).")


if __name__ == "__main__":
    if len(sys.argv) not in [2, 3]:
        print("Uso: python split_pdf.py <ruta_al_pdf> [modo_pagina_extra]")
        print("modo_pagina_extra opcional: 'add_forcing', 'not_add', 'add_if_needed'")
        sys.exit(1)

    input_path = sys.argv[1]

    if len(sys.argv) == 3:
        mode = sys.argv[2]
        if mode not in ['add_forcing', 'not_add', 'add_if_needed']:
            print(f"Modo no válido: {mode}")
            sys.exit(1)
    else:
        mode = 'add_if_needed'

    split_pdf(input_path, add_initial_page_mode=mode)

