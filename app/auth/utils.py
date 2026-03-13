from fastapi import Request
from fastapi.responses import RedirectResponse


def require_login(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login")