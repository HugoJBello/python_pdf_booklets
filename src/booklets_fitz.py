import sys
import fitz  # PyMuPDF

def cm_to_pt(cm):
    return cm * 28.35

def get_content_bbox(page):
    """Calculate bounding box of visible content (text/images) on the page."""
    blocks = page.get_text("dict").get("blocks", [])
    rects = [fitz.Rect(b["bbox"]) for b in blocks if "bbox" in b]

    if not rects:
        return page.rect  # fallback to full page rect if no blocks found

    bbox = rects[0]
    for r in rects[1:]:
        bbox |= r

    margin = 5  # points margin around content
    bbox = bbox + (-margin, -margin, margin, margin)
    bbox = bbox & page.rect

    return bbox

def create_booklet(input_pdf_path, output_pdf_path, margin_cm=1.0):
    print(f"📄 Opening input PDF: {input_pdf_path}")
    doc = fitz.open(input_pdf_path)
    num_pages = doc.page_count
    print(f"ℹ️ Original number of pages: {num_pages}")

    pages_to_add = (4 - num_pages % 4) % 4
    if pages_to_add > 0:
        print(f"➕ Adding {pages_to_add} blank page(s) to make page count multiple of 4")
        for _ in range(pages_to_add):
            doc.insert_page(-1, width=doc[0].rect.width, height=doc[0].rect.height)
        num_pages = doc.page_count
        print(f"🔄 New page count: {num_pages}")

    margin = cm_to_pt(margin_cm)
    a4_width, a4_height = fitz.paper_size("a4")
    if a4_width < a4_height:
        a4_width, a4_height = a4_height, a4_width  # landscape

    print(f"📐 Output page size (A4 landscape): {a4_width:.2f} x {a4_height:.2f} pts")
    booklet_doc = fitz.open()

    pairs = []
    for i in range(num_pages // 4):
        left1 = num_pages - 1 - 2 * i
        right1 = 2 * i
        left2 = 2 * i + 1
        right2 = num_pages - 2 - 2 * i
        pairs.append((left1, right1))
        pairs.append((left2, right2))

    print(f"🔧 Processing {len(pairs)} booklet pages (each with two original pages)...")

    for idx, (left_idx, right_idx) in enumerate(pairs):
        left_page = doc.load_page(left_idx)
        right_page = doc.load_page(right_idx)

        new_page = booklet_doc.new_page(width=a4_width, height=a4_height)
        half_width = a4_width / 2
        avail_width = half_width - 2 * margin
        avail_height = a4_height - 2 * margin

        left_bbox = get_content_bbox(left_page)
        right_bbox = get_content_bbox(right_page)

        print(f"➡️ Booklet page {idx + 1}: left original page {left_idx}, right original page {right_idx}")
        print(f"   Left bbox: {left_bbox}")
        print(f"   Right bbox: {right_bbox}")

        def scale_factor(rect, avail_w, avail_h):
            scale = min(avail_w / rect.width, avail_h / rect.height)
            # Prevent upscaling: do not enlarge small content, only shrink large content
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

        if right_idx == 0:
            new_page.show_pdf_page(right_dest, doc, right_idx)
            print("   → Right page is cover: showing without clipping")
        else:
            if right_page.get_text().strip():
                new_page.show_pdf_page(right_dest, doc, right_idx, clip=right_bbox)
                print("   → Right page clipped to content bbox")

        if left_idx == 0:
            new_page.show_pdf_page(left_dest, doc, left_idx)
            print("   → Left page is cover: showing without clipping")
        else:
            if left_page.get_text().strip():
                new_page.show_pdf_page(left_dest, doc, left_idx, clip=left_bbox)
                print("   → Left page clipped to content bbox")

    print("🔄 Rotating every even booklet page 180 degrees for duplex printing...")
    for i, page in enumerate(booklet_doc):
        if i % 2 == 0:
            page.set_rotation(180)

    booklet_doc.save(output_pdf_path)
    print(f"✅ Booklet PDF saved successfully at: {output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python booklet_pymupdf.py input.pdf output.pdf")
        sys.exit(1)

    create_booklet(sys.argv[1], sys.argv[2])

