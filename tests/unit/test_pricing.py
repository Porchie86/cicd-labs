"""Tests unitaires des règles de prix (Atelier 1)."""

from decimal import Decimal

import pytest

from minishop.pricing import coupon_discount, line_total, money, quote, shipping_cost

pytestmark = pytest.mark.unit


# --- Tests de base ---

def test_money_arrondi_commercial():
    """0.125 s'arrondit à 0.13 (ROUND_HALF_UP), pas 0.12."""
    assert money("0.125") == Decimal("0.13")


def test_line_total_sans_remise():
    assert line_total(Decimal("12.50"), 2) == Decimal("25.00")


def test_quote_panier_vide():
    """Un panier vide coûte 0 € : pas de frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


# --- Quantités invalides & remise volume ---

@pytest.mark.parametrize("qty", [0, -1, 100, "2", True])
def test_quantite_invalide(qty):
    with pytest.raises(ValueError):
        line_total(Decimal("10.00"), qty)


@pytest.mark.parametrize(
    ("qty", "expected"),
    [
        (9, Decimal("90.00")),    # 9 unités : pas de remise volume
        (10, Decimal("95.00")),   # 10 unités : -5 %
        (11, Decimal("104.50")),  # 11 unités : -5 %
    ],
)
def test_remise_volume_limites(qty, expected):
    assert line_total(Decimal("10.00"), qty) == expected


# --- Coupons & valeurs limites ---

@pytest.mark.parametrize(
    ("subtotal", "coupon", "expected_discount"),
    [
        (Decimal("19.99"), "WELCOME10", Decimal("0.00")),   # Juste sous 20 €
        (Decimal("20.00"), "WELCOME10", Decimal("2.00")),   # Seuil exact 20 €
        (Decimal("25.55"), " welcome10 ", Decimal("2.56")), # Casse/espaces + arrondi
        (Decimal("29.99"), "FIXED5", Decimal("0.00")),      # Juste sous 30 €
        (Decimal("30.00"), "FIXED5", Decimal("5.00")),      # Seuil exact 30 €
        (Decimal("40.00"), "FREESHIP", Decimal("0.00")),    # FREESHIP ne réduit pas le sous-total
        (Decimal("40.00"), None, Decimal("0.00")),
    ],
)
def test_coupon_discount_seuils_et_casse(subtotal, coupon, expected_discount):
    assert coupon_discount(subtotal, coupon) == expected_discount


def test_coupon_inconnu_leve_value_error():
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote([{"product_id": "mug", "qty": 1}], coupon="PROMO99")


# --- Livraison & valeurs limites ---

@pytest.mark.parametrize(
    ("amount_after_discount", "coupon", "empty", "expected_shipping"),
    [
        (Decimal("0.00"), None, True, Decimal("0.00")),
        (Decimal("49.99"), None, False, Decimal("4.90")),       # Juste sous 50 €
        (Decimal("50.00"), None, False, Decimal("0.00")),       # Seuil exact 50 €
        (Decimal("12.50"), "FREESHIP", False, Decimal("0.00")), # Coupon livraison offerte
    ],
)
def test_shipping_cost_limites(amount_after_discount, coupon, empty, expected_shipping):
    assert shipping_cost(amount_after_discount, coupon, empty) == expected_shipping


def test_livraison_calculee_apres_remise_coupon():
    """Un panier à 50.00 € qui passe à 45.00 € après WELCOME10 doit payer la livraison."""
    # 4 mugs à 12.50 € = 50.00 € -> -10 % = 45.00 € (< 50 €) + 4.90 € livraison = 49.90 €
    q = quote([{"product_id": "mug", "qty": 4}], coupon="WELCOME10")
    assert q.subtotal == Decimal("50.00")
    assert q.discount == Decimal("5.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("49.90")


# --- Devis complet, catalogue & sérialisation ---

def test_produit_inconnu_leve_key_error():
    with pytest.raises(KeyError):
        quote([{"product_id": "produit_inexistant", "qty": 1}])


def test_quote_as_dict():
    q = quote([{"product_id": "mug", "qty": 1}], coupon="FREESHIP")
    data = q.as_dict()
    assert data["coupon"] == "FREESHIP"
    assert data["subtotal"] == "12.50"
    assert data["shipping"] == "0.00"
    assert data["total"] == "12.50"
    assert len(data["lines"]) == 1


# --- Cycle TDD : Coupon STUDENT15 (3 tests en ROUGE avant implémentation) ---

def test_student15_sans_minimum_et_sans_remise_volume():
    """STUDENT15 : -15 % sur le sous-total sans montant minimum."""
    # 1 mug à 12.50 € -> 15 % = 1.875 -> 1.88 €
    q = quote([{"product_id": "mug", "qty": 1}], coupon="STUDENT15")
    assert q.subtotal == Decimal("12.50")
    assert q.discount == Decimal("1.88")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("15.52")


def test_student15_non_cumulable_panier_mixte():
    """STUDENT15 ne s'applique qu'aux lignes sans remise volume (< 10 unités)."""
    # Ligne 1 : 10 stickers à 2.45 € = 24.50 € * 0.95 = 23.275 -> 23.28 € (remise volume -> exclu)
    # Ligne 2 : 1 mug à 12.50 € (pas de remise volume -> éligible à -15 % = 1.88 €)
    q = quote(
        [
            {"product_id": "sticker", "qty": 10},
            {"product_id": "mug", "qty": 1},
        ],
        coupon="STUDENT15",
    )
    assert q.subtotal == Decimal("35.78")
    assert q.discount == Decimal("1.88")


def test_student15_panier_uniquement_remise_volume():
    """Si toutes les lignes ont la remise volume, STUDENT15 donne 0.00 € de remise."""
    q = quote([{"product_id": "sticker", "qty": 10}], coupon="STUDENT15")
    assert q.discount == Decimal("0.00")
