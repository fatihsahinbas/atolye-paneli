"""Ürün görselleri: yükle, kapak seç, sil.  Sahip: Alper (H3 PROJE 7)"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import csrf_protect, require_owner
from app.core.templating import render
from app.core.tenancy import get_owned
from app.modules.auth.models import User
from app.modules.catalog.models import Product
from app.modules.media.models import Media
from app.modules.media.service import UploadError, delete_files, save_image

router = APIRouter(tags=["gallery"])

MAX_PER_PRODUCT = 8


def product_images(db: Session, product: Product) -> list[Media]:
    return db.scalars(
        select(Media)
        .where(Media.product_id == product.id, Media.workshop_id == product.workshop_id)
        .order_by(Media.is_cover.desc(), Media.id)
    ).all()


def _set_cover(db: Session, m: Media) -> None:
    """Üründe tek kapak: diğerleri False, bu True (aynı transaction)."""
    db.execute(
        update(Media)
        .where(Media.product_id == m.product_id, Media.workshop_id == m.workshop_id, Media.id != m.id)
        .values(is_cover=False)
    )
    m.is_cover = True


@router.post("/urunler/{product_id}/gorsel", dependencies=[Depends(csrf_protect)])
async def upload_product_images(
    request: Request,
    product_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_owner),
):
    product = get_owned(db, Product, product_id, user)
    s = request.app.state.settings
    existing = product_images(db, product)
    if len(existing) + len(files) > MAX_PER_PRODUCT:
        return render(request, "errors/message.html", {
            "message": f"Bir üründe en fazla {MAX_PER_PRODUCT} görsel olabilir",
            "back": f"/urunler/{product.id}/duzenle"}, 400)
    added = []
    for f in files:
        try:
            name, ctype, size = await save_image(f, s.media_root, s.max_upload_bytes)
        except UploadError as e:
            db.rollback()
            for m in added:  # yarım kalan yüklemenin dosyaları diskte kalmasın
                delete_files(s.media_root, m.stored_name)
            return render(request, "errors/message.html",
                          {"message": str(e), "back": f"/urunler/{product.id}/duzenle"}, 400)
        m = Media(workshop_id=user.workshop_id, product_id=product.id, stored_name=name,
                  content_type=ctype, size_bytes=size, is_public=True)
        db.add(m)
        added.append(m)
    db.flush()
    if not any(m.is_cover for m in existing) and added:
        _set_cover(db, added[0])  # ilk görsel otomatik kapak
    db.commit()
    return RedirectResponse(f"/urunler/{product.id}/duzenle", status_code=303)


@router.post("/gorsel/{media_id}/kapak", dependencies=[Depends(csrf_protect)])
def make_cover(media_id: int, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    m = get_owned(db, Media, media_id, user)
    if m.product_id is None:
        raise HTTPException(404)
    _set_cover(db, m)
    db.commit()
    return RedirectResponse(f"/urunler/{m.product_id}/duzenle", status_code=303)


@router.post("/gorsel/{media_id}/sil", dependencies=[Depends(csrf_protect)])
def delete_image(request: Request, media_id: int, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    m = get_owned(db, Media, media_id, user)
    if m.product_id is None:  # sipariş fotoğrafları bu uçtan silinmez
        raise HTTPException(404)
    product_id, stored, was_cover = m.product_id, m.stored_name, m.is_cover
    db.delete(m)
    db.commit()  # önce DB, sonra dosyalar
    delete_files(request.app.state.settings.media_root, stored)
    if was_cover and product_id:
        nxt = db.scalar(select(Media).where(Media.product_id == product_id).order_by(Media.id))
        if nxt:
            _set_cover(db, nxt)
            db.commit()
    back = f"/urunler/{product_id}/duzenle" if product_id else "/urunler"
    return RedirectResponse(back, status_code=303)
