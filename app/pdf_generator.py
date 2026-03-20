"""PDF-Generierung fuer Einkaufsliste und Rezepte (Schwarz-Weiss)."""

import io
from fpdf import FPDF


class SWPdf(FPDF):
    """Schwarz-Weiss PDF mit einheitlichem Styling."""

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, self.title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"essenplaner | Seite {self.page_no()}", align="C")


def einkaufsliste_pdf(einkaufsliste, laeden):
    """Erzeugt ein SW-PDF der Einkaufsliste."""
    pdf = SWPdf()
    pdf.title = "Einkaufsliste"
    pdf.add_page()

    # Geschaefte
    if laeden:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, f"Geschaefte: {', '.join(laeden)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # Tabelle
    pdf.set_font("Helvetica", "B", 10)
    col_check = 8
    col_zutat = 120
    col_tage = 62

    pdf.cell(col_check, 7, "", border=1)
    pdf.cell(col_zutat, 7, "Zutat", border=1)
    pdf.cell(col_tage, 7, "Fuer", border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    for i, (zutat, tage) in enumerate(einkaufsliste):
        bg = 240 if i % 2 == 0 else 255
        pdf.set_fill_color(bg, bg, bg)
        pdf.cell(col_check, 6, "", border=1, fill=True)
        pdf.cell(col_zutat, 6, zutat, border=1, fill=True)
        pdf.cell(col_tage, 6, ", ".join(tage), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.getvalue()


def rezept_pdf(rezept):
    """Erzeugt ein SW-PDF eines einzelnen Rezepts."""
    pdf = SWPdf()
    pdf.title = rezept["name"]
    pdf.add_page()

    # Meta-Infos
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, f"Zubereitungszeit: {rezept['zubereitungszeit']} Min. | Portionen: {rezept['portionen']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Zutaten
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Zutaten", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    for zutat in rezept["zutaten"]:
        pdf.cell(5, 6, "")
        pdf.cell(0, 6, f"- {zutat}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    # Zubereitung
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Zubereitung", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    for i, schritt in enumerate(rezept["zubereitung"], 1):
        pdf.cell(5, 6, "")
        pdf.multi_cell(0, 6, f"{i}. {schritt}", new_x="LMARGIN", new_y="NEXT")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.getvalue()
