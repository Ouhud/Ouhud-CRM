# app/tenants/tenant_context.py

from contextvars import ContextVar

current_tenant_id = ContextVar("current_tenant_id", default=None)

def set_current_tenant(tenant_id: int):
    current_tenant_id.set(tenant_id)

def get_current_tenant():
    return current_tenant_id.get()