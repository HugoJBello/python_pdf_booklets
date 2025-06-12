import fitz
from pathlib import Path

def detect_content_bbox(page, margin_pts):
    blocks = page.get_text("blocks")
    if not blocks:
        return None  # Página vacía
    x0 = min(b[0] for b in blocks)
    y0 = min(b[1] for b in blocks)
    x1 = max(b[2] for b in blocks)
    y1 = max(b[3] for b in blocks)
    bbox = fitz.Rect(x0, y0, x1, y1)

    clip_rect = fitz.Rect(
        max(bbox.x0 - margin_pts, 0),
        max(bbox.y0 - margin_pts, 0),
        min(bbox.x1 + margin_pts, page.rect.width),
        min(bbox.y1 + margin_pts, page.rect.height),
    )

    if clip_rect.is_empty or clip_rect.width <= 0 or clip_rect.height <= 0:
        return page.rect
    return clip_rect

def create_booklet(input_pdf_path: str, output_pdf_path: str, margin_cm=0.5, add_watermark=False):
    margin_pts = margin_cm * 72 / 2.54  # convertir cm a puntos
    doc_in = fitz.open(input_pdf_path)
    doc_out = fitz.open()

    # A4 horizontal (landscape)
    out_width = 842  # ancho A4 pts (horizontal)
    out_height = 595  # alto A4 pts (horizontal)
    margin_out = margin_pts

    total_pages = doc_in.page_count
    while total_pages % 4 != 0:
        doc_in.insert_page(-1)  # añadir página en blanco
        total_pages += 1

    left_pages = list(range(total_pages - 1, total_pages // 2 - 1, -1))
    right_pages = list(range(0, total_pages // 2))

    for left_idx, right_idx in zip(left_pages, right_pages):
        page_out = doc_out.new_page(width=out_width, height=out_height)

        page_left = doc_in[left_idx]
        page_right = doc_in[right_idx]

        bbox_left = detect_content_bbox(page_left, margin_pts)
        bbox_right = detect_content_bbox(page_right, margin_pts)

        col_width = (out_width - 3 * margin_out) / 2
        col_height = out_height - 2 * margin_out

        def place_page(page_in, bbox, x_pos, y_pos):
            if bbox is None:
                # Página vacía: pinta blanco
                page_out.draw_rect(
                    fitz.Rect(x_pos, y_pos, x_pos + col_width, y_pos + col_height),
                    color=(1,1,1), fill=(1,1,1)
                )
                return

            scale = min(col_width / bbox.width, col_height / bbox.height)
            w_scaled = bbox.width * scale
            h_scaled = bbox.height * scale
            x_draw = x_pos + (col_width - w_scaled) / 2
            y_draw = y_pos + (col_height - h_scaled) / 2

            try:
                page_out.show_pdf_page(
                    fitz.Rect(x_draw, y_draw, x_draw + w_scaled, y_draw + h_scaled),
                    doc_in,
                    page_in.number,
                    clip=bbox if bbox != page_in.rect else None,
                    rotate=page_in.rotation,
                )
            except ValueError:
                try:
                    page_out.show_pdf_page(
                        fitz.Rect(x_draw, y_draw, x_draw + col_width, y_draw + col_height),
                        doc_in,
                        page_in.number,
                        rotate=page_in.rotation,
                    )
                except ValueError:
                    page_out.draw_rect(
                        fitz.Rect(x_pos, y_pos, x_pos + col_width, y_pos + col_height),
                        color=(1,1,1), fill=(1,1,1)
                    )

        place_page(page_left, bbox_left, margin_out, margin_out)
        place_page(page_right, bbox_right, margin_out * 2 + col_width, margin_out)

        if add_watermark:
            # Aquí se podría añadir marca de agua si se desea
            pass

    doc_out.save(output_pdf_path)
    doc_out.close()
    doc_in.close()

def main():
    input_pdf = "input.pdf"
    output_pdf = "booklet_output.pdf"
    margin_cm = 0.5

    print("Creando folleto PDF en A4 horizontal...")
    create_booklet(input_pdf, output_pdf, margin_cm=margin_cm, add_watermark=True)
    print("Folleto generado en:", output_pdf)

if __name__ == "__main__":
    main()

