"""Small dictionary-based EN/RU strings (no gettext toolchain needed)."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

LANGS = ("en", "ru")

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title": "How much water does this field need today",
        "tagline": "From Sentinel-2 satellite images and weather. Example season replay, real data.",
        "example": "Example",
        "pin_own": "Pin your own field",
        "today": "Today",
        "irrigate": "Irrigate",
        "wait": "No irrigation needed",
        "mm_line": "{mm} mm (about {m3} m3 per hectare)",
        "confidence": "Confidence",
        "conf_high": "high",
        "conf_medium": "medium",
        "conf_low": "low",
        "conf_reason": "Last clear satellite image {age} days ago",
        "conf_reason_none": "No clear satellite image yet; calculated from weather only",
        "why": "Why this advice",
        "why_kcb": "Crop coefficient (Kcb)",
        "why_src_sat": "from satellite NDVI",
        "why_src_table": "from the FAO-56 table",
        "why_dr": "Water deficit in root zone",
        "why_raw": "Irrigate when deficit reaches",
        "why_rain": "Rain forecast, next 3 days",
        "why_ver": "Calculation version",
        "why_validation": "Accuracy against measured data: not yet validated",
        "assumptions": "Assumptions",
        "season": "Season",
        "play": "Play",
        "pause": "Pause",
        "legend": "NDVI (vegetation greenness)",
        "legend_low": "bare / dry",
        "legend_high": "dense green",
        "no_image": "No clear image yet",
        "summary": "{date}: NDVI {ndvi}. Deficit {dr} mm of {raw} mm allowed. Rain {rain} mm, evaporation {et0} mm.",
        "chart_legend": "Black line: water deficit. Dashed: deficit at which irrigation is advised. Bars: rain. Blue ticks: irrigation days.",
        "table_title": "Observations table",
        "pin_title": "Pin a field",
        "pin_help": "Click the map to place the field centre, then set the radius.",
        "lat": "Latitude",
        "lon": "Longitude",
        "radius": "Field radius, m",
        "planting": "Planting date",
        "crop": "Crop",
        "consent": "I agree that AquaPin stores this location to calculate advice. I can delete it at any time.",
        "submit": "Calculate",
        "loading": "Calculating. Weather is first, satellite images follow.",
        "failed": "We could not calculate this field right now.",
        "retry": "Try again",
        "delete": "Delete this field",
        "language": "Language",
        "err_StaleWeatherError": "Weather data is too old to give honest advice. Try again later.",
        "err_StacSearchError": "The satellite catalogue did not answer. Try again later.",
        "err_GeometryError": "The location or radius is not valid.",
        "err_default": "Something went wrong. Try again later.",
        "offline_demo": "Offline example",
        "frame_age": "Image from {date}",
        "basemap": "Basemap: Sentinel-2 true colour, open data (Copernicus).",
        "replay_note": "This replay uses every image of the season. Live advice uses only past images.",
        "tiles_note": "Picker map: Esri satellite imagery or OpenStreetMap contributors (needs internet).",
        "validation_title": "Accuracy check",
        "validation_line": "Checked against flux-tower measurements ({seasons} wheat seasons, {sites} sites in Europe and China): evaporation error {rmse} mm/day, versus {rmse_tab} for the FAO-56 table curve. Clearly better in irrigated China ({china} vs {china_tab}); no better than the table in rainfed Europe ({eu} vs {eu_tab}). The model tends to overestimate evaporation by about {b_lo} to {b_hi}%, so advice can come early. No test site is in your region.",
        "validation_short": "Checked against flux towers: evaporation error about {rmse} mm/day; the model tends to overestimate evaporation by {b_lo} to {b_hi}%.",
        "as_of": "Calculate up to date",
        "as_of_help": "Today gives live advice. A past date replays the season up to that day (shows irrigation days).",
        "events": "Irrigation advised on",
        "events_none": "No irrigation was advised in this period (enough rain for the assumed soil).",
        "map_satellite": "Satellite",
        "map_streets": "Map",
    },
    "ru": {
        "title": "Сколько воды нужно этому полю сегодня",
        "tagline": "По спутниковым снимкам Sentinel-2 и погоде. Повтор сезона на реальных данных.",
        "example": "Пример",
        "pin_own": "Поставить свой пин",
        "today": "Сегодня",
        "irrigate": "Полив",
        "wait": "Полив не нужен",
        "mm_line": "{mm} мм (около {m3} м³ на гектар)",
        "confidence": "Уверенность",
        "conf_high": "высокая",
        "conf_medium": "средняя",
        "conf_low": "низкая",
        "conf_reason": "Последний чистый снимок {age} дн. назад",
        "conf_reason_none": "Чистого снимка пока нет, считаем только по погоде",
        "why": "Почему этот совет",
        "why_kcb": "Коэффициент культуры (Kcb)",
        "why_src_sat": "по спутниковому NDVI",
        "why_src_table": "из таблицы FAO-56",
        "why_dr": "Дефицит воды в корнях",
        "why_raw": "Полив, когда дефицит достигает",
        "why_rain": "Дождь в прогнозе, 3 дня",
        "why_ver": "Версия расчёта",
        "why_validation": "Точность по измеренным данным: ещё не проверена",
        "assumptions": "Допущения",
        "season": "Сезон",
        "play": "Играть",
        "pause": "Пауза",
        "legend": "NDVI (зелёность растительности)",
        "legend_low": "голо / сухо",
        "legend_high": "густая зелень",
        "no_image": "Чистого снимка пока нет",
        "summary": "{date}: NDVI {ndvi}. Дефицит {dr} мм из допустимых {raw} мм. Дождь {rain} мм, испарение {et0} мм.",
        "chart_legend": "Чёрная линия: дефицит воды. Пунктир: дефицит, при котором советуем полив. Столбики: дождь. Синие метки: дни полива.",
        "table_title": "Таблица наблюдений",
        "pin_title": "Поставить пин",
        "pin_help": "Нажмите на карту, чтобы задать центр поля, затем радиус.",
        "lat": "Широта",
        "lon": "Долгота",
        "radius": "Радиус поля, м",
        "planting": "Дата посева",
        "crop": "Культура",
        "consent": "Я согласен, что AquaPin хранит это место для расчёта совета. Я могу удалить его в любой момент.",
        "submit": "Рассчитать",
        "loading": "Считаем. Сначала погода, потом спутниковые снимки.",
        "failed": "Не удалось рассчитать это поле сейчас.",
        "retry": "Повторить",
        "delete": "Удалить это поле",
        "language": "Язык",
        "err_StaleWeatherError": "Данные о погоде устарели, честный совет дать нельзя. Попробуйте позже.",
        "err_StacSearchError": "Каталог спутниковых снимков не ответил. Попробуйте позже.",
        "err_GeometryError": "Место или радиус указаны неверно.",
        "err_default": "Что-то пошло не так. Попробуйте позже.",
        "offline_demo": "Офлайн-пример",
        "frame_age": "Снимок от {date}",
        "basemap": "Подложка: Sentinel-2 в естественных цветах, открытые данные (Copernicus).",
        "replay_note": "Повтор использует все снимки сезона. Живой совет использует только прошлые.",
        "tiles_note": "Карта выбора точки: спутниковые снимки Esri или участники OpenStreetMap (нужен интернет).",
        "validation_title": "Проверка точности",
        "validation_line": "Проверено по измерениям потоковых башен ({seasons} сезонов пшеницы, {sites} станций в Европе и Китае): ошибка испарения {rmse} мм/день против {rmse_tab} у табличной кривой FAO-56. Заметно лучше в орошаемом Китае ({china} против {china_tab}); не лучше таблицы в Европе без орошения ({eu} против {eu_tab}). Модель склонна завышать испарение примерно на {b_lo}-{b_hi}%, поэтому совет может приходить раньше нужного. Ни одной тестовой станции в вашем регионе нет.",
        "validation_short": "Проверено по потоковым башням: ошибка испарения около {rmse} мм/день; модель склонна завышать испарение на {b_lo}-{b_hi}%.",
        "as_of": "Считать до даты",
        "as_of_help": "Сегодня даёт живой совет. Прошлая дата повторяет сезон до этого дня (видны дни полива).",
        "events": "Полив советовали",
        "events_none": "За этот период полив не советовали (дождей хватало для принятой почвы).",
        "map_satellite": "Спутник",
        "map_streets": "Карта",
    },
}


def lang_for(request: HttpRequest) -> str:
    requested = request.GET.get("lang")
    if requested in LANGS:
        request.session["lang"] = requested
        return requested
    stored = request.session.get("lang")
    if stored in LANGS:
        return str(stored)
    accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    return "ru" if accept.lower().startswith("ru") else "en"


def tr(lang: str, key: str, **kwargs: Any) -> str:
    table = STRINGS.get(lang, STRINGS["en"])
    text = table.get(key) or STRINGS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text


def error_text(lang: str, error_code: str) -> str:
    table = STRINGS.get(lang, STRINGS["en"])
    return table.get(f"err_{error_code}") or table["err_default"]
