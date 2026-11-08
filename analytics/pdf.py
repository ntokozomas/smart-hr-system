PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 40
TEXT = (0.20, 0.23, 0.27)
MUTED = (0.42, 0.45, 0.50)
BLUE = (0.18, 0.45, 0.79)
BLUE_LIGHT = (0.91, 0.94, 0.98)
LINE = (0.87, 0.89, 0.91)


def _escape(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_width(value, size):
    return len(str(value)) * size * 0.52


def fit(value, width, size):
    value = str(value)
    if text_width(value, size) <= width:
        return value
    limit = max(int(width / (size * 0.52)) - 1, 1)
    return value[:limit] + "..."


class PdfDocument:
    def __init__(self, title):
        self.title = title
        self.pages = []
        self.add_page()

    def add_page(self):
        self.ops = []
        self.pages.append(self.ops)
        self.y = PAGE_HEIGHT - MARGIN

    def ensure_space(self, height):
        if self.y - height < MARGIN + 20:
            self.add_page()

    def text(self, x, y, value, size=10, bold=False, color=TEXT):
        font = "F2" if bold else "F1"
        red, green, blue = color
        self.ops.append(
            f"BT /{font} {size} Tf {red:.3f} {green:.3f} {blue:.3f} rg "
            f"{x:.2f} {y:.2f} Td ({_escape(value)}) Tj ET"
        )

    def rect(self, x, y, width, height, color):
        red, green, blue = color
        self.ops.append(
            f"{red:.3f} {green:.3f} {blue:.3f} rg {x:.2f} {y:.2f} {width:.2f} {height:.2f} re f"
        )

    def line(self, x1, y1, x2, y2, color=LINE, width=0.6):
        red, green, blue = color
        self.ops.append(
            f"{red:.3f} {green:.3f} {blue:.3f} RG {width:.2f} w "
            f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
        )

    def heading(self, value, size=13):
        self.ensure_space(size + 30)
        self.y -= size + 6
        self.text(MARGIN, self.y, value, size=size, bold=True, color=BLUE)
        self.y -= 8

    def paragraph(self, value, size=10, color=TEXT):
        self.ensure_space(size + 6)
        self.y -= size + 4
        self.text(MARGIN, self.y, fit(value, PAGE_WIDTH - 2 * MARGIN, size), size=size, color=color)

    def spacer(self, height=10):
        self.y -= height

    def table(self, headers, rows, size=8.5):
        usable = PAGE_WIDTH - 2 * MARGIN
        natural = []
        for index, header in enumerate(headers):
            longest_word = max(text_width(word, size) for word in str(header).split())
            longest_cell = max((text_width(row[index], size) for row in rows), default=0)
            natural.append(max(longest_word, longest_cell) + 12)
        spare = max(usable - sum(natural), 0)
        widths = [width + spare * width / sum(natural) for width in natural]
        scale = min(1, usable / sum(widths))
        widths = [width * scale for width in widths]
        line_height = size + 3
        row_height = size + 9

        def wrap(value, width):
            lines, current = [], ""
            for word in str(value).split():
                candidate = f"{current} {word}".strip()
                if current and text_width(candidate, size) > width:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            lines.append(current)
            return lines

        def place(x, index, value, baseline, bold):
            cell = fit(value, widths[index] - 8, size)
            if index == 0:
                self.text(x + 4, baseline, cell, size=size, bold=bold)
            else:
                right = x + widths[index] - 4
                self.text(right - text_width(cell, size), baseline, cell, size=size, bold=bold)

        def draw_header():
            wrapped = [wrap(header, widths[index] - 8) for index, header in enumerate(headers)]
            line_count = max(len(lines) for lines in wrapped)
            height = row_height + (line_count - 1) * line_height
            self.ensure_space(height + row_height)
            top = self.y
            self.rect(MARGIN, top - height, usable, height, BLUE_LIGHT)
            x = MARGIN
            for index, lines in enumerate(wrapped):
                for number, value in enumerate(lines):
                    baseline = top - height + 6 + (len(lines) - 1 - number) * line_height
                    place(x, index, value, baseline, True)
                x += widths[index]
            self.y = top - height
            self.line(MARGIN, self.y, MARGIN + usable, self.y)

        def draw_row(values):
            top = self.y
            x = MARGIN
            baseline = top - row_height + 6
            for index, value in enumerate(values):
                place(x, index, value, baseline, values[0] == "Total")
                x += widths[index]
            self.y = top - row_height
            self.line(MARGIN, self.y, MARGIN + usable, self.y)

        draw_header()
        for values in rows:
            if self.y - row_height < MARGIN + 20:
                self.add_page()
                draw_header()
            draw_row(values)

    def build(self):
        page_count = len(self.pages)
        objects = [
            "<< /Type /Catalog /Pages 2 0 R >>",
            None,
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            "/Encoding /WinAnsiEncoding >>",
        ]
        page_ids = []
        for number, ops in enumerate(self.pages, start=1):
            footer = (
                f"BT /F1 8 Tf {MUTED[0]:.3f} {MUTED[1]:.3f} {MUTED[2]:.3f} rg "
                f"{MARGIN} 22 Td ({_escape(self.title)} - page {number} of {page_count}) Tj ET"
            )
            stream = "\n".join(ops + [footer]).encode("cp1252", "replace")
            objects.append(
                f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
            )
            content_id = len(objects)
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
            )
            page_ids.append(len(objects))
        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>"

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for index, body in enumerate(objects, start=1):
            offsets.append(len(output))
            if isinstance(body, str):
                body = body.encode("latin-1")
            output += f"{index} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"
        xref_at = len(output)
        output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
        for offset in offsets:
            output += f"{offset:010d} 00000 n \n".encode("latin-1")
        output += (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
        ).encode("latin-1")
        return bytes(output)


def report_pdf(title, details, tables):
    document = PdfDocument(title)
    document.text(MARGIN, document.y - 18, title, size=18, bold=True, color=BLUE)
    document.y -= 26
    for label, value in details:
        document.paragraph(f"{label}: {value}", size=9.5, color=MUTED)
    document.spacer(6)
    for heading, headers, rows in tables:
        document.heading(heading)
        if rows:
            document.table(headers, rows)
        else:
            document.paragraph("No records for this period.", color=MUTED)
        document.spacer(12)
    return document.build()
