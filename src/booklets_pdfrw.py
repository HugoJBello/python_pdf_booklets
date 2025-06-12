import fitz
from pathlib import Path

def detect_content_bbox(page, margin_pts):
    blocks = page.get_text("blocks")
    if not blocks:
        # Página sin texto, devuelve toda la página
        return page.rect
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
        doc_in.insert_page(-1)  # añadir página en blanco al final
        total_pages += 1

    left_pages = list(range(total_pages - 1, total_pages // 2 - 1, -1))
    right_pages = list(range(0, total_pages // 2))

    for i, (left_idx, right_idx) in enumerate(zip(left_pages, right_pages), start=1):
        page_out = doc_out.new_page(width=out_width, height=out_height)

        page_left = doc_in[left_idx]
        page_right = doc_in[right_idx]

        bbox_left = detect_content_bbox(page_left, margin_pts)
        bbox_right = detect_content_bbox(page_right, margin_pts)

        col_width = (out_width - 3 * margin_out) / 2
        col_height = out_height - 2 * margin_out

        # Si la página salida es impar, rotamos ambas 180 grados
        rot_left = (page_left.rotation + 180) % 360 if i % 2 == 1 else page_left.rotation
        rot_right = (page_right.rotation + 180) % 360 if i % 2 == 1 else page_right.rotation

        def place_page(page_in, bbox, x_pos, y_pos, rotation):
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
                    rotate=rotation,
                )
            except ValueError:
                try:
                    page_out.show_pdf_page(
                        fitz.Rect(x_pos, y_pos, x_pos + col_width, y_pos + col_height),
                        doc_in,
                        page_in.number,
                        rotate=rotation,
                    )
                except ValueError:
                    # Página vacía: rellena con blanco
                    page_out.draw_rect(
                        fitz.Rect(x_pos, y_pos, x_pos + col_width, y_pos + col_height),
                        color=(1, 1, 1), fill=(1, 1, 1)
                    )

        # Intercambiamos posición derecha <-> izquierda
        place_page(page_right, bbox_right, margin_out, margin_out, rot_right)            # derecha a la izquierda
        place_page(page_left, bbox_left, margin_out * 2 + col_width, margin_out, rot_left)  # izquierda a la derecha

        if add_watermark:
            add_watermark_to_first_page(doc_out)


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

