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
from datetime import datetime, timezone

from sqlalchemy import Table

# app/models.py
from datetime import  timedelta

from sqlalchemy.types import Enum as SqlEnum

from sqlalchemy.orm import declarative_base
from sqlalchemy.types import JSON

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
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT / Firma, der der Log gehört
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # 👤 Optionaler Benutzer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 📁 Kategorie (Customers, Leads, Invoices, System, Auth...)
    category = Column(String(50), nullable=True)

    # 📝 Aktionstext
    action = Column(String(255), nullable=False)

    # 🔍 Details (z. B. E-Mail, ID, Betrag)
    details = Column(Text, nullable=True)

    # ⏱ Zeitstempel
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Beziehungen
    user = relationship("User", back_populates="logs")

    def __repr__(self):
        return (
            f"<ActivityLog(id={self.id}, company_id={self.company_id}, "
            f"action='{self.action}', timestamp={self.timestamp})>"
        )
        
# ─────────────────────────────
# 👥 Kunden
# ─────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT Zugehörigkeit
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # 👤 Interne Daten
    customer_number = Column(String(20), unique=True, nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    name = Column(String(100), nullable=False)

    # 📧 Kontakt
    email = Column(String(120), nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)

    # 🏢 Optionale Kundenfirma (z. B. Mercedes AG)
    customer_company_id = Column(Integer, ForeignKey("customer_companies.id"), nullable=True)
    customer_company = relationship("CustomerCompany", back_populates="contacts")

    # 🔗 Beziehungen
    offers = relationship("Offer", back_populates="customer", cascade="all, delete")
    invoices = relationship("Invoice", back_populates="customer", cascade="all, delete")
    orders = relationship("OrderDB", back_populates="customer", cascade="all, delete")
    messages = relationship("Message", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.name} ({self.email})>"
    
# ─────────────────────────────
# 🧾 Rechnungen & Mahnwesen (Invoice / InvoiceItem)
# ─────────────────────────────

class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    cancelled = "cancelled"
    overdue = "overdue"
    reminder = "reminder"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # 👥 Kunde
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # 📄 Rechnungsdaten
    invoice_number = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)

    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.00)

    # 📬 Mahnwesen
    reminder_level = Column(Integer, default=0)             
    last_reminder_date = Column(Date, nullable=True)

    # 🔗 Beziehungen
    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Invoice #{self.invoice_number} total={self.total_amount} status={self.status}>"
    
class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)

    # 🧾 Zugehörige Rechnung
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    # 📝 Positionsdaten
    description = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0.0)
    tax_rate = Column(Float, nullable=False, default=0.0)

    invoice = relationship("Invoice", back_populates="items")

    def __repr__(self):
        return f"<Item '{self.description}' x{self.quantity} = {self.unit_price}€>"
    
    
# ─────────────────────────────
# 🏢 Firmeneinstellungen
# ─────────────────────────────

class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, unique=True)

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

    def __repr__(self):
        return f"<CompanySettings company_id={self.company_id}>"

# ─────────────────────────────
# 💳 Zahlungseingänge / CAMT Import Log
# ─────────────────────────────

class PaymentLog(Base):
    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    booking_date = Column(Date, nullable=False)
    message = Column(String(255), nullable=True)

    invoice = relationship("Invoice")

    def __repr__(self):
        return f"<PaymentLog invoice={self.invoice_id} amount={self.amount}>"
    
# ─────────────────────────────
# 🛍️ Produkte
# ─────────────────────────────

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(String(500))
    price = Column(Float, nullable=False)

    active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Product {self.name} price={self.price}>"
    
# ─────────────────────────────
# 🛍 Bestellungen (Orders)
# ─────────────────────────────

class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="offen")
    total_amount = Column(Float, nullable=False)

    customer = relationship("Customer", back_populates="orders")

    def __repr__(self):
        return f"<Order {self.id} total={self.total_amount}>"
    
# ─────────────────────────────
# 🚀 Leads & Opportunities (Tenant-ready)
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

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

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
    conversion_chance = Column(Integer, default=0)
    ai_notes = Column(Text, nullable=True)

    # 📄 Dokumente (FEHLTE! → SERVER CRASH)
    documents = relationship("Document", back_populates="lead")

    def __repr__(self):
        return f"<Lead {self.name} status={self.status}>"
# ─────────────────────────────
# 📝 Kalender-Events (Tenant-ready)
# ─────────────────────────────

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    title = Column(String(255), nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<CalendarEvent {self.title}>"
    
# 📌 Zahlungsstatus als Enum
class PaymentStatus(str, enum.Enum):
    received = "received"
    refunded = "refunded"
    pending = "pending"
    partial = "partial"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    method = Column(String(50), nullable=False)  # "Kreditkarte", "Bank", "Bar"
    status = Column(Enum(PaymentStatus), default=PaymentStatus.received)
    note = Column(String(255), nullable=True)

    invoice = relationship("Invoice", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.amount} for invoice={self.invoice_id}>"
    
# ─────────────────────────────
# 📥 Inbox / Nachrichtenmodell (Tenant-ready)
# ─────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    sender_name = Column(String(100), nullable=False)
    sender_email = Column(String(120), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer = relationship("Customer", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.subject}>"
    
# ─────────────────────────────
# 💬 Interner Team-Chat (Tenant-ready)
# ─────────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    sender = Column(String(100), nullable=False)
    message = Column(String(1000), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ChatMessage sender={self.sender}>"
    
# 📲 WhatsApp Nachrichten (Tenant-ready)
class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    from_number = Column(String(50), nullable=False)
    to_number = Column(String(50), nullable=False)
    message = Column(String(1000), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<WhatsAppMessage {self.id} from={self.from_number}>"
    

# ⚙️ WhatsApp Business Account Einstellungen (Tenant-ready)
class WhatsAppSettings(Base):
    __tablename__ = "whatsapp_settings"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    phone_number = Column(String(50), nullable=False)
    phone_number_id = Column(String(100), nullable=False)
    business_id = Column(String(100), nullable=False)
    access_token = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<WhatsAppSettings phone={self.phone_number}>"
    
# 📞 Anrufhistorie (Tenant-ready)
class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    direction = Column(String(10), nullable=False)     # inbound/outbound
    phone_number = Column(String(50), nullable=False)
    contact_name = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration = Column(Integer, nullable=True)
    status = Column(String(20), default="completed")   # completed/missed/rejected

    def __repr__(self):
        return f"<CallLog {self.phone_number} dir={self.direction}>"
    
# 🔌 Telefonanlagen / PBX Settings (Tenant-ready)
class PBXSettings(Base):
    __tablename__ = "pbx_settings"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    provider = Column(String(50), nullable=False)       # twilio, placetel, sipgate, fritzbox, etc.
    api_url = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=True)
    sip_user = Column(String(100), nullable=True)
    sip_password = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PBXSettings provider={self.provider}>"
    
# 📝 Audit Logs (Tenant-ready)
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    user = Column(String(100), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog user={self.user} action={self.action}>"
    
# ─────────────────────────────
# 📢 Marketing-Kampagnen (Tenant-ready)
# ─────────────────────────────

class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SqlEnum(CampaignStatus), default=CampaignStatus.draft)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Campaign {self.id} {self.name} status={self.status}>"
    
# ─────────────────────────────
# 🎯 Zielgruppen-Segmente (Tenant-ready)
# ─────────────────────────────

class Segment(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Segment {self.id} {self.name}>"
    
# ─────────────────────────────
# 📝 Formulare (Tenant-ready)
# ─────────────────────────────

class Form(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # contact, lead, custom, landing-page-form etc.
    form_type = Column(String(50), nullable=True)

    fields_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Form {self.id} {self.name}>"
    
# ─────────────────────────────
# 🌐 API-Integrationen (z. B. WhatsApp, Stripe, Mailgun …)
# ─────────────────────────────

# ─────────────────────────────
# 🌐 API-Integrationen (Tenant-ready)
# ─────────────────────────────

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 TENANT
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)   # stripe, mailgun, whatsapp, sendgrid, etc.
    description = Column(Text, nullable=True)

    api_key = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Integration {self.name} ({self.type}) active={self.is_active}>"
    
# ─────────────────────────────
# 🔗 Rollen ↔ Berechtigungen (n:m)
# ─────────────────────────────

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True)
)
# ─────────────────────────────
# 🧩 Berechtigungen (feingranular)
# z. B.: "view_invoices", "edit_leads", "delete_users"
# ─────────────────────────────

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    # 🔁 Rollen (n:m)
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions"
    )

    def __repr__(self):
        return f"<Permission(code='{self.code}')>"
    

# ─────────────────────────────
# 👑 Rollen eines Tenants
# z. B.: admin, mitarbeiter, buchhaltung, support
# ─────────────────────────────

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 Tenant
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)

    # 🔁 Benutzer (1:n)
    users = relationship("User", back_populates="role", cascade="all, delete")

    # 🔁 Berechtigungen (n:m)
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles"
    )

    # Tenant-Backref
    company = relationship("Company", back_populates="roles")

    def __repr__(self):
        return f"<Role(name='{self.name}', company={self.company_id})>"
    
# ─────────────────────────────
# 👤 Benutzer (SaaS-ready)
# ─────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 Pflicht: Jeder User gehört zu EINEM Tenant
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 📇 Profilfelder
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    birthday = Column(Date, nullable=True)

    # 🔑 Passwort-Reset (legacy Felder)
    reset_token = Column(String(100), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # 🔗 Rollen
    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users")

    # 🔗 Tenant-Beziehung
    company = relationship("Company", back_populates="users")

    # 🔁 Aktivitätslogs
    logs = relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete"
    )

    # 📄 Dokumente
    documents = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # 🔑 Passwort-Reset-Token MODEL-BEZIEHUNG (NEU / WICHTIG!)
    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # 🔁 AI Chat Messages
    ai_chat_messages = relationship(
        "AIChatMessage",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # 🔐 Token-Methoden
    def set_reset_token(self, token: str, minutes_valid: int = 30):
        self.reset_token = token
        self.reset_token_expires = datetime.utcnow() + timedelta(minutes=minutes_valid)

    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expires = None

    def is_reset_token_valid(self, token: str) -> bool:
        return (
            self.reset_token == token
            and self.reset_token_expires
            and self.reset_token_expires > datetime.utcnow()
        )

    def __repr__(self):
        return (
            f"<User(username={self.username}, company={self.company_id}, "
            f"role={self.role.name if self.role else None})>"
        )
        
# ─────────────────────────────
# 🔑 Passwort Reset Token (SaaS-ready)
# ─────────────────────────────
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 Tenant-Vererbung über User.company_id
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    token = Column(String(100), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=1))

    # Beziehung zum Benutzer
    user = relationship("User", back_populates="password_reset_tokens")

    def __repr__(self):
        return f"<PasswordResetToken user={self.user_id} expires={self.expires_at}>"
    
# ─────────────────────────────
# 🤖 KI Chat Nachrichten (mandantenfähig)
# ─────────────────────────────
class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    # 🧑 Benutzer (damit automatisch company_id vorhanden)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    role = Column(String(20), nullable=False)   # 'user' oder 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Beziehung
    user = relationship("User", back_populates="ai_chat_messages")

    def __repr__(self):
        return f"<AIChatMessage user={self.user_id} role={self.role}>"
# ─────────────────────────────
# ⚙️ KI Einstellungen (Tenant + User)
# ─────────────────────────────
class AISettings(Base):
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, index=True)

    # 🔐 Option 1 → Global für eine Firma
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # 🔐 Option 2 → Spezifisch pro Benutzer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    assistant_name = Column(String(100), default="Ouhud KI-Assistent")
    api_key = Column(String(255), nullable=True)
    provider = Column(String(50), nullable=False, default="openai")
    model = Column(String(100), nullable=False, default="gpt-4o-mini")
    active = Column(Boolean, default=False)

    # Beziehungen
    company = relationship("Company", backref="ai_settings")
    user = relationship("User")

    def __repr__(self):
        return f"<AISettings provider={self.provider} model={self.model} tenant={self.company_id}>"
    

# ─────────────────────────────
# 📄 Dokumente (Multi-Tenant)
# ─────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 Pflicht-Feld → jedes Dokument gehört zu einer Firma!
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    filename = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True)

    file_size = Column(Integer, nullable=True)
    file_type = Column(String(50), nullable=True)

    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Optionaler Kunde / Lead
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)

    # Beziehungen
    company = relationship("Company", backref="documents")
    user = relationship("User", back_populates="documents")
    customer = relationship("Customer", backref="documents")
    lead = relationship("LeadDB", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.filename} company={self.company_id}>"
    
    
# ─────────────────────────────
# 🔧 Workflow / Automation Designer (SaaS-ready)
# ─────────────────────────────
class AutomationDesigner(Base):
    __tablename__ = "automation_designer"

    id = Column(Integer, primary_key=True, index=True)

    # 🏢 Tenant (Pflicht für SaaS)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Nodes + Edges + Actions des Designers
    config_json = Column(JSON, nullable=False, default={})

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    company = relationship("Company", backref="automation_designer")

    def __repr__(self):
        return f"<AutomationDesigner name='{self.name}' company={self.company_id}>"
    
# ─────────────────────────────
# 🏢 Firmen Deiner Kunden (NICHT Tenant!)
# ─────────────────────────────
class CustomerCompany(Base):
    __tablename__ = "customer_companies"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    address = Column(String(255))
    city = Column(String(100))
    country = Column(String(50))
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))

    # Beziehung zu Kunden (Customer)
    contacts = relationship(
        "Customer",
        back_populates="customer_company",  # FIX
        cascade="all, delete-orphan"
    )

    # Beziehung zu Email-Providern
    email_providers = relationship(
        "EmailProvider",
        back_populates="customer_company",
        cascade="all, delete-orphan"
    )

    # Beziehung zu Logs
    email_logs = relationship(
        "EmailLog",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<CustomerCompany {self.name}>"
    
    
# ─────────────────────────────
# 📄 Angebote (mandantenfähig)
# ─────────────────────────────
class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="offen")  # offen, versendet, akzeptiert, abgelehnt
    created_at = Column(DateTime, default=datetime.utcnow)

    # Kunde
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="offers")

    # Beziehung zum Tenant
    company = relationship("Company", back_populates="offers")

    def __repr__(self):
        return f"<Offer {self.title} ({self.amount}€)>"
# ─────────────────────────────
# 📧 E-Mail-Provider pro Kundenfirma
# ─────────────────────────────
class EmailProvider(Base):
    __tablename__ = "email_providers"

    id = Column(Integer, primary_key=True, index=True)

    customer_company_id = Column(
        Integer, 
        ForeignKey("customer_companies.id"), 
        nullable=False
    )

    provider = Column(String(50), nullable=False)

    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)   # FIXED
    smtp_user = Column(String(255), nullable=True)
    smtp_password = Column(Text, nullable=True)

    sendgrid_key = Column(Text, nullable=True)
    mailgun_key = Column(Text, nullable=True)
    ses_key = Column(Text, nullable=True)
    ses_secret = Column(Text, nullable=True)
    ses_region = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Beziehung zurück zu CustomerCompany
    customer_company = relationship(
        "CustomerCompany", 
        back_populates="email_providers"
    )

    # Beziehung zu Logs
    logs = relationship(
        "EmailLog", 
        back_populates="provider_ref", 
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<EmailProvider {self.provider}>"
# ─────────────────────────────
# 📨 E-Mail Logs
# ─────────────────────────────
class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)

    customer_company_id = Column(Integer, ForeignKey("customer_companies.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("email_providers.id"), nullable=False)

    to_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    message_preview = Column(Text, nullable=True)

    status = Column(String(50), default="sent")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    provider_ref = relationship("EmailProvider", back_populates="logs")
    company = relationship("CustomerCompany", back_populates="email_logs")

    def __repr__(self):
        return f"<EmailLog to='{self.to_email}' status='{self.status}'>"
    
# ─────────────────────────────
# 🏢 SaaS Tenant (Firma im CRM)
# ─────────────────────────────
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    # Haupt-Firmendaten
    name = Column(String(255), nullable=False)

    # Subdomain wie "arabia.ouhud.com"
    subdomain = Column(String(255), unique=True, nullable=False)

    # OPTIONAL: Eigene Domain des Kunden
    custom_domain = Column(String(255), unique=True, nullable=True)

    # Firmeninhaber (Admin der Firma)
    owner_email = Column(String(255), nullable=False)

    # SaaS Tarif (Free/Pro/Enterprise)
    plan = Column(String(50), default="free")

    # Account-Status
    status = Column(String(20), default="active")  # active / suspended / cancelled

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Beziehungen
    users = relationship("User", back_populates="company", cascade="all, delete")
    offers = relationship("Offer", back_populates="company", cascade="all, delete")

    # ❗❗❗ FEHLTE – MUSS REIN!
    roles = relationship("Role", back_populates="company", cascade="all, delete")

    def __repr__(self):
        domain = self.custom_domain if self.custom_domain else f"{self.subdomain}.ouhud.com"
        return f"<Company {self.name} ({domain})>"
    
# ─────────────────────────────
# 📧 E-Mail Automationen (Tenant-unabhängig)
# ─────────────────────────────
class EmailAutomation(Base):
    __tablename__ = "email_automations"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    trigger = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EmailAutomation {self.title}>"


# ─────────────────────────────
# 📝 Activity Log (Tenant-unabhängig)
# ─────────────────────────────
class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Activity {self.title}>"
    
    
    
    
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Welche Firma dieses Abo besitzt
    company_id = Column(Integer, ForeignKey("customer_companies.id"), nullable=False)

    # Plan: basic, pro, professional
    plan = Column(String(50), nullable=False)

    # Abrechnung: monthly oder yearly
    billing_cycle = Column(String(10), nullable=False)

    # Wann die Subscription begonnen hat
    start_date = Column(DateTime, default=datetime.utcnow)

    # 14 Tage Testphase → Ende
    trial_end = Column(DateTime, nullable=True)

    # 3 freie Monate nach dem Trial
    free_months_end = Column(DateTime, nullable=True)

    # Nächste Zahlung (Stripe oder manuell)
    next_payment = Column(DateTime, nullable=True)

    # Status: trial, active, paused, canceled, unpaid
    status = Column(String(20), default="trial")

    # Optional: Stripe / Payment Provider ID
    provider_subscription_id = Column(String(255), nullable=True)

    # Falls gekündigt:
    canceled_at = Column(DateTime, nullable=True)

    # Anzahl Benutzer im Tarif (für spätere Limits)
    user_limit = Column(Integer, default=1)

    # System Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    