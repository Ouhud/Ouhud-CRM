from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


# ---------------------------------------------------------
# WORKFLOW (Master)
# ---------------------------------------------------------
class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)

    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    triggers = relationship(
        "WorkflowTrigger",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    actions = relationship(
        "WorkflowAction",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )


# ---------------------------------------------------------
# TRIGGER (Startpunkt)
# ---------------------------------------------------------
class WorkflowTrigger(Base):
    __tablename__ = "workflow_triggers"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"))

    # Beispiele:
    # "on_create", "on_update", "schedule", "webhook"
    trigger_type = Column(String(100), nullable=False)

    # Alle Trigger-Einstellungen (z.B. schedule, webhook settings usw.)
    config_json = Column(JSON, nullable=True, default={})

    # ➤ Neu: IF-Bedingungen
    # Beispiele:
    # {
    #   "if": [
    #       { "field": "status", "operator": "=", "value": "new" }
    #   ]
    # }
    conditions_json = Column(JSON, nullable=True, default={})

    # Relation
    workflow = relationship("Workflow", back_populates="triggers")


# ---------------------------------------------------------
# ACTIONS (nach Trigger)
# ---------------------------------------------------------
class WorkflowAction(Base):
    __tablename__ = "workflow_actions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"))

    # Reihenfolge wie bei Zapier (1,2,3…)
    order_index = Column(Integer, nullable=False, default=1)

    # Action-Typen:
    # "send_email", "create_task", "update_record", "ai.generate", "webhook.call"
    action_type = Column(String(100), nullable=False)

    # JSON-Config der Aktion:
    # z.B. {"to": "...", "subject": "..."}
    config_json = Column(JSON, nullable=True, default={})

    workflow = relationship("Workflow", back_populates="actions")