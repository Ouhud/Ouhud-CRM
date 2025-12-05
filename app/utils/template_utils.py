from fastapi import Request
from typing import Dict, Any


def render_template(
    request: Request,
    template_name: str,
    context: Dict[str, Any]
):
    """
    Universale Render-Funktion für ALLE Templates.
    Sie garantiert:
    - 'request' wird immer gesetzt
    - 'user' ist IMMER vorhanden (für base.html)
    - 'company' wird sicher hinzugefügt
    - KEIN circular import
    - Nutzt das zentrale template-System aus main.py
    """

    # ⭐ Templates IMMER über app.state.templates, nicht neu erstellen!
    templates = request.app.state.templates

    # 1) request setzen
    context["request"] = request

    # 2) user einfügen
    current_user = getattr(request.state, "user", None)
    context.setdefault("user", current_user)

    # 3) company sicher holen
    company = None
    if current_user:
        try:
            company = getattr(current_user, "company", None)
        except Exception:
            company = None

    context.setdefault("company", company)

    # 4) Template rendern
    return templates.TemplateResponse(template_name, context)