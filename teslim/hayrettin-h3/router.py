from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_workshop_id  # Mevcut projendeki auth bağımlılığı
from app.modules.orders.service import get_order_or_404, generate_order_offer_pdf

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/{order_id}/pdf")
def download_order_pdf(
    order_id: int,
    db: Session = Depends(get_db),
    workshop_id: int = Depends(get_current_workshop_id)
):
    """
    Sipariş detayından teklif PDF'i indirir. Başka atölyenin siparişi ise 404 döner[cite: 1].
    """
    order = get_order_or_404(db, order_id, workshop_id)
    pdf_bytes = generate_order_offer_pdf(order)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=teklif_{order_id}.pdf"}
    )