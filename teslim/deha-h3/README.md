# AtolyeNotifier

Atölye sipariş durum değişikliklerinde müşteriye SMS veya e-posta gönderen,
başarısız gönderimleri tekrar denemeye izin veren mini servis.

## Kurulum
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload