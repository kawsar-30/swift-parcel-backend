from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from app.models.parcel import Parcel

def generate_invoice_pdf(parcel: Parcel) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title = Paragraph("<b>SwiftParcel Invoice</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Parcel Info Table
    parcel_data = [
        ["Tracking ID", parcel.tracking_id],
        ["Sender", parcel.sender_name],
        ["Receiver", parcel.receiver_name],
        ["Delivery City", parcel.delivery_city],
        ["Weight", f"{parcel.weight_kg} kg"],
        ["Delivery Charge", f"{parcel.delivery_charge} BDT"],
        ["COD Amount", f"{parcel.cod_amount} BDT"],
        ["Total Amount", f"{parcel.total_amount} BDT"],
        ["Status", parcel.status],
    ]
    t = Table(parcel_data, colWidths=[150, 350])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Items Table
    if parcel.items:
        elements.append(Paragraph("<b>Items</b>", styles['Heading2']))
        items_data = [["Item Name", "Quantity", "Unit Price (BDT)"]]
        for item in parcel.items:
            items_data.append([item.item_name, str(item.quantity), f"{item.unit_price}"])
        
        t_items = Table(items_data, colWidths=[200, 100, 200])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t_items)

    doc.build(elements)
    buffer.seek(0)
    return buffer