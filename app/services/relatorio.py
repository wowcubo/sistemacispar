from io import BytesIO
from datetime import datetime
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from app.models.pendencia import Pendencia, StatusPendencia

COR_PRIMARIA = colors.HexColor("#1a56db")
COR_CRITICA = colors.HexColor("#e02424")
COR_MAIOR = colors.HexColor("#e3a008")
COR_MENOR = colors.HexColor("#057a55")

LABELS_STATUS = {
    "aberta": "Aberta",
    "em_andamento": "Em andamento",
    "aguardando_aprovacao": "Aguard. aprovação",
    "resolvida": "Resolvida",
    "cancelada": "Cancelada",
}

LABELS_CRIT = {
    "critica": "CRÍTICA",
    "maior": "MAIOR",
    "menor": "MENOR",
}


def _cor_criticidade(c: str) -> colors.Color:
    return {"critica": COR_CRITICA, "maior": COR_MAIOR, "menor": COR_MENOR}.get(c, colors.grey)


def gerar_pdf_pendencias(db: Session, setor: str | None = None, mes: str | None = None) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("Titulo", parent=styles["Heading1"], textColor=COR_PRIMARIA, fontSize=16)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], textColor=colors.grey, fontSize=9)
    item_style = ParagraphStyle("Item", parent=styles["Normal"], fontSize=9, leading=12)

    q = db.query(Pendencia)
    if setor:
        q = q.filter(Pendencia.setor == setor)
    if mes:
        try:
            ano, m = map(int, mes.split("-"))
            from datetime import date
            import calendar
            ultimo_dia = calendar.monthrange(ano, m)[1]
            q = q.filter(
                Pendencia.data_abertura >= date(ano, m, 1),
                Pendencia.data_abertura <= date(ano, m, ultimo_dia),
            )
        except ValueError:
            pass

    pendencias = q.order_by(Pendencia.criticidade, Pendencia.data_abertura).all()

    total = len(pendencias)
    resolvidas = sum(1 for p in pendencias if p.status == StatusPendencia.resolvida)

    story = []
    story.append(Paragraph("CISPAR — Relatório de Pendências SISBI", titulo_style))
    story.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"Setor: {setor or 'Todos'} | Período: {mes or 'Geral'}",
        sub_style,
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", color=COR_PRIMARIA))
    story.append(Spacer(1, 0.3 * cm))

    # Resumo
    resumo_data = [
        ["Total", "Resolvidas", "Em aberto", "Taxa resolução"],
        [str(total), str(resolvidas), str(total - resolvidas),
         f"{resolvidas / total * 100:.0f}%" if total else "—"],
    ]
    resumo_table = Table(resumo_data, colWidths=[4 * cm] * 4)
    resumo_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    story.append(resumo_table)
    story.append(Spacer(1, 0.5 * cm))

    # Listagem
    for p in pendencias:
        cor = _cor_criticidade(p.criticidade.value)
        story.append(Paragraph(
            f'<font color="#{cor.hexval()[2:]}"><b>[{LABELS_CRIT[p.criticidade.value]}]</b></font> '
            f'#{p.id} — {p.titulo}',
            item_style,
        ))
        story.append(Paragraph(
            f"Setor: {p.setor} | Status: {LABELS_STATUS[p.status.value]} | "
            f"Abertura: {p.data_abertura.strftime('%d/%m/%Y')} | "
            f"Limite: {p.data_limite.strftime('%d/%m/%Y') if p.data_limite else '—'}",
            sub_style,
        ))
        story.append(Paragraph(p.descricao, item_style))
        story.append(Spacer(1, 0.3 * cm))

    doc.build(story)
    return buf.getvalue()
