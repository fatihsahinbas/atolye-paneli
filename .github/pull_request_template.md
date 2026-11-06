## Ne yaptım
<!-- 1–3 cümle. Trello kartının adını yaz. -->

Trello: 

## Nasıl test edilir
<!-- Fatih hoca bu adımları izleyerek denesin -->
1. 
2. 

## Ekran görüntüsü
<!-- Arayüz değiştiyse önce/sonra -->

## Kontrol listesi
- [ ] `ruff check .` ve `pytest -q` yerelde yeşil
- [ ] Yeni davranış için test yazdım
- [ ] Tenant tablosuna erişen her sorgu `scoped()` / `get_owned()` kullanıyor
- [ ] Durum değiştiren her formda `csrf_token` var
- [ ] Kullanıcı girdisi Pydantic ile doğrulanıyor
- [ ] Para hesabı `Decimal` (float yok)
- [ ] Model değiştiyse migration ekledim (`alembic revision --autogenerate`)
- [ ] Kodda, testte, log'da şifre / API anahtarı / telefon yok
