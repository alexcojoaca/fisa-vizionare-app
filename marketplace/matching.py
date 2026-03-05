# marketplace/matching.py – potrivire anunț <-> cerere (posibile colaborări)
"""
Reguli:
- Zonă: anunțul trebuie să aibă cel puțin o zonă comună cu cererea (sau invers).
- Tip: cumparare/inchiriere și tip imobil (apartament, casă, etc.) trebuie să coincidă.
- Buget închiriere: preț anunț în [buget_min - 100, buget_max + 100] euro.
- Buget vânzare: preț anunț se încadrează cu toleranță ±10% din prețul anunțului (buget_min - 10%, buget_max + 10%).
- Camere: dacă cererea are camere, anunțul trebuie să aibă același număr sau mai multe.
"""
from extensions import db
from models import (
    BuyerRequest,
    SellerOffer,
    PossibleCollaboration,
    RequestZones,
    OfferZones,
)

# Toleranțe buget
BUDGET_RENT_TOLERANCE_EUR = 100
# Vânzare: ±10% din prețul anunțului (nu mai e sumă fixă)
BUDGET_SALE_TOLERANCE_PERCENT = 0.10


def _offer_zone_ids(offer):
    """Set de zone_id pentru ofertă."""
    if not offer or not offer.id:
        return set()
    rows = OfferZones.query.filter_by(offer_id=offer.id).all()
    return {r.zone_id for r in rows}


def _request_zone_ids(request):
    """Set de zone_id pentru cerere."""
    if not request or not request.id:
        return set()
    rows = RequestZones.query.filter_by(request_id=request.id).all()
    return {r.zone_id for r in rows}


def _zones_overlap(offer, request):
    """True dacă oferta și cererea au cel puțin o zonă comună."""
    oz = _offer_zone_ids(offer)
    rz = _request_zone_ids(request)
    return bool(oz & rz)


def _offer_price(offer):
    """Prețul ofertei (price sau budget_max/budget_min)."""
    if offer.price is not None:
        return offer.price
    if offer.budget_max is not None:
        return offer.budget_max
    return offer.budget_min


def _budget_match_rent(offer_price, req_min, req_max):
    """Închiriere: preț în [req_min - 100, req_max + 100]."""
    if offer_price is None:
        return False
    low = (req_min - BUDGET_RENT_TOLERANCE_EUR) if req_min is not None else (offer_price - BUDGET_RENT_TOLERANCE_EUR)
    high = (req_max + BUDGET_RENT_TOLERANCE_EUR) if req_max is not None else (offer_price + BUDGET_RENT_TOLERANCE_EUR)
    if req_min is not None and req_max is None:
        return offer_price >= low
    if req_min is None and req_max is not None:
        return offer_price <= high
    if req_min is None and req_max is None:
        return True
    return low <= offer_price <= high


def _budget_match_sale(offer_price, req_min, req_max):
    """
    Vânzare: prețul anunțului se încadrează în bugetul cererii cu toleranță ±10% din prețul anunțului.
    Echivalent: req_min - 10%*offer <= offer <= req_max + 10%*offer
    => offer >= req_min/1.1  și  offer <= req_max/0.9 (când ambele sunt setate).
    """
    if offer_price is None or offer_price <= 0:
        return False
    tolerance = offer_price * BUDGET_SALE_TOLERANCE_PERCENT  # 10% din prețul anunțului
    if req_min is not None and req_max is None:
        return offer_price >= (req_min - tolerance)
    if req_min is None and req_max is not None:
        return offer_price <= (req_max + tolerance)
    if req_min is None and req_max is None:
        return True
    return (req_min - tolerance) <= offer_price <= (req_max + tolerance)


def _rooms_match(offer, request):
    """Dacă cererea specifică camere, oferta trebuie să aibă același număr sau mai multe."""
    req_rooms = getattr(request, "rooms", None)
    if req_rooms is None:
        return True
    offer_rooms = getattr(offer, "rooms", None)
    if offer_rooms is None:
        return True
    return offer_rooms >= req_rooms


def _property_type_match(offer, request):
    """Tip imobil identic (apartament, casă, teren, birou, etc.)."""
    op = (offer.property_type or "").strip()
    rp = (request.property_type or "").strip()
    if not op or not rp:
        return False
    return op == rp


def offer_matches_request(offer, request):
    """Verifică dacă oferta se potrivește cu cererea (zone, tip, buget, camere)."""
    if not offer or not request:
        return False
    if offer.request_type != request.request_type:
        return False
    if not _property_type_match(offer, request):
        return False
    if not _zones_overlap(offer, request):
        return False
    if not _rooms_match(offer, request):
        return False
    price = _offer_price(offer)
    if request.request_type == "inchiriere":
        if not _budget_match_rent(price, request.budget_min, request.budget_max):
            return False
    else:
        if not _budget_match_sale(price, request.budget_min, request.budget_max):
            return False
    return True


def request_matches_offer(request, offer):
    """Același criteriu: cererea se potrivește cu oferta."""
    return offer_matches_request(offer, request)


def find_matching_requests_for_offer(offer):
    """Returnează lista de cereri (alte useri, active) care se potrivesc cu oferta. Include și cererile clienților."""
    if not offer or not offer.id:
        return []
    # Exclude cererile utilizatorului care a postat oferta
    # Include cererile de la agenți și de la clienți
    q = (
        BuyerRequest.query.filter(BuyerRequest.user_id != offer.user_id)
        .filter(BuyerRequest.request_type == (offer.request_type or ""))
        .filter(BuyerRequest.property_type == (offer.property_type or ""))
    )
    candidates = q.all()
    return [r for r in candidates if offer_matches_request(offer, r)]


def find_matching_offers_for_request(request):
    """Returnează lista de oferte (alte useri, active) care se potrivesc cu cererea."""
    if not request or not request.id:
        return []
    q = (
        SellerOffer.query.filter(SellerOffer.user_id != request.user_id)
        .filter(SellerOffer.request_type == request.request_type)
        .filter(SellerOffer.property_type == request.property_type)
    )
    candidates = q.all()
    return [o for o in candidates if request_matches_offer(request, o)]


def run_matching_for_new_offer(offer_id):
    """
    După ce s-a creat/actualizat un anunț: recalculează potrivirile pentru acest anunț
    (șterge cele vechi, adaugă doar pe cele care încă se potrivesc). Valabil până se șterge anunțul.
    """
    offer = SellerOffer.query.get(offer_id)
    if not offer:
        return 0
    # Șterge toate potrivirile existente pentru acest anunț (la editare pot dispărea cereri din zonă/buget)
    PossibleCollaboration.query.filter_by(offer_id=offer_id).delete(synchronize_session=False)
    requests = find_matching_requests_for_offer(offer)
    for req in requests:
        pc = PossibleCollaboration(offer_id=offer.id, request_id=req.id)
        db.session.add(pc)
    db.session.commit()
    return len(requests)


def run_matching_for_new_request(request_id):
    """
    După ce s-a creat/actualizat o cerere: recalculează potrivirile pentru această cerere
    (șterge cele vechi, adaugă doar pe cele care încă se potrivesc).
    """
    request = BuyerRequest.query.get(request_id)
    if not request:
        return 0
    PossibleCollaboration.query.filter_by(request_id=request_id).delete(synchronize_session=False)
    offers = find_matching_offers_for_request(request)
    for offer in offers:
        pc = PossibleCollaboration(offer_id=offer.id, request_id=request.id)
        db.session.add(pc)
    db.session.commit()
    return len(offers)
