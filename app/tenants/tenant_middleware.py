# app/middleware/tenant_middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.tenants.tenant_service import (
    extract_subdomain,
    resolve_company_by_subdomain,
    resolve_company_by_custom_domain
)

ALLOWED_BASE_DOMAINS = ["ouhud.com", "crm.ouhud.com", "localhost"]


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").lower()

        # 1. Prüfe zuerst: Custom Domain (z. B. firma.de)
        company = resolve_company_by_custom_domain(host)
        if company:
            request.state.company = company
            return await call_next(request)

        # 2. Prüfe Subdomain (z. B. acme.crm.ouhud.com)
        subdomain = extract_subdomain(host)
        if subdomain:
            company = resolve_company_by_subdomain(subdomain)
            if company:
                request.state.company = company
                return await call_next(request)

        # 3. Kein Tenant → öffentlich / neutral
        request.state.company = None
        return await call_next(request)