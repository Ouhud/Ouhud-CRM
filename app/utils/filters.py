# app/utils/filters.py

from typing import Union, Dict

# Professionelle Currency-Symbole für SaaS-CRM Systeme
CURRENCY_SYMBOLS: Dict[str, str] = {
    "EUR": "€",
    "USD": "$",
    "CHF": "CHF",
    "GBP": "£",

    # GCC Währungen
    "AED": "د.إ",     # UAE Dirham
    "SAR": "﷼",       # Saudi Riyal
    "QAR": "ر.ق",     # Qatar Riyal
    "OMR": "ر.ع",     # Oman Riyal
    "KWD": "د.ك",     # Kuwait Dinar
    "BHD": "ب.د",     # Bahrain Dinar

    # Weitere
    "TRY": "₺",
    "AUD": "A$",
    "CAD": "C$",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "JPY": "¥",
    "CNY": "¥",
}


def format_currency(value: Union[int, float, str], currency: str = "EUR") -> str:
    """
    Format a number into an international currency format.
    Always returns a *string*, so Jinja2 never crashes.

    Examples:
    - 1234.5 EUR → "1.234,50 €"
    - 599 AED → "599.00 د.إ"
    - 1500 SAR → "1,500.00 ﷼"
    """

    # 1) Zahl validieren
    try:
        number = float(value)
    except (ValueError, TypeError):
        return str(value)

    # 2) Währungssymbol wählen
    symbol = CURRENCY_SYMBOLS.get(currency.upper(), currency.upper())

    # 3) EU-Format (Tausenderpunkte & Dezimalkomma)
    formatted_number = f"{number:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    # 4) Rückgabe
    return f"{formatted_number} {symbol}"