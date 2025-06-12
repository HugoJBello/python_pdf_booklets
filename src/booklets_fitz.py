import sys
import fitz  # PyMuPDF

def cm_to_pt(cm):
    return cm * 28.35

def get_content_bbox(page):
    blocks = page.get_text("dict").get("blocks", [])
    rects = [fitz.Rect(b["bbox"]) for b in blocks if "bbox" in b]

    if not rects:
        return page.rect

    bbox = rects[0]
    for r in rects[1:]:
        bbox |= r

    margin = 5
    bbox = bbox + (-margin, -margin, margin, margin)
    bbox = bbox & page.rect

    # 👇 Validamos que el bbox no sea absurdamente pequeño
    MIN_SIZE_THRESHOLD = 50  # en puntos (~1.7cm)
    if bbox.width < MIN_SIZE_THRESHOLD or bbox.height < MIN_SIZE_THRESHOLD:
        return page.rect  # usamos toda la página si el contenido es sospechosamente pequeño

    return bbox

def add_watermark_to_first_page(doc):
    """Añade un asterisco '*' en la esquina superior derecha de la primera página del documento."""
    if len(doc) == 0:
        return

    page = doc[0]
    text = "*"
    font_size = 20
    margin = 20
    text_width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
    x = page.rect.width - text_width - margin
    y = margin + font_size  # Ajustamos para que el texto quede dentro del margen superior
    page.insert_text((x, y), text, fontsize=font_size, fontname="helv", color=(0, 0, 0))

def create_booklet(input_pdf_path, output_pdf_path, margin_cm=1.0, add_watermark=False):
    print(f"📄 Opening input PDF: {input_pdf_path}")
    doc = fitz.open(input_pdf_path)
    num_pages = doc.page_count
    print(f"ℹ️ Original number of pages: {num_pages}")

    pages_to_add = (4 - num_pages % 4) % 4
    if pages_to_add > 0:
        print(f"➕ Adding {pages_to_add} blank page(s) to make total a multiple of 4")
        for _ in range(pages_to_add):
            doc.insert_page(-1, width=doc[0].rect.width, height=doc[0].rect.height)
        num_pages = doc.page_count
        print(f"🔄 New page count: {num_pages}")

    margin = cm_to_pt(margin_cm)
    a4_width, a4_height = fitz.paper_size("a4")
    if a4_width < a4_height:
        a4_width, a4_height = a4_height, a4_width

    print(f"📐 Output page size: {a4_width:.2f} x {a4_height:.2f} pts (A4 landscape)")
    booklet_doc = fitz.open()

    pairs = []
    for i in range(num_pages // 4):
        left1 = num_pages - 1 - 2 * i
        right1 = 2 * i
        left2 = 2 * i + 1
        right2 = num_pages - 2 - 2 * i
        pairs.append((left1, right1))
        pairs.append((left2, right2))

    print(f"🔧 Creating {len(pairs)} booklet pages (each with 2 original pages)...")

    for idx, (left_idx, right_idx) in enumerate(pairs):
        left_page = doc.load_page(left_idx)
        right_page = doc.load_page(right_idx)

        new_page = booklet_doc.new_page(width=a4_width, height=a4_height)
        half_width = a4_width / 2
        avail_width = half_width - 2 * margin
        avail_height = a4_height - 2 * margin

        left_bbox = get_content_bbox(left_page)
        right_bbox = get_content_bbox(right_page)

        def scale_factor(rect, max_w, max_h):
            scale = min(max_w / rect.width, max_h / rect.height)
            return min(scale, 1.0)

        left_scale = scale_factor(left_bbox, avail_width, avail_height)
        right_scale = scale_factor(right_bbox, avail_width, avail_height)

        left_w = left_bbox.width * left_scale
        left_h = left_bbox.height * left_scale
        left_x = margin + (half_width - 2 * margin - left_w) / 2
        left_y = margin + (avail_height - left_h) / 2
        left_dest = fitz.Rect(left_x, left_y, left_x + left_w, left_y + left_h)

        right_w = right_bbox.width * right_scale
        right_h = right_bbox.height * right_scale
        right_x = half_width + margin + (half_width - 2 * margin - right_w) / 2
        right_y = margin + (avail_height - right_h) / 2
        right_dest = fitz.Rect(right_x, right_y, right_x + right_w, right_y + right_h)

        rotate_degrees = 180 if idx % 2 == 0 else 0

        if rotate_degrees == 180:
            # Al rotar 180°, intercambia posiciones para que las páginas queden en orden correcto
            try:
                new_page.show_pdf_page(right_dest, doc, left_idx, clip=left_bbox, rotate=rotate_degrees)
            except Exception as e:
                print(f"   ❌ Error rendering left page {left_idx} (rotated): {e}")

            try:
                new_page.show_pdf_page(left_dest, doc, right_idx, clip=right_bbox, rotate=rotate_degrees)
            except Exception as e:
                print(f"   ❌ Error rendering right page {right_idx} (rotated): {e}")
        else:
            try:
                new_page.show_pdf_page(left_dest, doc, left_idx, clip=left_bbox, rotate=rotate_degrees)
            except Exception as e:
                print(f"   ❌ Error rendering left page {left_idx}: {e}")

            try:
                new_page.show_pdf_page(right_dest, doc, right_idx, clip=right_bbox, rotate=rotate_degrees)
            except Exception as e:
                print(f"   ❌ Error rendering right page {right_idx}: {e}")

    if add_watermark:
        add_watermark_to_first_page(booklet_doc)

    booklet_doc.save(output_pdf_path)
    print(f"✅ Booklet PDF saved: {output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python booklet_pymupdf.py input.pdf output.pdf")
        sys.exit(1)

    create_booklet(sys.argv[1], sys.argv[2], add_watermark=False)

