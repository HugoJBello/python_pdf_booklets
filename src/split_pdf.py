import sys
import os
import fitz  # PyMuPDF

# ===== CONFIGURATION =====
MAX_PAGES_PER_SPLIT = 40  # Recommended to be even for best results
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "splits")

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_blank_page_like(page):
    """Creates a blank page document matching the size of `page`. (Kept for compatibility, not used here)"""
    blank_doc = fitz.open()
    blank_doc.new_page(width=page.rect.width, height=page.rect.height)
    return blank_doc

def needs_extra_page(doc):
    """Checks if first and second pages have different sizes."""
    if len(doc) < 2:
        return False
    return doc[0].rect != doc[1].rect

def split_pdf(input_pdf_path, add_initial_page_mode='add_if_needed', max_pages_per_split=MAX_PAGES_PER_SPLIT):
    """
    Splits the PDF into parts ensuring each split starts on an even page (human count), i.e. odd 0-based index,
    but keeps the first split starting on page 0 (cover).

    Parameters:
    - input_pdf_path: path to the original PDF
    - add_initial_page_mode: 'add_forcing', 'not_add' or 'add_if_needed' (default)
    - max_pages_per_split: max pages per split chunk (adjusted dynamically to keep splits starting on even pages)
    """
    if not os.path.isfile(input_pdf_path):
        print(f"Error: The file '{input_pdf_path}' does not exist.")
        return

    doc = fitz.open(input_pdf_path)
    ensure_output_dir()

    # Decide if add extra page at start of first split
    if add_initial_page_mode == 'add_forcing':
        insert_extra_page_first = True
    elif add_initial_page_mode == 'not_add':
        insert_extra_page_first = False
    else:  # add_if_needed
        insert_extra_page_first = needs_extra_page(doc)

    total_pages = len(doc)
    split_count = 0
    current_index = 0

    while current_index < total_pages:
        split = fitz.open()

        # Insert blank page at start of first split if needed
        if split_count == 0 and insert_extra_page_first:
            ref_page = doc[1] if total_pages > 1 else doc[0]
            blank_doc = create_blank_page_like(ref_page)
            split.insert_pdf(blank_doc)
            blank_doc.close()

        # For splits after the first, ensure starting index is odd (0-based) = even human page number
        if split_count > 0 and current_index % 2 == 0:
            print(f"Adjusting start index from {current_index} (even) to {current_index + 1} (odd)")
            current_index += 1
            if current_index >= total_pages:
                break

        to_page = min(current_index + max_pages_per_split - 1, total_pages - 1)
        next_start = to_page + 1

        # Adjust to_page so next split starts on odd index if not last page
        if next_start < total_pages and next_start % 2 == 0:
            if to_page + 1 < total_pages:
                to_page += 1

        split.insert_pdf(doc, from_page=current_index, to_page=to_page)

        split_count += 1
        output_path = os.path.join(OUTPUT_DIR, f"split{split_count:02}.pdf")
        split.save(output_path)
        split.close()

        print(f"Saved split {split_count}: pages {current_index + 1} to {to_page + 1} (1-based numbering)")

        current_index = to_page + 1

    doc.close()
    print(f"✅ PDF split into {split_count} parts.")

if __name__ == "__main__":
    if len(sys.argv) not in [2, 3]:
        print("Usage: python split_pdf.py <input_pdf> [add_initial_page_mode]")
        print("Optional add_initial_page_mode: 'add_forcing', 'not_add', 'add_if_needed'")
        sys.exit(1)

    input_path = sys.argv[1]

    if len(sys.argv) == 3:
        mode = sys.argv[2]
        if mode not in ['add_forcing', 'not_add', 'add_if_needed']:
            print(f"Invalid mode: {mode}")
            sys.exit(1)
    else:
        mode = 'add_if_needed'

    split_pdf(input_path, add_initial_page_mode=mode)

