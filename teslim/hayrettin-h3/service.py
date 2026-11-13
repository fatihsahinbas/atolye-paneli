import io
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.modules.orders.models import Order
from app.domain.pricing import calculate_item_price

def get_order_or_404(db: Session, order_id: int, workshop_id: int) -> Order:
    """
    Siparişi ID ve atölye ID (tenant) bazlı sorgular. 
    Başka atölyeye ait siparişler veya bulunamayanlar için 404 döner.
    """
    order = db.query(Order).filter(Order.id == order_id, Order.workshop_id == workshop_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sipariş bulunamadı veya bu işlem için yetkiniz yok."
        )
    return order

def generate_order_offer_pdf(order: Order) -> bytes:
    """
    Teklif PDF'ini üretir: Atölye bilgisi, kalemler, malzeme/işçilik/KDV ayrıntıları,
    geçerlilik süresi ve altın ürünlerde has fiyatını içerir.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Başlık ve Atölye Bilgileri
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"TEKLIF / SIPARIS DETAYI #{order.id}")
    
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, f"Atölye ID: {order.workshop_id}")
    p.drawString(50, height - 85, f"Müşteri: {getattr(order, 'customer_name', 'Standart Müşteri')}")
    p.drawString(50, height - 100, f"Geçerlilik Süresi: {getattr(order, 'validity_period', '7 Gün')}")

    # Kalemler ve Detaylar
    y = height - 140
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Kalem Açıklaması")
    p.drawString(250, y, "Has Fiyatı")
    p.drawString(330, y, "Malzeme")
    p.drawString(400, y, "İşçilik")
    p.drawString(470, y, "Toplam")
    
    p.line(50, y - 5, 550, y - 5)
    y -= 25

    p.setFont("Helvetica", 9)
    items = getattr(order, "items", [])
    
    # Örnek dummy kalem verisi yoksa siparişin kendi alanlarından türetelim
    if not items and hasattr(order, "total_amount"):
        items = [{
            "description": f"Sipariş #{order.id} Ürün/Hizmet Bedeli",
            "is_gold": False,
            "malzeme_tutari": str(order.total_amount * Decimal("0.6")),
            "iscilik_tutari": str(order.total_amount * Decimal("0.4")),
            "kdv_orani": "0.20"
        }]

    for item in items:
        desc = item.get("description", "Özel Ürün")
        has_fiy = item.get("has_fiyati", "N/A")
        
        calc = calculate_item_price(item, Decimal(str(has_fiy)) if has_fiy != "N/A" else Decimal("0"))
        
        p.drawString(50, y, str(desc)[:30])
        p.drawString(250, y, str(calc["has_fiyati"]) if calc["has_fiyati"] else "-")
        p.drawString(330, y, f"{calc['malzeme_tutari']} TL")
        p.drawString(400, y, f"{calc['iscilik_tutari']} TL")
        p.drawString(470, y, f"{calc['toplam']} TL")
        
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return buffer.getvalue()