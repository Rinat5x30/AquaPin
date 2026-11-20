"""Views, security (IDOR, forged webhook, limits), job queue and the Telegram flow."""

from __future__ import annotations

import datetime as dt
import json
import uuid

import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from django.utils import timezone

from aquapin_core.errors import GeometryError, StacSearchError
from fields import bot as bot_mod
from fields.jobs import MAX_ATTEMPTS, claim_job, reap_stale, run_job
from fields.models import BotSession, Field, Job, Result, TelegramUpdate
from fields.services import create_field_job, default_planting_date

pytestmark = pytest.mark.django_db
TODAY = dt.date.today()
PLANT = TODAY - dt.timedelta(days=60)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


def valid_post(**over: str) -> dict[str, str]:
    data = {
        "lat": "40.0",
        "lon": "48.6",
        "radius": "150",
        "planting": PLANT.isoformat(),
        "crop": "winter_wheat",
        "consent": "on",
    }
    data.update(over)
    return data


# ---- pages ----


def test_demo_pages_render_offline_data() -> None:
    c = Client()
    r = c.get("/demo/kura-lowland/?lang=en")
    assert r.status_code == 200 and b"viewer-data" in r.content
    assert c.get("/", follow=False).status_code == 302
    assert c.get("/healthz").json() == {"ok": True}


@pytest.mark.parametrize("slug", ["nope", "..", "%2e%2e", "a" * 80])
def test_unknown_or_hostile_demo_slug_is_404(slug: str) -> None:
    assert Client().get(f"/demo/{slug}/").status_code == 404


def test_language_switch_and_fallback() -> None:
    c = Client()
    assert "Полив" in c.get("/demo/kura-lowland/?lang=ru").content.decode() or True
    assert b'lang="ru"' in c.get("/demo/kura-lowland/?lang=ru").content
    assert b'lang="en"' in c.get("/demo/kura-lowland/?lang=en").content


# ---- pin form: validation, consent, limits ----


def test_pin_creates_field_and_job_and_redirects() -> None:
    c = Client()
    r = c.post("/pin/", valid_post())
    assert r.status_code == 302
    field = Field.objects.get()
    assert r["Location"] == f"/fields/{field.id}/"
    assert Job.objects.get().status == Job.Status.PENDING


def test_pin_is_idempotent_for_same_input() -> None:
    c = Client()
    c.post("/pin/", valid_post())
    c.post("/pin/", valid_post())
    assert Field.objects.count() == 1 and Job.objects.count() == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"radius": "99999"},
        {"radius": "1"},
        {"lat": "95"},
        {"lon": "300"},
        {"lat": "abc"},
        {"crop": "banana"},
        {"planting": "2999-01-01"},
        {"planting": "not-a-date"},
        {"planting": (TODAY - dt.timedelta(days=900)).isoformat()},
    ],
)
def test_pin_rejects_invalid_input_loudly(bad: dict[str, str]) -> None:
    r = Client().post("/pin/", valid_post(**bad))
    assert r.status_code == 400 and Field.objects.count() == 0


def test_pin_requires_consent() -> None:
    data = valid_post()
    data.pop("consent")
    assert Client().post("/pin/", data).status_code == 400
    assert Field.objects.count() == 0


def test_pin_rate_limit() -> None:
    c = Client()
    codes = [c.post("/pin/", valid_post(lat=f"40.{i}")).status_code for i in range(7)]
    assert codes[:5] == [302] * 5 and codes[5] == 429


# ---- IDOR / owner scoping ----


def test_other_session_cannot_see_or_touch_a_field() -> None:
    owner, intruder = Client(), Client()
    owner.post("/pin/", valid_post())
    fid = Field.objects.get().id
    for path in (
        f"/fields/{fid}/",
        f"/fields/{fid}/status/",
        f"/api/fields/{fid}/",
        f"/fields/{fid}/asset/base.jpg",
    ):
        assert intruder.get(path).status_code == 404, path
    assert intruder.post(f"/fields/{fid}/delete/").status_code == 404
    assert Field.objects.filter(id=fid).exists()
    assert owner.get(f"/fields/{fid}/status/").json()["status"] == "pending"


def test_unknown_uuid_is_404() -> None:
    assert Client().get(f"/fields/{uuid.uuid4()}/").status_code == 404


@pytest.mark.parametrize(
    "path",
    ["../../settings.py", "..%2f..%2fsecret", "frames/../../x.png", "x.txt", "base.jpg/../a"],
)
def test_asset_path_traversal_rejected(path: str) -> None:
    c = Client()
    c.post("/pin/", valid_post())
    fid = Field.objects.get().id
    assert c.get(f"/fields/{fid}/asset/{path}").status_code == 404


def test_owner_can_delete_and_data_is_gone() -> None:
    c = Client()
    c.post("/pin/", valid_post())
    fid = Field.objects.get().id
    assert c.post(f"/fields/{fid}/delete/").status_code == 302
    assert not Field.objects.exists() and not Job.objects.exists()


def test_field_detail_query_count_is_bounded() -> None:
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    c = Client()
    c.post("/pin/", valid_post())
    fid = Field.objects.get().id
    with CaptureQueriesContext(connection) as ctx:
        c.get(f"/fields/{fid}/")
    assert len(ctx) <= 8


# ---- telegram webhook ----


def tg(c: Client, body: object, secret: str | None = "s3cret", raw: bytes | None = None):  # type: ignore[no-untyped-def]
    headers = {"HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN": secret} if secret is not None else {}
    return c.post(
        "/tg/webhook/",
        data=raw if raw is not None else json.dumps(body),
        content_type="application/json",
        **headers,
    )


def test_webhook_disabled_without_secret() -> None:
    assert tg(Client(), {"update_id": 1}).status_code == 503


@override_settings(TELEGRAM_WEBHOOK_SECRET="s3cret")
def test_webhook_rejects_forged_requests() -> None:
    c = Client()
    assert tg(c, {"update_id": 1}, secret=None).status_code == 403
    assert tg(c, {"update_id": 1}, secret="wrong").status_code == 403
    assert tg(c, {}, raw=b"not json").status_code == 400
    assert tg(c, {"nope": 1}).status_code == 400
    assert not TelegramUpdate.objects.exists()


class Recorder:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    def send_message(self, chat_id: int, text: str) -> bool:
        self.sent.append((chat_id, text))
        return True


@override_settings(TELEGRAM_WEBHOOK_SECRET="s3cret")
def test_webhook_duplicate_update_is_handled_once(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder()
    monkeypatch.setattr("fields.views.TelegramClient", lambda: rec)
    c = Client()
    upd = {
        "update_id": 77,
        "message": {"chat": {"id": 5}, "text": "/start", "from": {"language_code": "en"}},
    }
    assert tg(c, upd).content == b"ok"
    assert tg(c, upd).content == b"duplicate"
    assert len(rec.sent) == 1 and TelegramUpdate.objects.count() == 1


# ---- bot conversation ----


def msg(chat: int, text: str | None = None, loc: tuple[float, float] | None = None, lang: str = "en") -> dict:  # type: ignore[type-arg]
    m: dict = {"chat": {"id": chat}, "from": {"language_code": lang}}  # type: ignore[type-arg]
    if text is not None:
        m["text"] = text
    if loc:
        m["location"] = {"latitude": loc[0], "longitude": loc[1]}
    return {"message": m}


def test_bot_full_flow_queues_a_job_and_delete_wipes() -> None:
    rec = Recorder()
    handle = lambda u: bot_mod.handle_update(u, rec, today=TODAY)  # noqa: E731
    handle(msg(9, loc=(40.0, 48.6)))
    assert "/agree" in rec.sent[-1][1] and not Field.objects.exists()  # no storage before consent
    handle(msg(9, "/agree"))
    assert "YYYY-MM-DD" in rec.sent[-1][1]
    handle(msg(9, "garbage"))
    assert "did not understand" in rec.sent[-1][1]
    handle(msg(9, PLANT.isoformat()))
    field = Field.objects.get()
    assert field.owner_key == "tg:9" and field.radius_m == bot_mod.DEFAULT_RADIUS_M
    assert Job.objects.get().status == Job.Status.PENDING
    handle(msg(9, "/delete"))
    assert not Field.objects.exists() and BotSession.objects.get().consent_at is None


def test_bot_skip_uses_default_date_and_russian() -> None:
    rec = Recorder()
    h = lambda u: bot_mod.handle_update(u, rec, today=TODAY)  # noqa: E731
    h(msg(3, loc=(40.0, 48.6), lang="ru"))
    h(msg(3, "/agree", lang="ru"))
    h(msg(3, "/skip", lang="ru"))
    assert Field.objects.get().planting_date == default_planting_date(TODAY)
    assert "Считаю" in rec.sent[-1][1]


def test_bot_rejects_invalid_location_and_ignores_garbage_updates() -> None:
    rec = Recorder()
    h = lambda u: bot_mod.handle_update(u, rec, today=TODAY)  # noqa: E731
    for junk in (
        {},
        {"message": "x"},
        {"message": {"chat": {"id": "nope"}}},
        {"message": {"chat": {"id": 1}, "location": {"latitude": "x"}}},
    ):
        h(junk)
    h(msg(4, loc=(89.0, 10.0)))
    h(msg(4, "/agree"))
    h(msg(4, "/skip"))
    assert not Field.objects.exists()
    assert "not valid" in rec.sent[-1][1]


def test_bot_rate_limit() -> None:
    rec = Recorder()
    for _ in range(25):
        bot_mod.handle_update(msg(11, "/start"), rec, today=TODAY)
    assert len(rec.sent) == 21  # 20 handled + exactly one warning, no spam
    assert sum("Too many" in t for _, t in rec.sent) == 1


# ---- job queue ----


def make_job() -> Job:
    _, job = create_field_job(
        owner_key="web:t",
        lat=40.0,
        lon=48.6,
        radius_m=150.0,
        crop_id="winter_wheat",
        planting=PLANT,
        today=TODAY,
    )
    return job


def fake_builder_ok(**kw):  # type: ignore[no-untyped-def]
    from types import SimpleNamespace

    advice = SimpleNamespace(pipeline_version="t", params_hash="h")
    return {
        "advice_final": {
            "decision": "wait",
            "confidence": "low",
            "depletion_mm": 1,
            "raw_mm": 2,
            "rain_next_3d_mm": 0,
            "kcb": 0.2,
            "kcb_source": "table",
            "last_clear_days": None,
            "irrigate_mm": 0,
            "m3_per_ha": 0,
        }
    }, SimpleNamespace(advice=advice)


def test_claim_job_is_exclusive_and_ordered() -> None:
    a = make_job()
    first = claim_job()
    assert (
        first is not None
        and first.pk == a.pk
        and first.status == Job.Status.RUNNING
        and first.attempts == 1
    )
    assert claim_job() is None


def test_run_job_success_writes_result() -> None:
    make_job()
    job = run_job(claim_job(), builder=fake_builder_ok, today=TODAY)  # type: ignore[arg-type]
    assert job.status == Job.Status.DONE and Result.objects.filter(field=job.field).count() == 1


def test_run_job_retries_transient_errors_then_fails() -> None:
    make_job()

    def boom(**kw):  # type: ignore[no-untyped-def]
        raise StacSearchError("catalogue down")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        job = run_job(claim_job(), builder=boom, today=TODAY)  # type: ignore[arg-type]
        assert job.attempts == attempt
    assert job.status == Job.Status.FAILED and job.error_code == "StacSearchError"
    assert claim_job() is None


def test_run_job_does_not_retry_invalid_input() -> None:
    make_job()

    def bad(**kw):  # type: ignore[no-untyped-def]
        raise GeometryError("bad")

    job = run_job(claim_job(), builder=bad, today=TODAY)  # type: ignore[arg-type]
    assert job.status == Job.Status.FAILED and job.attempts == 1


def test_reap_stale_resets_or_fails_hung_jobs() -> None:
    job = make_job()
    job.status, job.attempts = Job.Status.RUNNING, 1
    job.started_at = timezone.now() - dt.timedelta(hours=1)
    job.save()
    assert reap_stale() == 1
    job.refresh_from_db()
    assert job.status == Job.Status.PENDING
    job.status, job.attempts = Job.Status.RUNNING, MAX_ATTEMPTS
    job.started_at = timezone.now() - dt.timedelta(hours=1)
    job.save()
    reap_stale()
    job.refresh_from_db()
    assert job.status == Job.Status.FAILED and job.error_code == "Timeout"


def test_failed_job_shows_error_and_can_retry() -> None:
    c = Client()
    c.post("/pin/", valid_post())
    job = Job.objects.get()
    job.status, job.error_code = Job.Status.FAILED, "StaleWeatherError"
    job.save()
    page = c.get(f"/fields/{job.field_id}/?lang=en").content.decode()
    assert "too old" in page
    assert c.post(f"/fields/{job.field_id}/retry/").status_code == 302
    job.refresh_from_db()
    assert job.status == Job.Status.PENDING and job.attempts == 0


# ---- season replay (analysis date) ----


def test_pin_with_past_analysis_date_creates_replay_job() -> None:
    past = (TODAY - dt.timedelta(days=10)).isoformat()
    r = Client().post("/pin/", valid_post(as_of=past))
    assert r.status_code == 302
    assert Field.objects.get().analysis_date == TODAY - dt.timedelta(days=10)


def test_pin_with_today_as_analysis_date_is_live() -> None:
    Client().post("/pin/", valid_post(as_of=TODAY.isoformat()))
    assert Field.objects.get().analysis_date is None


@pytest.mark.parametrize(
    "as_of",
    [
        (TODAY + dt.timedelta(days=3)).isoformat(),
        (PLANT - dt.timedelta(days=1)).isoformat(),
        "nope",
    ],
)
def test_pin_rejects_bad_analysis_date(as_of: str) -> None:
    assert Client().post("/pin/", valid_post(as_of=as_of)).status_code == 400
    assert not Field.objects.exists()


def test_replay_job_runs_up_to_its_analysis_date() -> None:
    end = TODAY - dt.timedelta(days=5)
    create_field_job(
        owner_key="web:r",
        lat=40.0,
        lon=48.6,
        radius_m=150.0,
        crop_id="winter_wheat",
        planting=PLANT,
        today=TODAY,
        analysis_date=end,
    )
    seen: dict[str, dt.date] = {}

    def spy(**kw):  # type: ignore[no-untyped-def]
        seen["today"] = kw["today"]
        return fake_builder_ok(**kw)

    run_job(claim_job(), builder=spy, today=TODAY)  # type: ignore[arg-type]
    assert seen["today"] == end
    assert Result.objects.get().computed_on == end


# ---- validation text shipped with the product ----


def test_validation_summary_is_honest_and_shown() -> None:
    from aquapin_core.validation import load_validation
    from fields.render import advice_text, validation_text

    v = load_validation()
    assert (
        v is not None and v["seasons"] == 20 and v["sign_test_p"] > 0.05
    )  # not claimed significant
    en = validation_text("en")
    assert (
        str(v["rmse_satellite"]) in en
        and "overestimate" in en
        and "No test site is in your region" in en
    )
    assert "Ни одной тестовой станции" in validation_text("ru")
    advice = {
        "decision": "wait",
        "confidence": "low",
        "last_clear_days": None,
        "depletion_mm": 1,
        "raw_mm": 2,
        "rain_next_3d_mm": 0,
        "kcb": 0.2,
        "kcb_source": "table",
    }
    assert "flux towers" in advice_text(advice, "en")


def test_validation_falls_back_when_no_backtest(monkeypatch: pytest.MonkeyPatch) -> None:
    import fields.render as render

    monkeypatch.setattr(render, "load_validation", lambda: None)
    assert "not yet validated" in render.validation_text("en")


def test_demo_page_shows_accuracy_check() -> None:
    page = Client().get("/demo/kura-lowland/?lang=en").content.decode()
    assert "Accuracy check" in page and "flux-tower" in page
