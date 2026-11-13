from decimal import Decimal
from typing import Dict, Any, List

def calculate_item_price(item: Dict[str, Any], has_fiyati: Decimal = Decimal("0")) -> Dict[str, Any]:
    """
    Kalem bazlı fiyat hesaplama (Malzeme, İşçilik, KDV).
    Altın ürünlerde teklif anındaki has fiyatı baz alınır.
    """
    is_gold = item.get("is_gold", False)
    gram = Decimal(str(item.get("gram", "0")))
    iscilik_birim_fiyat = Decimal(str(item.get("iscilik_birim_fiyat", "0")))
    
    malzeme_tutari = (gram * has_fiyati) if is_gold else Decimal(str(item.get("malzeme_tutari", "0")))
    iscilik_tutari = gram * iscilik_birim_fiyat if is_gold else Decimal(str(item.get("iscilik_tutari", "0")))
    
    ara_toplam = malzeme_tutari + iscilik_tutari
    kdv_orani = Decimal(str(item.get("kdv_orani", "0.20")))
    kdv_tutari = ara_toplam * kdv_orani
    toplam = ara_toplam + kdv_tutari
    
    return {
        "malzeme_tutari": malzeme_tutari,
        "iscilik_tutari": iscilik_tutari,
        "ara_toplam": ara_toplam,
        "kdv_tutari": kdv_tutari,
        "toplam": toplam,
        "has_fiyati": has_fiyati if is_gold else None
    }