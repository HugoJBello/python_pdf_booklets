import os
import shutil
import sys
import fitz  # PyMuPDF
import argparse

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)

from booklets import create_booklet
#from booklets_fitz import create_booklet

from split_pdf import split_pdf

DATA_DIR = os.path.join(BASE_DIR, "..", "data")
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
BOOKLETS_DIR = os.path.join(DATA_DIR, "booklets")


def clear_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path)


def run_split_pdf(input_pdf_path, same_page_parity=True, max_pages_per_split=40):
    split_pdf(input_pdf_path, same_page_parity=same_page_parity, max_pages_per_split=max_pages_per_split)


def process_splits(margin_cm=1.0):
    os.makedirs(BOOKLETS_DIR, exist_ok=True)
    for filename in sorted(os.listdir(SPLITS_DIR)):
        if filename.lower().endswith(".pdf"):
            input_path = os.path.join(SPLITS_DIR, filename)
            output_path = os.path.join(BOOKLETS_DIR, filename)
            create_booklet(input_path, output_path, add_watermark=True, margin_cm=margin_cm)
            print(f"Booklet generado: {output_path}")


def merge_booklets(output_file):
    merged = fitz.open()
    for filename in sorted(os.listdir(BOOKLETS_DIR)):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(BOOKLETS_DIR, filename)
            with fitz.open(pdf_path) as doc:
                merged.insert_pdf(doc)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    merged.save(output_file)
    print(f"PDF final generado en: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Procesar un PDF y generar un booklet combinado.")
    parser.add_argument("input_pdf", help="Ruta al archivo PDF de entrada.")
    parser.add_argument("--output", "-o", type=str, help="Ruta al archivo PDF de salida (opcional).")
    parser.add_argument("--max_pages_per_split", "-max", type=int, default=40, help="Máximo número de páginas en cada booklet")
    parser.add_argument("--same_page_parity", "-spp", type=str, default="true",
                        help="Si es 'true' cada split empieza en página impar (1-based). "
                             "Si es 'false' añade página en blanco al principio y splits empiezan en página par.")
    parser.add_argument("--margin", "-m", type=float, default=1.0, help="Margen en cm a dejar (default: 1.0)")

    args = parser.parse_args()

    input_pdf = args.input_pdf
    max_pages_per_split = args.max_pages_per_split

    # Parseamos same_page_parity a booleano
    spp_str = args.same_page_parity.lower()
    if spp_str == "true":
        same_page_parity = True
    elif spp_str == "false":
        same_page_parity = False
    else:
        print(f"Valor inválido para --same_page_parity: {args.same_page_parity}. Debe ser 'true' o 'false'.")
        sys.exit(1)

    if not os.path.isfile(input_pdf):
        print(f"Error: No se encontró el archivo: {input_pdf}")
        sys.exit(1)

    if args.output:
        output_file = args.output
    else:
        input_filename = os.path.splitext(os.path.basename(input_pdf))[0]
        output_file = os.path.join(DATA_DIR, f"{input_filename}_booklets_for_printing.pdf")

    margin_cm = args.margin

    print("Limpiando carpeta splits...")
    clear_folder(SPLITS_DIR)
    
    print("Limpiando carpeta booklets...")
    clear_folder(BOOKLETS_DIR)

    print("Rompiendo en pdfs y añadiendo marcas de agua")
    run_split_pdf(input_pdf, same_page_parity=same_page_parity, max_pages_per_split=max_pages_per_split)

    print("Procesando splits para crear booklets...")
    process_splits(margin_cm=margin_cm)

    print("Uniendo booklets en PDF final...")
    merge_booklets(output_file)


if __name__ == "__main__":
    main()

