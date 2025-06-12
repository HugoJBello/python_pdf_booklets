import sys
import os
import fitz  # PyMuPDF
import tempfile

# ===== CONFIGURATION =====
MAX_PAGES_PER_SPLIT = 40  # Ajustable
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "splits")

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_blank_page_like(page):
    """Crea un documento PDF con una página en blanco del tamaño de `page`."""
    blank_doc = fitz.open()
    blank_doc.new_page(width=page.rect.width, height=page.rect.height)
    return blank_doc

def split_pdf(input_pdf_path, max_pages_per_split=MAX_PAGES_PER_SPLIT, same_page_parity=True):
    """
    Divide el PDF en partes, con el máximo de páginas por split.

    Parámetros:
    - input_pdf_path: ruta al PDF original
    - max_pages_per_split: máximo de páginas por split
    - same_page_parity: booleano
        * True: cada split empieza en página par (índice 0-based), excepto el primero que empieza en 0
        * False: añade página en blanco al principio (archivo temporal) y trabaja con este
    """
    if not os.path.isfile(input_pdf_path):
        print(f"Error: el archivo '{input_pdf_path}' no existe.")
        return

    doc_path_to_use = input_pdf_path
    temp_doc = None
    temp_file = None

    if not same_page_parity:
        # Crear PDF temporal con página en blanco al principio
        doc_orig = fitz.open(input_pdf_path)
        temp_doc = fitz.open()

        if len(doc_orig) == 0:
            print("Error: PDF vacío.")
            return
        
        # Crear página en blanco del tamaño de la primera página
        blank_doc = create_blank_page_like(doc_orig[0])
        temp_doc.insert_pdf(blank_doc)
        blank_doc.close()
        # Insertar todas las páginas originales después
        temp_doc.insert_pdf(doc_orig)
        doc_orig.close()

        # Guardar temporal
        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=os.path.dirname(input_pdf_path))
        temp_doc.save(temp_file.name)
        temp_doc.close()
        doc_path_to_use = temp_file.name
        print(f"Archivo temporal creado con página en blanco: {doc_path_to_use}")

    doc = fitz.open(doc_path_to_use)
    ensure_output_dir()

    total_pages = len(doc)
    split_count = 0
    current_index = 0  # Empezamos siempre desde la página 0

    while current_index < total_pages:
        split = fitz.open()

        # Excepto para el primer split, aseguramos que current_index sea par (índice base 0 par)
        if split_count > 0 and current_index % 2 == 1:
            current_index += 1
            if current_index >= total_pages:
                break

        to_page = min(current_index + max_pages_per_split - 1, total_pages - 1)

        # Ajustamos to_page para que el siguiente split empiece en página par (índice base 0 par)
        next_start = to_page + 1
        if next_start < total_pages and next_start % 2 == 1:
            # Si la siguiente página es impar, retrocedemos para que el próximo split comience en par
            to_page -= 1

        # Evitamos que to_page quede antes que current_index
        if to_page < current_index:
            to_page = current_index

        split.insert_pdf(doc, from_page=current_index, to_page=to_page)

        split_count += 1
        output_path = os.path.join(OUTPUT_DIR, f"split{split_count:02}.pdf")
        split.save(output_path)
        split.close()

        print(f"Guardado split {split_count}: páginas {current_index + 1} a {to_page + 1} (base 1)")

        current_index = to_page + 1

    doc.close()

    # Borrar archivo temporal si se creó
    if temp_file is not None:
        try:
            os.remove(doc_path_to_use)
            print(f"Archivo temporal borrado: {doc_path_to_use}")
        except Exception as e:
            print(f"No se pudo borrar el archivo temporal: {e}")

    print(f"✅ PDF dividido en {split_count} partes.")


if __name__ == "__main__":
    if len(sys.argv) not in [2, 3]:
        print("Uso: python split_pdf.py <input_pdf> [same_page_parity]")
        print("same_page_parity opcional: 'true' o 'false' (default true)")
        sys.exit(1)

    input_path = sys.argv[1]

    if len(sys.argv) == 3:
        mode = sys.argv[2].lower()
        if mode == 'true':
            same_page_parity = True
        elif mode == 'false':
            same_page_parity = False
        else:
            print(f"Parámetro inválido para same_page_parity: {sys.argv[2]}")
            sys.exit(1)
    else:
        same_page_parity = True

    split_pdf(input_path, max_pages_per_split=MAX_PAGES_PER_SPLIT, same_page_parity=same_page_parity)

