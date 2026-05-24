import requests

def get_ltc_price_usd() -> float:
    """جلب سعر LTC الحالي بالدولار من LitePay"""
    try:
        r = requests.get(
            "https://litepay.ch/api/fiat_rates",
            timeout=10
        )
        return float(r.json()["LTC"]["USD"])
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
