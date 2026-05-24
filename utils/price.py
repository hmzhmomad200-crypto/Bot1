import requests

def get_ltc_price_usd() -> float:
    """جلب سعر LTC الحالي بالدولار"""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd",
            timeout=10
        )
        return r.json()["litecoin"]["usd"]
    except Exception:
        return 80.0  # fallback لو فشل الاتصال

def usd_to_ltc(usd_amount: float) -> float:
    """تحويل دولار لـ LTC"""
    price = get_ltc_price_usd()
    return round(usd_amount / price, 8)

def ltc_to_usd(ltc_amount: float) -> float:
    """تحويل LTC لدولار"""
    price = get_ltc_price_usd()
    return round(ltc_amount * price, 2)
