# DIVERGENCE SPEC/CODE : la spec attend une erreur "Produit inconnu" ; le code laisse remonter
# le KeyError de get_product sans ce message. Le test vérifie le type d'erreur (KeyError ou ValueError)
# et ne peut pas vérifier le libellé exact.
# DIVERGENCE SPEC/CODE : pour un panier vide avec un coupon inconnu, quote() ne lève pas d'erreur
# (coupon_discount n'est appelé que si le panier contient des lignes). Ce cas n'est donc pas testé.

from decimal import Decimal

import pytest

from minishop.pricing import (
    coupon_discount,
    line_total,
    money,
    quote,
    shipping_cost,
)

pytestmark = [pytest.mark.generated, pytest.mark.unit]


@pytest.fixture(autouse=True)
def _sans_bug_arrondi(monkeypatch):
    """Garantit que le bug de démo d'arrondi n'est jamais actif pendant les tests."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)


# ---------------------------------------------------------------------------
# Scénarios de la spécification
# ---------------------------------------------------------------------------


def test_panier_vide():
    """Un panier vide a un total de 0 et aucuns frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Deux mugs donnent un sous-total de 25.00, avec 4.90 de livraison."""
    q = quote([{"product_id": "mug", "qty": 2}])
    assert q.subtotal == Decimal("25.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Un hoodie et un mug (56.50) bénéficient de la livraison offerte."""
    q = quote(
        [
            {"product_id": "hoodie", "qty": 1},
            {"product_id": "mug", "qty": 1},
        ]
    )
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("56.50")


def test_remise_volume_des_10_unites():
    """Dix stickers déclenchent la remise volume de 5 % et donnent 23.28."""
    q = quote([{"product_id": "sticker", "qty": 10}])
    assert q.subtotal == Decimal("23.28")


def test_coupon_de_bienvenue():
    """WELCOME10 applique 10 % sur deux mugs : remise 2.50, total 27.40."""
    q = quote([{"product_id": "mug", "qty": 2}], coupon="WELCOME10")
    assert q.discount == Decimal("2.50")
    assert q.total == Decimal("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """WELCOME10 n'applique aucune remise sous le seuil de 20 euros."""
    q = quote([{"product_id": "mug", "qty": 1}], coupon="WELCOME10")
    assert q.discount == Decimal("0.00")


def test_coupon_de_livraison_offerte():
    """FREESHIP offre la livraison sur un petit panier : total 2.45."""
    q = quote([{"product_id": "sticker", "qty": 1}], coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("2.45")


def test_coupon_inconnu():
    """Un coupon inconnu lève une erreur 'Coupon inconnu'."""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote([{"product_id": "mug", "qty": 1}], coupon="NOEL2026")


def test_produit_inconnu():
    """Un produit absent du catalogue lève une erreur."""
    # DIVERGENCE SPEC/CODE : le code lève KeyError (issu de catalog.get_product), sans le message "Produit inconnu".
    with pytest.raises((KeyError, ValueError)):
        quote([{"product_id": "licorne", "qty": 1}])


def test_coupon_fixed5_au_dessus_du_seuil_de_30_euros():
    """FIXED5 retire 5.00 sur un sous-total de 32.40 et donne un total de 32.30."""
    q = quote(
        [
            {"product_id": "tshirt", "qty": 1},
            {"product_id": "mug", "qty": 1},
        ],
        coupon="FIXED5",
    )
    assert q.subtotal == Decimal("32.40")
    assert q.discount == Decimal("5.00")
    assert q.total == Decimal("32.30")


def test_cumul_remise_volume_et_coupon_welcome10():
    """La remise volume et WELCOME10 se cumulent sur dix mugs : total 106.87."""
    q = quote([{"product_id": "mug", "qty": 10}], coupon="WELCOME10")
    assert q.subtotal == Decimal("118.75")
    assert q.discount == Decimal("11.88")
    assert q.total == Decimal("106.87")


def test_quantite_nulle_invalide():
    """Une quantité nulle lève l'erreur 'Quantité hors limites'."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote([{"product_id": "mug", "qty": 0}])


# ---------------------------------------------------------------------------
# Cas limites (non cités par la spécification)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("qty", [1, 99])
def test_limite_quantites_bornes_acceptees(qty):
    """Les quantités 1 et 99, bornes incluses, sont acceptées."""
    assert line_total(Decimal("1.00"), qty) >= Decimal("0.00")


@pytest.mark.parametrize("qty", [0, -1, 100, True, 2.0, "2"])
def test_limite_quantites_invalides_rejetees(qty):
    """Les quantités hors bornes, booléens, flottants et chaînes sont rejetés."""
    with pytest.raises(ValueError):
        line_total(Decimal("12.50"), qty)


def test_limite_quantite_99_arrondie_au_centime():
    """99 mugs à 12.50 avec remise volume donnent 1175.63 après arrondi half-up."""
    assert line_total(Decimal("12.50"), 99) == Decimal("1175.63")


@pytest.mark.parametrize(
    "qty, expected",
    [
        (9, Decimal("112.50")),  # sous le seuil : pas de remise
        (10, Decimal("118.75")),  # seuil atteint : remise de 5 %
    ],
)
def test_limite_seuil_remise_volume(qty, expected):
    """La remise volume s'applique exactement à partir de 10 unités."""
    assert line_total(Decimal("12.50"), qty) == expected


@pytest.mark.parametrize(
    "valeur, attendu",
    [
        ("0.124", Decimal("0.12")),
        ("0.125", Decimal("0.13")),
        ("2.675", Decimal("2.68")),
        (0.125, Decimal("0.13")),
        (Decimal("10"), Decimal("10.00")),
    ],
)
def test_limite_arrondi_half_up_au_centime(valeur, attendu):
    """L'arrondi se fait au centime en half-up."""
    assert money(valeur) == attendu


@pytest.mark.parametrize(
    "montant, attendu",
    [
        (Decimal("49.99"), Decimal("4.90")),
        (Decimal("50.00"), Decimal("0.00")),
        (Decimal("50.01"), Decimal("0.00")),
    ],
)
def test_limite_seuil_livraison_offerte_inclus(montant, attendu):
    """La livraison est offerte à partir de 50.00 inclus, et facturée en dessous."""
    assert shipping_cost(montant, None, empty=False) == attendu


def test_limite_livraison_offerte_exactement_50_euros():
    """Quatre mugs (50.00 pile) bénéficient de la livraison offerte."""
    q = quote([{"product_id": "mug", "qty": 4}])
    assert q.subtotal == Decimal("50.00")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("50.00")


def test_limite_livraison_facturee_sous_50_euros():
    """Trois mugs (37.50) paient la livraison de 4.90."""
    q = quote([{"product_id": "mug", "qty": 3}])
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("42.40")


def test_limite_welcome10_sous_seuil_20_euros():
    """Un t-shirt seul (19.90) est juste sous le seuil de WELCOME10 : pas de remise."""
    q = quote([{"product_id": "tshirt", "qty": 1}], coupon="WELCOME10")
    assert q.discount == Decimal("0.00")


def test_limite_welcome10_au_dessus_seuil_20_euros_arrondi():
    """Sous-total 22.35 : remise 2.235 arrondie à 2.24 et total 25.01."""
    q = quote(
        [
            {"product_id": "tshirt", "qty": 1},
            {"product_id": "sticker", "qty": 1},
        ],
        coupon="WELCOME10",
    )
    assert q.subtotal == Decimal("22.35")
    assert q.discount == Decimal("2.24")
    assert q.total == Decimal("25.01")


def test_limite_fixed5_sous_seuil_30_euros():
    """Un sous-total de 29.70 est juste sous le seuil de FIXED5 : pas de remise."""
    q = quote(
        [
            {"product_id": "tshirt", "qty": 1},
            {"product_id": "sticker", "qty": 4},
        ],
        coupon="FIXED5",
    )
    assert q.subtotal == Decimal("29.70")
    assert q.discount == Decimal("0.00")


@pytest.mark.parametrize(
    "saisie",
    ["welcome10", " WELCOME10 ", "Welcome10", "  welcome10\t"],
)
def test_limite_code_coupon_insensible_a_la_casse_et_aux_espaces(saisie):
    """Le code coupon est normalisé (casse et espaces) avant application."""
    q = quote([{"product_id": "mug", "qty": 2}], coupon=saisie)
    assert q.coupon == "WELCOME10"
    assert q.discount == Decimal("2.50")


@pytest.mark.parametrize("coupon", [None, ""])
def test_limite_coupon_vide_equivaut_a_absence(coupon):
    """Un coupon None ou vide n'applique aucune remise et n'est pas conservé."""
    q = quote([{"product_id": "mug", "qty": 2}], coupon=coupon)
    assert q.coupon is None
    assert q.discount == Decimal("0.00")
    assert q.total == Decimal("29.90")


def test_limite_student15_sans_minimum():
    """STUDENT15 s'applique sans minimum : 15 % d'un mug (1.875) arrondi à 1.88."""
    q = quote([{"product_id": "mug", "qty": 1}], coupon="STUDENT15")
    assert q.discount == Decimal("1.88")


def test_limite_student15_exclut_les_lignes_en_remise_volume():
    """STUDENT15 ignore les lignes de 10 unités et ne porte que sur le reste."""
    q = quote(
        [
            {"product_id": "mug", "qty": 10},
            {"product_id": "sticker", "qty": 1},
        ],
        coupon="STUDENT15",
    )
    # Seul le sticker (2.45) est éligible : 15 % = 0.3675 -> 0.37
    assert q.discount == Decimal("0.37")


def test_limite_student15_sans_lignes_eligibles():
    """STUDENT15 n'accorde rien si toutes les lignes ont la remise volume."""
    q = quote([{"product_id": "mug", "qty": 10}], coupon="STUDENT15")
    assert q.discount == Decimal("0.00")


def test_limite_coupon_direct_inconnu_leve_erreur():
    """coupon_discount rejette un code inconnu avec 'Coupon inconnu'."""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        coupon_discount(Decimal("50.00"), "NOPE")


@pytest.mark.parametrize("coupon", [None, ""])
def test_limite_coupon_discount_sans_coupon(coupon):
    """Sans coupon, coupon_discount retourne zéro."""
    assert coupon_discount(Decimal("50.00"), coupon) == Decimal("0.00")


def test_limite_panier_vide_avec_coupon_ne_remise_rien():
    """Un panier vide avec FIXED5 reste à zéro partout."""
    q = quote([], coupon="FIXED5")
    assert q.discount == Decimal("0.00")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("0.00")


def test_limite_freeship_sur_gros_panier_reste_gratuit():
    """FREESHIP sur un panier au-dessus de 50 euros garde la livraison à zéro."""
    q = quote([{"product_id": "hoodie", "qty": 2}], coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")


def test_limite_as_dict_expose_montants_en_chaine():
    """as_dict expose les montants sous forme de chaînes à deux décimales."""
    d = quote([{"product_id": "mug", "qty": 2}]).as_dict()
    assert d["subtotal"] == "25.00"
    assert d["total"] == "29.90"
    assert d["coupon"] is None
