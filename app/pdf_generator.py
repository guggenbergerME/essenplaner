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


def einkaufsliste_pdf(einkaufsliste_gruppiert, laeden):
    """Erzeugt ein SW-PDF der Einkaufsliste, nach Abteilungen sortiert."""
    pdf = SWPdf()
    pdf.title = "Einkaufsliste"
    pdf.add_page()

    # Geschaefte
    if laeden:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, f"Geschaefte: {', '.join(laeden)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    col_check = 8
    col_zutat = 120
    col_tage = 62

    for abteilung, zutaten in einkaufsliste_gruppiert:
        # Abteilungs-Header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(col_check + col_zutat + col_tage, 7, f"  {abteilung}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        # Zutaten
        pdf.set_font("Helvetica", "", 9)
        for i, (zutat, tage) in enumerate(zutaten):
            bg = 245 if i % 2 == 0 else 255
            pdf.set_fill_color(bg, bg, bg)
            pdf.cell(col_check, 6, "", border=1, fill=True)
            pdf.cell(col_zutat, 6, zutat, border=1, fill=True)
            pdf.cell(col_tage, 6, ", ".join(tage), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(1)

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


def wochenplan_pdf(plan, einkaufsliste_gruppiert, laeden, personen):
    """Erzeugt ein Komplett-PDF: Wochenplan mit allen Rezepten + Einkaufsliste."""
    pdf = SWPdf()
    pdf.title = "Wochenplan"
    pdf.add_page()

    # Uebersicht
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, f"Fuer {personen} Personen", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Wochenuebersicht als Tabelle
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(45, 7, "Tag", border=1, fill=True)
    pdf.cell(80, 7, "Rezept", border=1, fill=True)
    pdf.cell(30, 7, "Zeit", border=1, fill=True)
    pdf.cell(35, 7, "Max. Zeit", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    for i, eintrag in enumerate(plan):
        bg = 245 if i % 2 == 0 else 255
        pdf.set_fill_color(bg, bg, bg)
        name = eintrag["rezept"]["name"] if eintrag["rezept"] else "—"
        zeit = f"{eintrag['rezept']['zubereitungszeit']} Min." if eintrag["rezept"] else "—"
        pdf.cell(45, 6, eintrag["tag"], border=1, fill=True)
        pdf.cell(80, 6, name, border=1, fill=True)
        pdf.cell(30, 6, zeit, border=1, fill=True)
        pdf.cell(35, 6, f"max. {eintrag['max_zeit']} Min.", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    # Einzelne Rezepte
    for eintrag in plan:
        if not eintrag["rezept"]:
            continue
        r = eintrag["rezept"]

        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"{eintrag['tag']}: {r['name']}", new_x="LMARGIN", new_y="NEXT")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, f"Zubereitungszeit: {r['zubereitungszeit']} Min. | {r['portionen']} Personen", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Zutaten", new_x="LMARGIN", new_y="NEXT")
        pdf.line(10, pdf.get_y(), 100, pdf.get_y())
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 10)
        for zutat in r["zutaten"]:
            pdf.cell(5, 6, "")
            pdf.cell(0, 6, f"- {zutat}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Zubereitung", new_x="LMARGIN", new_y="NEXT")
        pdf.line(10, pdf.get_y(), 100, pdf.get_y())
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 10)
        for j, schritt in enumerate(r["zubereitung"], 1):
            pdf.cell(5, 6, "")
            pdf.multi_cell(0, 6, f"{j}. {schritt}", new_x="LMARGIN", new_y="NEXT")

    # Einkaufsliste
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Einkaufsliste", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    if laeden:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, f"Geschaefte: {', '.join(laeden)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    col_check = 8
    col_zutat = 120
    col_tage = 62

    for abteilung, zutaten in einkaufsliste_gruppiert:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(col_check + col_zutat + col_tage, 7, f"  {abteilung}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 9)
        for k, (zutat, tage) in enumerate(zutaten):
            bg = 245 if k % 2 == 0 else 255
            pdf.set_fill_color(bg, bg, bg)
            pdf.cell(col_check, 6, "", border=1, fill=True)
            pdf.cell(col_zutat, 6, zutat, border=1, fill=True)
            pdf.cell(col_tage, 6, ", ".join(tage), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(1)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.getvalue()
