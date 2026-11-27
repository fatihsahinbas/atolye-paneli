"""Atölyeyi pilot yapar (ödeme ekranı görmez, ücretsiz). Yalnızca Fatih çalıştırır.

Kullanım:  python -m scripts.make_pilot <slug> [--geri-al]
"""
import sys

from sqlalchemy import select

from app import models  # noqa: F401
from app.core.config import get_settings
from app.core.db import build_engine, build_sessionmaker
from app.modules.workshop.models import Workshop


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    slug, undo = argv[0], "--geri-al" in argv
    db = build_sessionmaker(build_engine(get_settings().database_url))()
    ws = db.scalar(select(Workshop).where(Workshop.slug == slug))
    if ws is None:
        print(f"Atölye bulunamadı: {slug}")
        return 1
    ws.is_pilot = not undo
    ws.plan_code = None if undo else "PILOT"
    db.commit()
    print(f"{ws.name} ({slug}) → pilot={'evet' if ws.is_pilot else 'hayır'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
