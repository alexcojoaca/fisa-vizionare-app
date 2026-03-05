from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def utcnow():
    # Postgres + Railway: stocăm UTC (timezone-aware)
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('email', 'role', name='uq_user_email_role'),
    )

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)  # actualizat la login

    # Paid access (trial pe zile eliminat complet)
    paid_ends_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Ultima dată când a dat „OK” la notificarea de expirare paid (1 zi înainte)
    expiry_reminder_dismissed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Trial pe acțiuni pentru conturi neplătite (1x fiecare tip)
    # free_rental_viewing_used: True dacă a folosit deja accesul gratuit pentru fișă chirie
    free_rental_viewing_used = db.Column(db.Boolean, default=False, nullable=False)
    # free_sale_viewing_used: True dacă a folosit deja accesul gratuit pentru fișă vânzare
    free_sale_viewing_used = db.Column(db.Boolean, default=False, nullable=False)
    
    # Legacy field - păstrat pentru compatibilitate dar nu mai folosit în logică
    trial_ends_at = db.Column(db.DateTime(timezone=True), nullable=True)
    free_actions_remaining = db.Column(db.Integer, default=3, nullable=False)

    # blocare manuală (ban / disable)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Incrementat de admin la "Deconectează de pe alte dispozitive"; sesiunile cu version veche sunt invalidate
    session_version = db.Column(db.Integer, default=1, nullable=False)

    # User role: "agent" or "client"
    role = db.Column(db.String(20), nullable=False, default="agent", index=True)
    
    # Phone number (required for clients, optional for agents)
    phone = db.Column(db.String(32), nullable=True)
    
    @property
    def normalized_role(self):
        """Returns 'agent' or 'client' - defensive fallback for any NULL or invalid role values."""
        role_val = getattr(self, 'role', None)
        if not role_val or role_val not in ('agent', 'client'):
            return 'agent'  # Default to agent for backward compatibility
        return role_val
    
    @property
    def is_client(self):
        """Check if user is a client."""
        return self.normalized_role == 'client'
    
    @property
    def is_agent(self):
        """Check if user is an agent."""
        return self.normalized_role == 'agent'

    # relație 1-1: fiecare user are profilul lui de documente
    profile = db.relationship(
        "UserProfile",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # relație 1-N: device-urile contului (pt limită 2-3 device-uri)
    devices = db.relationship(
        "UserDevice",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # relație 1-N: fișe remote de chirie (link către client)
    chirie_remote_signings = db.relationship(
        "ChirieRemoteSigning",
        backref="owner_user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ✅ relație 1-N: fișe remote de vânzare (link către client)
    vanzare_remote_signings = db.relationship(
        "VanzareRemoteSigning",
        backref="owner_user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # relație 1-N: task-uri To-Do (private per user)
    tasks = db.relationship(
        "Task",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # relație 1-N: cereri marketplace (buyer requests)
    buyer_requests = db.relationship(
        "BuyerRequest",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Limita de oferte marketplace (null = default: 3 gratuit + offer_paid_slots)
    offer_quota_limit = db.Column(db.Integer, nullable=True)
    # Sloturi anunțuri plătite: +3 / +6 / +12, valabile 30 zile
    offer_paid_slots = db.Column(db.Integer, default=0, nullable=False)
    offer_paid_slots_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # Limita de cereri marketplace (null = default: 5 gratuit + request_paid_slots)
    request_quota_limit = db.Column(db.Integer, nullable=True)
    # Sloturi cereri plătite, valabile 30 zile
    request_paid_slots = db.Column(db.Integer, default=0, nullable=False)
    request_paid_slots_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # relație 1-N: oferte marketplace (seller offers)
    seller_offers = db.relationship(
        "SellerOffer",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # relație 1-N: anunțuri citite (pentru notificări admin)
    announcement_reads = db.relationship(
        "UserAnnouncementRead",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # --- password helpers ---
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # --- access helpers ---
    def access_until(self):
        """Data până la care are acces (doar paid, trial eliminat)."""
        return self.paid_ends_at if self.paid_ends_at is not None else None

    def has_access(self) -> bool:
        """
        Are acces dacă nu e blocat și:
        - Are paid activ SAU
        - Are acțiuni gratuite disponibile (free_rental_viewing_used sau free_sale_viewing_used false)
        """
        if not self.is_active:
            return False
        has_paid = bool(self.paid_ends_at and self.paid_ends_at > utcnow())
        has_free_actions = not self.free_rental_viewing_used or not self.free_sale_viewing_used
        return has_paid or has_free_actions

    def is_active_account(self) -> bool:
        """True dacă are paid activ (nu doar acțiuni gratuite)."""
        if not self.is_active:
            return False
        return bool(self.paid_ends_at and self.paid_ends_at > utcnow())

    def can_create_rental_viewing(self) -> bool:
        """True dacă poate crea fișă de vizionare chirie (paid activ SAU nu a folosit încă accesul gratuit)."""
        if self.is_active_account():
            return True
        return not self.free_rental_viewing_used

    def can_create_sale_viewing(self) -> bool:
        """True dacă poate crea fișă de vizionare vânzare (paid activ SAU nu a folosit încă accesul gratuit)."""
        if self.is_active_account():
            return True
        return not self.free_sale_viewing_used

    def mark_rental_viewing_used(self) -> None:
        """Marchează că a folosit accesul gratuit pentru fișă chirie."""
        if not self.is_active_account():
            self.free_rental_viewing_used = True

    def mark_sale_viewing_used(self) -> None:
        """Marchează că a folosit accesul gratuit pentru fișă vânzare."""
        if not self.is_active_account():
            self.free_sale_viewing_used = True

    def days_left(self) -> int:
        """Zile rămase (rotunjit în sus). 0 dacă nu are acces."""
        until = self.access_until()
        if not until:
            return 0
        delta = until - utcnow()
        if delta.total_seconds() <= 0:
            return 0
        return int((delta.total_seconds() + 86400 - 1) // 86400)

    def access_source(self) -> str:
        """Returnează: 'paid' / 'none' / 'blocked' (trial eliminat)"""
        if not self.is_active:
            return "blocked"

        now = utcnow()
        paid_ok = self.paid_ends_at is not None and self.paid_ends_at > now

        if paid_ok:
            return "paid"
        return "none"

    def support_whatsapp_text(self) -> str:
        """
        Text bun de pus în wa.me/?text=...
        (URL-encoding îl faci în Jinja / front-end)
        """
        source = self.access_source()
        left = self.days_left()
        until = self.access_until()
        until_str = until.strftime("%d.%m.%Y") if until else "-"

        if source == "blocked":
            status = "Cont blocat manual"
        elif source == "paid":
            status = f"Abonament activ ({left} zile) până la {until_str}"
        else:
            status = "Acces expirat"

        return (
            "Salut! Vreau activare/continuare abonament.\n"
            f"User ID: {self.id}\n"
            f"Email: {self.email}\n"
            f"Status: {status}\n"
        )


class DeviceTrial(db.Model):
    __tablename__ = "device_trial"

    id = db.Column(db.Integer, primary_key=True)

    # device_id pe care îl dă device_guard (cookie id stabil)
    device_id = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # de câte ori a primit trial device-ul ăsta
    trial_count = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class UserDevice(db.Model):
    __tablename__ = "user_device"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    device_id = db.Column(db.String(64), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=True)  # optional: "iPhone", "Laptop"
    last_seen_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "device_id", name="uq_user_device"),
    )


class UserProfile(db.Model):
    __tablename__ = "user_profile"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)

    # agent (date documente)
    agent_name = db.Column(db.String(120), default="__________", nullable=False)
    agent_phone = db.Column(db.String(20), default="", nullable=False)
    agent_signature_dataurl = db.Column(db.Text, default="", nullable=False)

    # agency (setări documente)
    agency_name = db.Column(db.String(160), default="__________ SRL", nullable=False)
    agency_hq_address = db.Column(db.String(255), default="__________", nullable=False)
    agency_orc_number = db.Column(db.String(80), default="__________", nullable=False)
    agency_cui = db.Column(db.String(80), default="__________", nullable=False)
    agency_iban = db.Column(db.String(80), default="__________", nullable=False)
    agency_bank = db.Column(db.String(120), default="__________", nullable=False)
    agency_administrator = db.Column(db.String(160), default="__________", nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ChirieRemoteSigning(db.Model):
    __tablename__ = "chirie_remote_signing"

    id = db.Column(db.Integer, primary_key=True)

    # agent owner (cine a generat link-ul)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    # link token public
    public_token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # status: pending / signed / expired
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    # meta timp
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    signed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # date vizionare + imobil (setate de agent)
    data_vizionarii = db.Column(db.String(20), nullable=False)   # "dd.mm.yyyy"
    ora_vizionarii = db.Column(db.String(10), nullable=False)    # "HH:MM"
    tip_imobil = db.Column(db.String(120), nullable=False)

    # IMPORTANT: adresa full doar în PDF, adresa_public în pagina client
    adresa_full = db.Column(db.String(255), nullable=False)
    adresa_public = db.Column(db.String(255), nullable=False)

    comision_procent = db.Column(db.String(50), nullable=False)

    # semnături
    signature_agent_dataurl = db.Column(db.Text, nullable=True)
    signature_visitor_dataurl = db.Column(db.Text, nullable=True)

    # date vizitator (completate de client)
    viz_nume = db.Column(db.String(160), nullable=True)
    viz_telefon = db.Column(db.String(50), nullable=True)
    viz_email = db.Column(db.String(160), nullable=True)

    # id pdf salvat în tmp (ex: "remote-<docid>")
    pdf_doc_id = db.Column(db.String(64), nullable=True)

    __table_args__ = (
        db.Index("ix_chirie_remote_user_status", "user_id", "status"),
    )


class VanzareRemoteSigning(db.Model):
    __tablename__ = "vanzare_remote_signing"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    public_token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    signed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    data_vizionarii = db.Column(db.String(20), nullable=False)
    ora_vizionarii = db.Column(db.String(10), nullable=False)
    tip_imobil = db.Column(db.String(120), nullable=False)

    adresa_full = db.Column(db.String(255), nullable=False)
    adresa_public = db.Column(db.String(255), nullable=False)

    comision_procent = db.Column(db.String(50), nullable=False)

    signature_agent_dataurl = db.Column(db.Text, nullable=True)
    signature_visitor_dataurl = db.Column(db.Text, nullable=True)

    viz_nume = db.Column(db.String(160), nullable=True)
    viz_telefon = db.Column(db.String(50), nullable=True)
    viz_email = db.Column(db.String(160), nullable=True)

    pdf_doc_id = db.Column(db.String(64), nullable=True)

    __table_args__ = (
        db.Index("ix_vanzare_remote_user_status", "user_id", "status"),
    )


class Task(db.Model):
    """To-Do task for agents. Private per user; auto-expire 30 days after completion."""
    __tablename__ = "task"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)   # optional
    due_time = db.Column(db.Time, nullable=True)   # optional

    priority = db.Column(db.String(20), nullable=False, default="medium")  # low, medium, high
    status = db.Column(db.String(20), nullable=False, default="open", index=True)  # open, in-progress, done
    tags = db.Column(db.String(255), nullable=True)  # comma-separated

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Token pentru completare prin link (notificări)
    completion_token = db.Column(db.String(64), unique=True, nullable=True, index=True)

    __table_args__ = (
        db.Index("ix_task_user_status", "user_id", "status"),
    )
    
    def generate_completion_token(self):
        """Generează un token unic pentru completare prin link."""
        import secrets
        if not self.completion_token:
            self.completion_token = secrets.token_urlsafe(32)
        return self.completion_token


# --- Marketplace: Zone, BuyerRequest, RequestZones ---


class Zone(db.Model):
    __tablename__ = "zone"

    id = db.Column(db.Integer, primary_key=True)
    group = db.Column(db.String(80), nullable=True)   # e.g. Sector 1, Ilfov
    subgroup = db.Column(db.String(80), nullable=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)


# many-to-many: buyer_request <-> zone
class RequestZones(db.Model):
    __tablename__ = "request_zones"

    request_id = db.Column(db.Integer, db.ForeignKey("buyer_request.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("zone.id"), nullable=False, primary_key=True)

    __table_args__ = (
        db.Index("ix_request_zones_zone_request", "zone_id", "request_id"),
    )


class BuyerRequest(db.Model):
    __tablename__ = "buyer_request"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    request_type = db.Column(db.String(20), nullable=False)   # cumparare | inchiriere
    property_type = db.Column(db.String(40), nullable=False)   # apartament | casa | teren
    budget_min = db.Column(db.Integer, nullable=True)
    budget_max = db.Column(db.Integer, nullable=True)
    rooms = db.Column(db.Integer, nullable=True)
    year_min = db.Column(db.Integer, nullable=True)
    year_max = db.Column(db.Integer, nullable=True)
    etaj = db.Column(db.String(120), nullable=True)  # comma-separated: Demisol,Parter,1,2,...,18
    description = db.Column(db.Text, nullable=True)
    urgent = db.Column(db.Boolean, default=False, nullable=False)
    plus_tva = db.Column(db.Boolean, default=False, nullable=False)
    collaboration_type = db.Column(db.String(40), nullable=True)   # none | with_agents | agents_zero_commission (PF only)
    commission_percent = db.Column(db.Integer, nullable=True)
    contact_phone = db.Column(db.String(32), nullable=True)   # optional; visibility by role/access
    posted_by_role = db.Column(db.String(20), nullable=True)   # 'agent' or 'client'
    # Vizibil doar pentru user_id: număr telefon al persoanei pentru care cauți (să știi cui îi cauți)
    client_phone_private = db.Column(db.String(32), nullable=True)
    
    # Client commission fields
    client_offers_commission = db.Column(db.Boolean, default=False, nullable=False)  # True if client offers commission
    client_commission_value = db.Column(db.String(100), nullable=True)  # Commission value (e.g., "3%" or "500 €")
    client_no_commission = db.Column(db.Boolean, default=False, nullable=False)  # True if client explicitly says no commission
    
    # View count for client requests
    view_count = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=utcnow, nullable=True)

    zones = db.relationship(
        "Zone",
        secondary="request_zones",
        backref=db.backref("requests", lazy="dynamic"),
        lazy="joined",
    )

    __table_args__ = (
        db.Index("ix_buyer_request_type_prop_urgent", "request_type", "property_type", "urgent"),
    )


# --- Marketplace Oferte: OfferZones, SellerOffer ---

class OfferZones(db.Model):
    __tablename__ = "offer_zones"

    offer_id = db.Column(db.Integer, db.ForeignKey("seller_offer.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("zone.id"), nullable=False, primary_key=True)

    __table_args__ = (
        db.Index("ix_offer_zones_zone_offer", "zone_id", "offer_id"),
    )


class SellerOffer(db.Model):
    """Anunț de la agent: tip (vânzare/închiriere), imobil, preț, suprafețe, etaj, an, parcare, comision, contact."""
    __tablename__ = "seller_offer"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    request_type = db.Column(db.String(20), nullable=True)   # cumparare | inchiriere
    property_type = db.Column(db.String(40), nullable=True)   # apartament | casa | teren | spatiu_comercial
    budget_min = db.Column(db.Integer, nullable=True)   # legacy / filter
    budget_max = db.Column(db.Integer, nullable=True)   # legacy / filter
    price = db.Column(db.Integer, nullable=True)       # preț unic al imobilului
    price_negotiable = db.Column(db.Boolean, default=False, nullable=False)  # preț negociabil da/nu
    plus_tva = db.Column(db.Boolean, default=False, nullable=False)  # preț/buget plus TVA
    rooms = db.Column(db.Integer, nullable=True)
    year_min = db.Column(db.Integer, nullable=True)
    year_max = db.Column(db.Integer, nullable=True)
    anul_constructiei = db.Column(db.Integer, nullable=True)
    surface_utila = db.Column(db.Float, nullable=True)
    surface_totala = db.Column(db.Float, nullable=True)
    surface_balcon = db.Column(db.Float, nullable=True)
    surface_terasa = db.Column(db.Float, nullable=True)
    surface_curte = db.Column(db.Float, nullable=True)
    etaj = db.Column(db.String(120), nullable=True)    # comma-separated: Demisol,1,2,...,30
    nr_etaje_cladire = db.Column(db.Integer, nullable=True)  # câte etaje are clădirea
    nr_locuri_parcare = db.Column(db.Integer, nullable=True)
    offers_commission = db.Column(db.Boolean, default=False, nullable=False)
    commission_value = db.Column(db.String(80), nullable=True)  # e.g. "3%" or "500 €"
    description = db.Column(db.Text, nullable=True)
    contact_phone = db.Column(db.String(32), nullable=True)
    title = db.Column(db.String(200), nullable=True)
    # Vizibil doar pentru user_id: numele proprietarului (să știi cui îi desemnezi anunțul)
    owner_name_private = db.Column(db.String(120), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=utcnow, nullable=True)

    zones = db.relationship(
        "Zone",
        secondary="offer_zones",
        backref=db.backref("offers", lazy="dynamic"),
        lazy="joined",
    )

    __table_args__ = (
        db.Index("ix_seller_offer_type_prop", "request_type", "property_type"),
    )


# --- Posibile colaborări: potrivire anunț <-> cerere ---

class PossibleCollaboration(db.Model):
    """Potrivire între un anunț (ofertă) și o cerere. Valabilă până se șterge anunțul sau cererea."""
    __tablename__ = "possible_collaboration"

    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(
        db.Integer,
        db.ForeignKey("seller_offer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_id = db.Column(
        db.Integer,
        db.ForeignKey("buyer_request.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    offer = db.relationship("SellerOffer", backref=db.backref("possible_collaborations", lazy="dynamic", cascade="all, delete-orphan"))
    request = db.relationship("BuyerRequest", backref=db.backref("possible_collaborations", lazy="dynamic", cascade="all, delete-orphan"))
    seen_records = db.relationship(
        "CollaborationSeen",
        backref="collaboration",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint("offer_id", "request_id", name="uq_possible_collaboration_offer_request"),
        db.Index("ix_possible_collaboration_created", "created_at"),
    )


class CollaborationSeen(db.Model):
    """Utilizatorul a deschis secțiunea Posibile colaborări și a văzut potrivirile. Pentru a ascunde notificarea „Ai o posibilă colaborare”."""
    __tablename__ = "collaboration_seen"

    id = db.Column(db.Integer, primary_key=True)
    collaboration_id = db.Column(
        db.Integer,
        db.ForeignKey("possible_collaboration.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    seen_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("collaboration_id", "user_id", name="uq_collaboration_seen_user"),
        db.Index("ix_collaboration_seen_user", "user_id"),
    )


class AssistantDailyUsage(db.Model):
    """Daily message count per user for assistant (Gemini rate limit)."""
    __tablename__ = "assistant_daily_usage"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    usage_date = db.Column(db.Date, nullable=False, index=True)
    message_count = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("user_id", "usage_date", name="uq_assistant_daily_user_date"),
        db.Index("ix_assistant_daily_user_date", "user_id", "usage_date"),
    )


class Announcement(db.Model):
    """Anunț trimis de admin către toți utilizatorii. Vizibil în asistent până la marcarea ca citit."""
    __tablename__ = "announcement"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
    )

    __table_args__ = (db.Index("ix_announcement_created_at", "created_at"),)


class UserAnnouncementRead(db.Model):
    """Utilizator X a citit anunțul Y. Unread = nu există înregistrare."""
    __tablename__ = "user_announcement_read"

    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    announcement_id = db.Column(
        db.Integer, db.ForeignKey("announcement.id", ondelete="CASCADE"), primary_key=True
    )
    read_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "announcement_id", name="uq_user_announcement_read"),)


# --- Echipă & Performanță ---


class Team(db.Model):
    """Echipă de agenți. O agenție = 1 echipă. Managerul creează echipa."""
    __tablename__ = "team"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    manager_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    manager = db.relationship("User", backref=db.backref("managed_teams", lazy="dynamic"), foreign_keys=[manager_user_id])
    members = db.relationship(
        "TeamMember",
        backref="team",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    tasks = db.relationship(
        "TeamTask",
        backref="team",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="TeamTask.created_at.desc()",
    )


class TeamMember(db.Model):
    """Membru al echipei: manager sau agent. Agentul trebuie să confirme invitația."""
    __tablename__ = "team_member"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default="agent")  # manager | agent
    status = db.Column(db.String(20), nullable=False, default="confirmed")  # pending | confirmed
    joined_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("team_memberships", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", name="uq_team_member_user"),
        db.Index("ix_team_member_status", "status"),
    )


class TeamTask(db.Model):
    """Task de echipă creat de manager."""
    __tablename__ = "team_task"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="medium")  # low, medium, high
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    created_by = db.relationship("User", backref=db.backref("created_team_tasks", lazy="dynamic"))
    assignments = db.relationship(
        "TeamTaskAssignment",
        backref="task",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class TeamTaskAssignment(db.Model):
    """Assignment per agent. Se creează automat la crearea task-ului."""
    __tablename__ = "team_task_assignment"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("team_task.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)  # open | done
    acknowledged_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    comment = db.Column(db.Text, nullable=True)  # ce a făcut agentul
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    assignee = db.relationship("User", backref=db.backref("team_task_assignments", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("task_id", "assignee_user_id", name="uq_team_task_assignment"),
        db.Index("ix_team_task_assignment_status", "status"),
    )


class DailyActivity(db.Model):
    """Raport zilnic de activitate al agentului."""
    __tablename__ = "daily_activity"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    viewings_count = db.Column(db.Integer, nullable=False, default=0)
    deals_closed_count = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=True)  # suma totală
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("daily_activities", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_daily_activity_user_date"),
        db.Index("ix_daily_activity_user_date", "user_id", "date"),
    )


class CleanupRun(db.Model):
    """Istoric rulări curățare: manual, auto, auto_failsafe."""
    __tablename__ = "cleanup_run"

    id = db.Column(db.Integer, primary_key=True)
    ran_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ran_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    mode = db.Column(db.String(20), nullable=False)  # manual | auto | auto_failsafe
    ok = db.Column(db.Boolean, nullable=False, default=True)
    details_json = db.Column(db.Text, nullable=True)  # JSON: counts per categorie + warnings
    error_text = db.Column(db.Text, nullable=True)

    __table_args__ = (db.Index("ix_cleanup_run_ran_at", "ran_at"),)
