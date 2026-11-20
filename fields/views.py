"""Thin views: parse input, call services, render. No business logic here."""

from __future__ import annotations

import datetime as dt
import hmac
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from aquapin_core.crops import list_crops
from aquapin_core.errors import AquaPinError
from aquapin_core.geometry import MAX_RADIUS_M, MIN_RADIUS_M

from .bot import TelegramClient, handle_update
from .i18n import LANGS, STRINGS, error_text, lang_for, tr
from .models import Field, Job, Result, TelegramUpdate
from .ratelimit import allow
from .render import validation_text
from .services import create_field_job, default_planting_date, delete_field

DEMO_DIR = Path(settings.BASE_DIR) / "fields" / "static" / "fields" / "demo"
_SLUG = re.compile(r"^[a-z0-9-]{1,40}$")
_ASSET = re.compile(r"^(base\.jpg|frames/\d{4}-\d{2}-\d{2}\.png)$")


@lru_cache(maxsize=32)
def _read_demo(path: str, mtime: float) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def list_demos() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if DEMO_DIR.is_dir():
        for folder in sorted(DEMO_DIR.iterdir()):
            f = folder / "data.json"
            if f.is_file() and _SLUG.match(folder.name):
                d = _read_demo(str(f), f.stat().st_mtime)
                out.append({"slug": folder.name, "name": d["name"], "name_ru": d["name_ru"]})
    return out


def load_demo(slug: str) -> dict[str, Any] | None:
    if not _SLUG.match(slug):
        return None
    f = DEMO_DIR / slug / "data.json"
    return _read_demo(str(f), f.stat().st_mtime) if f.is_file() else None


def _owner_key(request: HttpRequest) -> str:
    if not request.session.session_key:
        request.session.create()
    return f"web:{request.session.session_key}"


def _base_context(request: HttpRequest) -> dict[str, Any]:
    lang = lang_for(request)
    return {"lang": lang, "T": STRINGS[lang], "langs": LANGS, "demos": list_demos()}


def _viewer(
    request: HttpRequest,
    *,
    data: dict[str, Any],
    asset_base: str,
    title: str,
    mode: str,
    field: Field | None = None,
) -> HttpResponse:
    ctx = _base_context(request)
    ctx.update(
        {
            "viewer": data,
            "title_name": title,
            "mode": mode,
            "field": field,
            "validation_text": validation_text(ctx["lang"]),
            "cfg": {"assetBase": asset_base, "autoplay": mode == "demo", "lang": ctx["lang"]},
        }
    )
    return render(request, "fields/viewer.html", ctx)


@require_GET
def index(request: HttpRequest) -> HttpResponse:
    demos = list_demos()
    if not demos:
        ctx = _base_context(request)
        return render(request, "fields/empty.html", ctx, status=200)
    return redirect("demo", slug=demos[0]["slug"])


@require_GET
def demo(request: HttpRequest, slug: str) -> HttpResponse:
    data = load_demo(slug)
    if data is None:
        raise Http404("unknown example")
    lang = lang_for(request)
    name = data["name_ru"] if lang == "ru" else data["name"]
    from django.templatetags.static import static

    return _viewer(
        request, data=data, asset_base=static(f"fields/demo/{slug}/"), title=name, mode="demo"
    )


def _pin_context(request: HttpRequest, error: str = "") -> dict[str, Any]:
    ctx = _base_context(request)
    today = dt.date.today()
    ctx.update(
        {
            "map_labels": {
                "satellite": ctx["T"]["map_satellite"],
                "streets": ctx["T"]["map_streets"],
            },
            "error": error,
            "crops": list_crops(),
            "min_r": MIN_RADIUS_M,
            "max_r": MAX_RADIUS_M,
            "default_planting": default_planting_date(today).isoformat(),
            "today": today.isoformat(),
        }
    )
    return ctx


def pin(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(request, "fields/pin.html", _pin_context(request))
    if request.method != "POST":
        return HttpResponseBadRequest("method not allowed")
    lang = lang_for(request)
    owner = _owner_key(request)
    if not allow(f"pin:{owner}", 5, 3600):
        return render(request, "fields/pin.html", _pin_context(request, "rate"), status=429)
    if request.POST.get("consent") != "on":
        return render(
            request, "fields/pin.html", _pin_context(request, tr(lang, "consent")), status=400
        )
    try:
        lat = float(request.POST["lat"])
        lon = float(request.POST["lon"])
        radius = float(request.POST["radius"])
        planting = dt.date.fromisoformat(request.POST["planting"])
        crop = request.POST.get("crop", "")
        raw_as_of = request.POST.get("as_of", "").strip()
        as_of = dt.date.fromisoformat(raw_as_of) if raw_as_of else None
        if as_of == dt.date.today():
            as_of = None  # live advice
        field, _ = create_field_job(
            owner_key=owner,
            lat=lat,
            lon=lon,
            radius_m=radius,
            crop_id=crop,
            planting=planting,
            today=dt.date.today(),
            analysis_date=as_of,
        )
    except (KeyError, ValueError):
        return render(
            request,
            "fields/pin.html",
            _pin_context(request, error_text(lang, "GeometryError")),
            status=400,
        )
    except AquaPinError as exc:
        return render(
            request,
            "fields/pin.html",
            _pin_context(request, error_text(lang, type(exc).__name__)),
            status=400,
        )
    return redirect("field", field_id=field.id)


def _own_field(request: HttpRequest, field_id: str) -> Field:
    """Owner-scoped lookup: another owner's UUID looks exactly like a missing one (404)."""
    field = Field.objects.filter(id=field_id, owner_key=_owner_key(request)).first()
    if field is None:
        raise Http404("no such field")
    return field


@require_GET
def field_detail(request: HttpRequest, field_id: str) -> HttpResponse:
    field = _own_field(request, field_id)
    result = Result.objects.filter(field=field).order_by("-computed_on", "-id").first()
    job = field.jobs.order_by("-created_at").first()
    lang = lang_for(request)
    if result is not None and (job is None or job.status == Job.Status.DONE):
        from django.urls import reverse

        data = dict(result.payload)
        data.update(
            {
                "name": f"{field.lat:.3f}, {field.lon:.3f}",
                "name_ru": f"{field.lat:.3f}, {field.lon:.3f}",
            }
        )
        return _viewer(
            request,
            data=data,
            asset_base=reverse("field_asset", args=[field.id, "x"])[:-1],
            title=data["name"],
            mode="live",
            field=field,
        )
    ctx = _base_context(request)
    failed = job is not None and job.status == Job.Status.FAILED
    ctx.update(
        {
            "field": field,
            "failed": failed,
            "error_message": error_text(lang, job.error_code) if failed and job else "",
        }
    )
    return render(request, "fields/loading.html", ctx, status=200)


@require_GET
def field_status(request: HttpRequest, field_id: str) -> JsonResponse:
    field = _own_field(request, field_id)
    job = field.jobs.order_by("-created_at").first()
    return JsonResponse(
        {"status": job.status if job else "none", "error_code": job.error_code if job else ""}
    )


@require_POST
def field_retry(request: HttpRequest, field_id: str) -> HttpResponse:
    field = _own_field(request, field_id)
    if not allow(f"retry:{field.id}", 5, 3600):
        return HttpResponse(status=429)
    job = field.jobs.order_by("-created_at").first()
    if job is not None and job.status == Job.Status.FAILED:
        job.status, job.attempts, job.error_code, job.error_text = Job.Status.PENDING, 0, "", ""
        job.save(update_fields=["status", "attempts", "error_code", "error_text"])
    return redirect("field", field_id=field.id)


@require_POST
def field_delete(request: HttpRequest, field_id: str) -> HttpResponse:
    delete_field(_own_field(request, field_id))
    return redirect("index")


@require_GET
def field_api(request: HttpRequest, field_id: str) -> JsonResponse:
    field = _own_field(request, field_id)
    result = Result.objects.filter(field=field).order_by("-computed_on", "-id").first()
    if result is None:
        raise Http404("no result yet")
    return JsonResponse(result.payload["advice_final"])


@require_GET
def field_asset(request: HttpRequest, field_id: str, path: str) -> FileResponse:
    field = _own_field(request, field_id)
    if not _ASSET.match(path):
        raise Http404("bad asset path")
    file = settings.LIVE_DATA_ROOT / str(field.id) / path
    if not file.is_file():
        raise Http404("no such asset")
    return FileResponse(
        open(file, "rb"), content_type="image/jpeg" if path.endswith(".jpg") else "image/png"
    )


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def telegram_webhook(request: HttpRequest) -> HttpResponse:
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if not secret:
        return HttpResponse("telegram webhook is not configured", status=503)
    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(supplied.encode(), secret.encode()):
        return HttpResponseForbidden("forbidden")
    try:
        update = json.loads(request.body.decode("utf-8"))
        update_id = int(update["update_id"])
    except (ValueError, KeyError, TypeError):
        return HttpResponseBadRequest("bad update")
    try:
        with transaction.atomic():
            TelegramUpdate.objects.create(update_id=update_id)
    except IntegrityError:
        return HttpResponse("duplicate")  # already handled: Telegram retried
    handle_update(update, TelegramClient())
    return HttpResponse("ok")


def set_language(request: HttpRequest, code: str) -> HttpResponse:
    if code in LANGS:
        request.session["lang"] = code
    target = request.META.get("HTTP_REFERER", "")
    host = request.get_host()
    return redirect(
        target
        if target.startswith(f"http://{host}") or target.startswith(f"https://{host}")
        else "index"
    )
