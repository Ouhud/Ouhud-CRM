# app/models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Enum,
    Boolean,
    ForeignKey,
    Numeric,
    Float,
    Text,
    func
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum
from datetime import datetime

from sqlalchemy import Table



# app/models.py
from datetime import  timedelta
import uuid


import enum
from sqlalchemy.types import Enum as SqlEnum

# ─────────────────────────────
# 🧭 Benutzerrollen (Enum)
# ─────────────────────────────

class UserRole(str, enum.Enum):
    admin = "admin"            # volle Rechte
    mitarbeiter = "mitarbeiter"  # Standard Mitarbeiterzugriff
    kunde = "kunde"            # externer Kunde (eingeschränkter Zugriff)

# ─────────────────────────────
# 📝 Verlauf & Aktivitäten (ActivityLog)
# ─────────────────────────────

class ActivityLog(Base):
    """
    CRM-Aktivitätsprotokoll:
    Speichert Benutzeraktionen, Systemereignisse und Interaktionen, 
    um einen klaren Verlauf zu gewährleisten (z. B. Leads erstellt, Rechnungen verschickt, Logins, etc.)
    """
    __tablename__ = "activity_logs"

    # 🆔 Primärschlüssel
    id = Column(Integer, primary_key=True, index=True)

    # 👤 Verweis auf Benutzer (optional, z. B. Systemaktionen haben keinen User)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 🧭 Kategorie für einfache Filterung (Lead, Customer, Invoice, Auth, System, etc.)
    category = Column(String(50), nullable=True)

    # 📝 Kurze Beschreibung der Aktion
    action = Column(String(255), nullable=False)

    # 🧾 Detailliertere Infos, z. B. E-Mail, Kundennummer, Rechnungsbetrag etc.
    details = Column(Text, nullable=True)

    # ⏱ Zeitstempel (automatisch)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # 🔁 Beziehung zurück zum Benutzer
    user = relationship("User", back_populates="logs")   # ✅ korrigiert

    def __repr__(self):
        return f"<ActivityLog(id={self.id}, category='{self.category}', action='{self.action}', timestamp={self.timestamp})>"
    
    
    
# ─────────────────────────────
# 👥 Kunden
# ─────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_number = Column(String(20), unique=True, nullable=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False, unique=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)

    # 📄 Beziehungen
    invoices = relationship("Invoice", back_populates="customer", cascade="all, delete")
    orders = relationship("OrderDB", back_populates="customer", cascade="all, delete")

    # 📥 Inbox-Nachrichten (z. B. Kontaktformular, Support)
    messages = relationship("Message", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.name} ({self.email})>"
    
    
# ─────────────────────────────
# 🧾 Rechnungen & Mahnwesen (Invoice / InvoiceItem)
# ─────────────────────────────

class InvoiceStatus(str, enum.Enum):
    """Status einer Rechnung (z. B. für Dashboard & Erinnerungen)."""
    draft = "draft"           # Entwurf – noch nicht versendet
    sent = "sent"             # An Kunden gesendet
    paid = "paid"             # Bezahlt
    cancelled = "cancelled"   # Storniert
    overdue = "overdue"       # Überfällig (nach Fälligkeitsdatum)
    reminder = "reminder"     # Mahnung aktiv


class Invoice(Base):
    """Rechnungen mit Mahnstufen, Zahlungen und Positionen."""
    __tablename__ = "invoices"

    # 🆔 Primärschlüssel
    id = Column(Integer, primary_key=True, index=True)

    # 👥 Beziehung zum Kunden
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # 📄 Rechnungsdaten
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.00)

    # 📬 Mahnwesen
    reminder_level = Column(Integer, default=0)         # 0 = keine Mahnung, 1 = 1. Mahnung, etc.
    last_reminder_date = Column(Date, nullable=True)    # Datum der letzten Mahnung

    # 🔗 Beziehungen
    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Invoice #{self.invoice_number} Betrag={self.total_amount} Status={self.status}>"


class InvoiceItem(Base):
    """Rechnungspositionen (z. B. Produkte oder Dienstleistungen)."""
    __tablename__ = "invoice_items"

    # 🆔 Primärschlüssel
    id = Column(Integer, primary_key=True, index=True)

    # 📄 Zugehörige Rechnung
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    # 📝 Positionsdaten
    description = Column(String(255), nullable=False)
    quantity: int = Column(Integer, nullable=False, default=1)
    unit_price: float = Column(Float, nullable=False, default=0.0)
    tax_rate: float = Column(Float, nullable=False, default=0.0)

    # 🔗 Beziehung zurück zur Rechnung
    invoice = relationship("Invoice", back_populates="items")

    def __repr__(self):
        return f"<InvoiceItem {self.description} x{self.quantity} @ {self.unit_price}€>"
    
    
# ─────────────────────────────
# 🏢 Firmeneinstellungen
# ─────────────────────────────

class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255))
    address = Column(String(255))
    city = Column(String(100))
    country = Column(String(100))
    email = Column(String(100))
    phone = Column(String(50))
    iban = Column(String(50))
    bic = Column(String(50))
    vat_number = Column(String(50))
    logo_path = Column(String(255))

    enable_sepa = Column(Boolean, default=True)
    enable_twint = Column(Boolean, default=False)
    enable_online_payment = Column(Boolean, default=True)

    legal_notice = Column(Text, nullable=True)
    currency_code = Column(String(3), default="EUR")


# ─────────────────────────────
# 💳 Zahlungseingänge / CAMT Import Log
# ─────────────────────────────

class PaymentLog(Base):
    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    booking_date = Column(Date, nullable=False)
    message = Column(String(255), nullable=True)

    invoice = relationship("Invoice")

# ─────────────────────────────
# 🛍️ Produkte
# ─────────────────────────────

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    price = Column(Float, nullable=False)
    active = Column(Boolean, default=True)


# ─────────────────────────────
# 🛍 Bestellungen (Orders)
# ─────────────────────────────

class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="offen")  # offen, bezahlt, storniert, versendet ...
    total_amount = Column(Float, nullable=False)

    # Beziehungen
    customer = relationship("Customer", back_populates="orders")
    
# ─────────────────────────────
# 🚀 Leads & Opportunities
# ─────────────────────────────

class LeadStatus(str, enum.Enum):
    neu = "Neu"
    kontaktiert = "Kontaktiert"
    angeboten = "Angebot gesendet"
    gewonnen = "Gewonnen"
    verloren = "Verloren"

class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(100), nullable=True)
    status = Column(Enum(LeadStatus), default=LeadStatus.neu, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔥 KI Score Felder
    score = Column(Integer, default=0)
    score_label = Column(String(50), default="Cold")
    score_reason = Column(Text, nullable=True)

    # 🔥 KI Dashboard Felder
    conversion_chance = Column(Integer, default=0)   # 0–100 %
    ai_notes = Column(Text, nullable=True)           # freie KI-Analyse
    
    
# ─────────────────────────────
# 📝 Kalender-Events
# ─────────────────────────────
class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    
    
    
# 📌 Zahlungsstatus als Enum
class PaymentStatus(str, enum.Enum):
    received = "received"         # Zahlung erhalten
    refunded = "refunded"         # Erstattung
    pending = "pending"           # offen
    partial = "partial"           # Teilzahlung
    

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    method = Column(String(50), nullable=False)   # z.B. "Banküberweisung", "Kreditkarte", "Bar"
    status = Column(Enum(PaymentStatus), default=PaymentStatus.received)
    note = Column(String(255), nullable=True)

    # 🔗 Beziehung zur Rechnung
    invoice = relationship("Invoice", back_populates="payments")
    
    
    
# ─────────────────────────────
# 📥 Inbox / Nachrichtenmodell
# ─────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_name = Column(String(100), nullable=False)
    sender_email = Column(String(120), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    # 👤 optional Verknüpfung zu Kunde
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer = relationship("Customer", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.subject} from {self.sender_email}>"
    
    
    
    
    # 📝 Interner Chat
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String(100), nullable=False)
    message = Column(String(1000), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, sender='{self.sender}', timestamp='{self.timestamp}')>"


# 📲 WhatsApp Nachrichten
class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True, index=True)
    from_number = Column(String(50), nullable=False)       # Absendernummer
    to_number = Column(String(50), nullable=False)         # Empfängernummer (eigene Businessnummer)
    message = Column(String(1000), nullable=False)         # Textinhalt
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<WhatsAppMessage(id={self.id}, from='{self.from_number}', to='{self.to_number}', time='{self.timestamp}')>"


# ⚙️ WhatsApp Business Account Einstellungen
class WhatsAppSettings(Base):
    __tablename__ = "whatsapp_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)  # oder user_id, falls mandantenfähig
    phone_number = Column(String(50), nullable=False)
    phone_number_id = Column(String(100), nullable=False)
    business_id = Column(String(100), nullable=False)
    access_token = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<WhatsAppSettings(id={self.id}, phone='{self.phone_number}')>"
    
    
    
# ✅ Deine CallLog-Klasse (bleibt unverändert)
class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    direction = Column(String(10), nullable=False)         # inbound / outbound
    phone_number = Column(String(50), nullable=False)      # angerufene oder anrufende Nummer
    contact_name = Column(String(100), nullable=True)      # falls bekannt
    timestamp = Column(DateTime, default=datetime.utcnow)  # Zeitstempel
    duration = Column(Integer, nullable=True)              # Dauer in Sekunden
    status = Column(String(20), default="completed")       # completed / missed / rejected

    def __repr__(self):
        return (
            f"<CallLog(id={self.id}, number='{self.phone_number}', "
            f"dir='{self.direction}', time='{self.timestamp}')>"
        )


# ✅ Neue Tabelle für Telefonanlage/PBX-Einstellungen
class PBXSettings(Base):
    __tablename__ = "pbx_settings"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)             # z.B. 'twilio', 'fritzbox', 'placetel', 'custom'
    api_url = Column(String(255), nullable=False)             # Basis-URL oder SIP-Server
    api_key = Column(String(255), nullable=True)              # Optionaler API-Key
    sip_user = Column(String(100), nullable=True)             # SIP Benutzername
    sip_password = Column(String(100), nullable=True)         # SIP Passwort
    created_at = Column(DateTime, default=datetime.utcnow)    # Zeitstempel

    def __repr__(self):
        return f"<PBXSettings(provider='{self.provider}', url='{self.api_url}')>"
    
    
    
    
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(100), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog(user='{self.user}', action='{self.action}')>"
    
    
    
# ─────────────────────────────
# 📢 Marketing-Kampagnen
# ─────────────────────────────
# 🔸 Enum-Klasse für Status
class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"  # optional

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SqlEnum(CampaignStatus), default=CampaignStatus.draft)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    
# ─────────────────────────────
# 🧭 Zielgruppen-Segmente
# ─────────────────────────────
class Segment(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Segment(id={self.id}, name='{self.name}')>"
    
    
    # ─────────────────────────────
# 📄 Formulare (z. B. Website-Kontakt, Kampagnen, Leads)
# ─────────────────────────────
class Form(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)          # z. B. "Kontaktformular Webseite"
    description = Column(Text, nullable=True)
    form_type = Column(String(50), nullable=True)       # z. B. "contact", "lead", "custom"
    fields_json = Column(Text, nullable=True)           # Felder als JSON-String gespeichert
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Form(id={self.id}, name='{self.name}', type='{self.form_type}')>"
    
    
    # ─────────────────────────────
# 🌐 API-Integrationen (z. B. WhatsApp, Stripe, Mailgun …)
# ─────────────────────────────

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from app.database import Base

class Integration(Base):
    """
    Definiert externe Integrationen wie WhatsApp, Stripe, Mailgun usw.
    Enthält API-Schlüssel, Typ und Aktivierungsstatus.
    """
    __tablename__ = "integrations"

    # 🆔 Primärschlüssel
    id = Column(Integer, primary_key=True, index=True)

    # 📝 Name der Integration (z. B. „WhatsApp API“)
    name = Column(String(100), nullable=False)

    # 🧭 Typ (z. B. „whatsapp“, „stripe“, „mailgun“)
    type = Column(String(50), nullable=False)

    # 📄 Beschreibung (optional)
    description = Column(Text, nullable=True)

    # 🔑 API-Schlüssel (optional, falls Integration diesen benötigt)
    api_key = Column(String(255), nullable=True)

    # ✅ Aktiviert / Deaktiviert
    is_active = Column(Boolean, default=False)

    # 🕒 Zeitstempel
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Integration(name='{self.name}', type='{self.type}', active={self.is_active})>"
    
# ─────────────────────────────
# 📝 Berechtigungen & Rollen (feingranular)
# ─────────────────────────────


# 🔸 Zwischentabelle: Rolle ↔ Berechtigung (n:m)
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True)
)


# 🔸 Berechtigungs-Tabelle (z. B. "view_invoices", "edit_users")
class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False)   # z. B. "view_invoices"
    description = Column(String(255), nullable=True)

    # 🔁 n:m Beziehung zu Rollen
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions"
    )

    def __repr__(self):
        return f"<Permission(code={self.code})>"


# 🔸 Rollen-Tabelle (z. B. "admin", "mitarbeiter", "kunde")
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # z. B. "admin"
    description = Column(String(255), nullable=True)

    # 🔁 Beziehung zu Benutzern (1:n)
    users = relationship(
        "User",
        back_populates="role",
        cascade="all, delete"
    )

    # 🔁 Beziehung zu Berechtigungen (n:m)
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles"
    )

    def __repr__(self):
        return f"<Role(name={self.name})>"



# ─────────────────────────────
# 👤 Benutzer (CRM-kompatibel)
# ─────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ➕ Neue Felder:
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    birthday = Column(Date, nullable=True)

    # ➕ Passwort-Reset-Felder:
    reset_token = Column(String(100), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # 🔗 Rollenverknüpfung
    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users")

    # 🔗 Aktivitätslogs (optional)
    logs = relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete"
    )

    # -----------------------------
    # 🧰 Hilfsmethoden
    # -----------------------------
    def set_reset_token(self, token: str, minutes_valid: int = 30):
        """Setzt den Passwort-Reset-Token und Ablaufzeit."""
        self.reset_token = token
        self.reset_token_expires = datetime.utcnow() + timedelta(minutes=minutes_valid)

    def clear_reset_token(self):
        """Löscht den Reset-Token nach erfolgreichem Reset."""
        self.reset_token = None
        self.reset_token_expires = None

    def is_reset_token_valid(self, token: str) -> bool:
        """Prüft, ob ein Reset-Token gültig ist."""
        return (
            self.reset_token == token
            and self.reset_token_expires is not None
            and self.reset_token_expires > datetime.utcnow()
        )

    def __repr__(self):
        role_name = self.role.name if self.role else None
        return f"<User(username={self.username}, role={role_name})>"
    
    
# ─────────────────────────────
# 🔑 Passwort Reset Token
# ─────────────────────────────
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(100), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=1))

    # Beziehung zum User
    user = relationship("User", backref="password_reset_tokens")
    
    
    
    
    
# 🧠 KI Chat Nachrichten
class AIChatMessage(Base):
    """
    💬 Speichert Chat-Nachrichten zwischen Benutzer und KI-Assistent.
    - user_id: Verknüpfung mit eingeloggtem Benutzer
    - role: 'user' oder 'assistant'
    - content: Textnachricht
    - created_at: Zeitstempel
    """
    __tablename__ = "ai_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)   # Wer hat gefragt
    role = Column(String(20), nullable=False)                           # 'user' oder 'assistant'
    content = Column(Text, nullable=False)                              # Nachrichtentext
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Beziehung zum Benutzer (bidirektional)
    user = relationship("User", backref="ai_chat_messages")

# ⚙️ KI-Einstellungen (global oder pro Benutzer)
class AISettings(Base):
    """
    Speichert KI-Provider, Modell, API-Key sowie optional pro Benutzer.
    Wenn user_id = NULL → globale Einstellung.
    """
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, index=True)

    # NULL = global, sonst pro Benutzer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # KI Meta-Daten
    assistant_name = Column(String(100), default="Ouhud KI-Assistent")
    api_key = Column(String(255), nullable=True)
    provider = Column(String(50), nullable=False, default="openai")  # openai, gemini, local
    model = Column(String(100), nullable=False, default="gpt-4o-mini")
    active = Column(Boolean, default=False)

    # Beziehung zum User
    user = relationship("User", backref="ai_settings")

    def __repr__(self):
        return (
            f"<AISettings(provider='{self.provider}', "
            f"model='{self.model}', active={self.active})>"
        )