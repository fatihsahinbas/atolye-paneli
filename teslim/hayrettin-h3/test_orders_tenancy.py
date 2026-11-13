from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.modules.orders.models import Order

client = TestClient(app)

def test_download_order_pdf_success(db_session: Session, normal_user_token_headers, test_order):
    """
    Kendi atölyesine ait siparişin teklif PDF'ini başarıyla indirebilmeli.
    """
    response = client.get(f"/orders/{test_order.id}/pdf", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

def test_download_other_workshop_order_returns_404(client: TestClient, normal_user_token_headers, another_workshop_order):
    """
    Başka bir atölyeye ait siparişin PDF'ine erişilmek istendiğinde 404 dönmeli (Tenant Güvenliği)[cite: 1].
    """
    response = client.get(f"/orders/{another_workshop_order.id}/pdf", headers=normal_user_token_headers)
    assert response.status_code == 404