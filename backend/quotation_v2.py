from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP


SYSTEM_CATEGORIES = (
    {"id": "equipment-cabinet", "order": 1, "name_zh": "设备柜体", "name_en": "Equipment Cabinet", "icon": "cabinet"},
    {"id": "central-control", "order": 2, "name_zh": "中控系统", "name_en": "Central Control System", "icon": "monitor"},
    {"id": "touch-control", "order": 3, "name_zh": "触控系统", "name_en": "Touch Control System", "icon": "panel"},
    {"id": "curtain", "order": 4, "name_zh": "遮阳系统", "name_en": "Shading System", "icon": "curtain"},
    {"id": "hvac", "order": 5, "name_zh": "暖通系统", "name_en": "HVAC System", "icon": "air"},
    {"id": "cable", "order": 6, "name_zh": "线材", "name_en": "Cabling", "icon": "cable"},
    {"id": "intercom", "order": 7, "name_zh": "可视对讲系统", "name_en": "Visual Intercom System", "icon": "intercom"},
    {"id": "network", "order": 8, "name_zh": "网络系统", "name_en": "Network System", "icon": "wifi"},
    {"id": "surveillance", "order": 9, "name_zh": "监控系统", "name_en": "Surveillance System", "icon": "camera"},
    {"id": "music", "order": 10, "name_zh": "背景音乐", "name_en": "Background Music", "icon": "headphones"},
    {"id": "lighting-control", "order": 11, "name_zh": "灯控", "name_en": "Lighting Control", "icon": "light"},
)
UNCATEGORIZED = {"id": "uncategorized", "order": 99, "name_zh": "未分类", "name_en": "Uncategorized", "icon": "other"}
SYSTEM_BY_ID = {item["id"]: item for item in (*SYSTEM_CATEGORIES, UNCATEGORIZED)}
SYSTEM_IDS = tuple(item["id"] for item in SYSTEM_CATEGORIES)


def canonical_system_category(value: object) -> str:
    clean = str(value or "").strip()
    return clean if clean in SYSTEM_BY_ID else "uncategorized"


def normalize_quotation_text(value: object, *, multiline: bool = False, limit: int = 1000) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("⽶", "米").replace("\u00a0", " ").replace("\u3000", " ")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    if multiline:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    else:
        text = re.sub(r"\s+", " ", text)
    return text.strip()[:limit]


def decimal_to_cents(value: object) -> int:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)


def service_amount(system: dict, subtotal_cents: int) -> int:
    service_type = system.get("service_type", "none")
    if service_type == "percentage":
        return round(subtotal_cents * int(system.get("service_rate_basis") or 0) / 10000)
    if service_type == "fixed":
        return max(0, int(system.get("service_amount_cents") or 0))
    return 0


def calculate_quotation(systems: list[dict], settings: dict, construction_fee_total_cents: int = 0) -> dict:
    base_total = 0
    for system in systems:
        subtotal = 0
        for item in system.get("items", []):
            item["item_total_cents"] = max(0, int(item.get("quantity") or 0)) * max(0, int(item.get("unit_price_cents") or 0)) if item.get("visible", 1) else 0
            subtotal += item["item_total_cents"]
        system["subtotal_cents"] = subtotal
        system["service_calculated_cents"] = service_amount(system, subtotal)
        system["total_cents"] = subtotal + system["service_calculated_cents"]
        base_total += system["total_cents"]

    discount_type = settings.get("discount_type", "none")
    discount_value = max(0, int(settings.get("discount_value") or 0))
    if discount_type == "percentage":
        discount_cents = round(base_total * discount_value / 10000)
    elif discount_type == "fixed":
        discount_cents = discount_value
    else:
        discount_cents = 0
    discount_cents = min(base_total, discount_cents)
    after_discount = base_total - discount_cents
    tax_cents = round(after_discount * max(0, int(settings.get("tax_rate_basis") or 0)) / 10000)
    construction_fee_total_cents = max(0, int(construction_fee_total_cents or 0))
    return {
        "systems_total_cents": base_total,
        "discount_cents": discount_cents,
        "tax_cents": tax_cents,
        "construction_fee_total_cents": construction_fee_total_cents,
        "grand_total_cents": after_discount + tax_cents + construction_fee_total_cents,
    }
