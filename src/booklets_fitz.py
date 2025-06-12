import sys
import fitz  # PyMuPDF

def cm_to_pt(cm):
    return cm * 28.35

def get_valid_bbox(page):
    try:
        blocks = page.get_text("dict").get("blocks", [])
        rects = [fitz.Rect(b["bbox"]) for b in blocks if "bbox" in b and b.get("type") == 0]
        if not rects:
            return None
        bbox = rects[0]
        for r in rects[1:]:
            bbox |= r
        bbox = bbox + (-5, -5, 5, 5)
        bbox = bbox & page.rect
        if bbox.width < 30 or bbox.height < 30:
            return None
        return bbox
    except Exception:
        return None

def add_watermark_to_first_page(doc):
    if len(doc) == 0:
        return
    page = doc[0]
    text = "*"
    font_size = 20
    margin = 20
    text_width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
    x = page.rect.width - text_width - margin
    y = margin + font_size
    page.insert_text((x, y), text, fontsize=font_size, fontname="helv", color=(0, 0, 0))

def create_booklet(input_pdf_path, output_pdf_path, margin_cm=1.0, add_watermark=False):
    print(f"📄 Opening input PDF: {input_pdf_path}")
    doc = fitz.open(input_pdf_path)
    num_pages = doc.page_count
    print(f"ℹ️ Original number of pages: {num_pages}")

    pages_to_add = (4 - num_pages % 4) % 4
    if pages_to_add > 0:
        print(f"➕ Adding {pages_to_add} blank page(s)")
        for _ in range(pages_to_add):
            doc.insert_page(-1, width=doc[0].rect.width, height=doc[0].rect.height)
        num_pages = doc.page_count

    margin = cm_to_pt(margin_cm)
    a4_width, a4_height = fitz.paper_size("a4")
    if a4_width < a4_height:
        a4_width, a4_height = a4_height, a4_width

    print(f"📐 Output size: {a4_width:.2f} x {a4_height:.2f} pts")
    booklet_doc = fitz.open()

    # Cálculo de pares de páginas para folleto
    pairs = []
    for i in range(num_pages // 4):
        left1 = num_pages - 1 - 2 * i
        right1 = 2 * i
        left2 = 2 * i + 1
        right2 = num_pages - 2 - 2 * i
        pairs.append((left1, right1))
        pairs.append((left2, right2))

    for idx, (left_idx, right_idx) in enumerate(pairs):
        left_page = doc.load_page(left_idx)
        right_page = doc.load_page(right_idx)

        new_page = booklet_doc.new_page(width=a4_width, height=a4_height)
        half_width = a4_width / 2
        avail_width = half_width - 2 * margin
        avail_height = a4_height - 2 * margin

        left_bbox = get_valid_bbox(left_page)
        right_bbox = get_valid_bbox(right_page)

        use_clip_left = left_bbox is not None
        use_clip_right = right_bbox is not None

        left_bbox = left_bbox or left_page.rect
        right_bbox = right_bbox or right_page.rect

        def compute_dest(bbox, is_left):
            scale = min(avail_width / bbox.width, avail_height / bbox.height, 1.0)
            scale = max(scale, 0.4)
            w = bbox.width * scale
            h = bbox.height * scale
            x_base = margin if is_left else half_width + margin
            x = x_base + (half_width - 2 * margin - w) / 2
            y = margin + (a4_height - 2 * margin - h) / 2
            return fitz.Rect(x, y, x + w, y + h)

        left_dest = compute_dest(left_bbox, is_left=True)
        right_dest = compute_dest(right_bbox, is_left=False)

        rotate = 180 if idx % 2 == 0 else 0

        def render(page_idx, dest, bbox, use_clip):
            try:
                if use_clip:
                    new_page.show_pdf_page(dest, doc, page_idx, clip=bbox, rotate=rotate)
                else:
                    new_page.show_pdf_page(dest, doc, page_idx, rotate=rotate)
            except Exception as e:
                print(f"❌ Failed to render page {page_idx}: {e}")

        if rotate == 180:
            render(left_idx, right_dest, left_bbox, use_clip_left)
            render(right_idx, left_dest, right_bbox, use_clip_right)
        else:
            render(left_idx, left_dest, left_bbox, use_clip_left)
            render(right_idx, right_dest, right_bbox, use_clip_right)

    if add_watermark:
        add_watermark_to_first_page(booklet_doc)

    booklet_doc.save(output_pdf_path)
    print(f"✅ Booklet saved: {output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python booklet.py input.pdf output.pdf")
        sys.exit(1)

    create_booklet(sys.argv[1], sys.argv[2])

