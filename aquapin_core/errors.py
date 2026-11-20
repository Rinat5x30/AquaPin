"""Typed errors. Catch-all handlers are banned; catch these by name."""


class AquaPinError(Exception):
    """Base class for all expected AquaPin failures."""


class GeometryError(AquaPinError):
    """Point or radius is invalid (out of range, too large)."""


class StacSearchError(AquaPinError):
    """Satellite catalogue search failed (timeout, 429, 5xx, bad payload)."""


class SatelliteReadError(AquaPinError):
    """Reading a raster window from a satellite asset failed."""


class NoClearObservationError(AquaPinError):
    """No usable cloud-free observation in the requested period."""


class WeatherApiError(AquaPinError):
    """Weather provider failed (timeout, 429, malformed JSON)."""


class StaleWeatherError(WeatherApiError):
    """Weather data is too old to give honest advice."""


class CropParamsError(AquaPinError):
    """Unknown crop id or crop parameters without a source."""
