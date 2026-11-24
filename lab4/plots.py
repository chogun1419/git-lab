"""Turn numeric series into SVG polyline geometry.

The page has no JavaScript, so charts are drawn as inline SVG whose point
strings are computed here. This module is pure geometry: no Flask, no styling
decisions, no unit formatting (labels are formatted by the route).
"""

import math

DEFAULT_PADDING = (58.0, 14.0, 18.0, 34.0)


def _x_mapper(low: float, high: float, left: float, span: float, scale: str):
    if high <= low:
        return lambda value: left
    if scale == "log":
        low, high = math.log10(low), math.log10(high)
        return lambda value: left + span * (math.log10(value) - low) / (high - low)
    return lambda value: left + span * (value - low) / (high - low)


def _decade_ticks(low: float, high: float) -> list[float]:
    start = math.ceil(math.log10(low) - 1e-9)
    stop = math.floor(math.log10(high) + 1e-9)
    ticks = [10.0**power for power in range(start, stop + 1)]
    if len(ticks) < 2:
        return [low, high]
    return ticks


def _linear_ticks(low: float, high: float, count: int = 5) -> list[float]:
    if high <= low:
        return [low]
    return [low + (high - low) * index / (count - 1) for index in range(count)]


def build_chart(
    series: list[list[float]],
    x_values: list[float],
    x_scale: str = "linear",
    width: float = 660.0,
    height: float = 240.0,
    padding: tuple[float, float, float, float] = DEFAULT_PADDING,
    y_ticks: int = 4,
) -> dict:
    """Return polylines and tick positions for an inline SVG chart.

    ``padding`` is ``(left, top, right, bottom)`` in SVG user units. ``series``
    may hold several curves that share one x axis.
    """
    if not series or not x_values:
        raise ValueError("chart needs at least one series and one x value.")
    if any(len(values) != len(x_values) for values in series):
        raise ValueError("every series must be as long as the x values.")
    if any(value <= 0 for value in x_values) and x_scale == "log":
        raise ValueError("a log axis needs strictly positive x values.")

    left, top, right, bottom = padding
    plot_width = max(width - left - right, 1.0)
    plot_height = max(height - top - bottom, 1.0)

    finite = [value for values in series for value in values if math.isfinite(value)]
    if not finite:
        raise ValueError("chart needs at least one finite value.")

    low, high = min(finite), max(finite)
    if high <= low:
        low, high = low - 1.0, high + 1.0
    pad = (high - low) * 0.08
    low, high = low - pad, high + pad

    map_x = _x_mapper(min(x_values), max(x_values), left, plot_width, x_scale)
    map_y = lambda value: top + plot_height * (high - value) / (high - low)

    polylines = []
    for values in series:
        pairs = [
            f"{map_x(x):.2f},{map_y(y):.2f}"
            for x, y in zip(x_values, values)
            if math.isfinite(y)
        ]
        polylines.append(" ".join(pairs))

    if x_scale == "log":
        tick_values = _decade_ticks(min(x_values), max(x_values))
    else:
        tick_values = _linear_ticks(min(x_values), max(x_values))

    y_tick_values = [
        low + (high - low) * index / (y_ticks - 1) for index in range(y_ticks)
    ]

    return {
        "width": width,
        "height": height,
        "left": left,
        "top": top,
        "plot_width": plot_width,
        "plot_height": plot_height,
        "polylines": polylines,
        "x_ticks": [{"value": value, "x": map_x(value)} for value in tick_values],
        "y_ticks": [
            {"value": value, "y": map_y(value)}
            for value in reversed(y_tick_values)
        ],
        "y_min": low,
        "y_max": high,
    }
