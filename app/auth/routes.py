from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="templates")

USERNAME = "admin"
PASSWORD = "tyres123"


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):

    if username == USERNAME and password == PASSWORD:
        request.session["user"] = username
        return RedirectResponse("/ui/", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid login"}
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)