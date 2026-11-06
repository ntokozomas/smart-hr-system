from .metrics import number

WIDTH = 640
HEIGHT = 240
LEFT = 44
RIGHT = 12
TOP = 16
BOTTOM = 28


def nice_max(value):
    if value <= 0:
        return 1
    magnitude = 1
    while magnitude * 10 <= value:
        magnitude *= 10
    while magnitude > value:
        magnitude /= 10
    for step in (1, 2, 2.5, 5, 10):
        if value <= step * magnitude:
            return step * magnitude
    return 10 * magnitude


def _round(value):
    return round(value, 1)


def bar_chart(labels, series, unit=""):
    plot_width = WIDTH - LEFT - RIGHT
    plot_height = HEIGHT - TOP - BOTTOM
    baseline = TOP + plot_height
    totals = [sum(item["values"][index] for item in series) for index in range(len(labels))]
    top_value = nice_max(max(totals, default=0))
    slot = plot_width / max(len(labels), 1)
    bar_width = min(slot * 0.6, 56)

    bars = []
    for index, label in enumerate(labels):
        x = LEFT + slot * index + (slot - bar_width) / 2
        y = baseline
        segments = []
        for item in series:
            value = item["values"][index]
            height = plot_height * value / top_value
            y -= height
            if value:
                segments.append(
                    {
                        "x": _round(x),
                        "y": _round(y),
                        "width": _round(bar_width),
                        "height": _round(height),
                        "css": item["css"],
                        "title": f"{item['name']}, {label}: {number(value)}{unit}",
                    }
                )
        bars.append(
            {
                "label": label,
                "label_x": _round(x + bar_width / 2),
                "total": number(totals[index]) + unit,
                "total_y": _round(y - 5),
                "segments": segments,
            }
        )

    ticks = [
        {"y": _round(baseline - plot_height * step / 4), "label": number(top_value * step / 4)}
        for step in range(5)
    ]
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "left": LEFT,
        "right": WIDTH - RIGHT,
        "label_y": HEIGHT - 8,
        "bars": bars,
        "ticks": ticks,
        "legend": [{"name": item["name"], "css": item["css"]} for item in series]
        if len(series) > 1
        else [],
        "empty": not any(totals),
    }


def leave_chart(report):
    labels = [row["month"].strftime("%b %y") for row in report.months]
    series = [
        {
            "name": name,
            "css": f"bar-{name.lower()}",
            "values": [row["bucket"].leave[name] for row in report.months],
        }
        for name in ("Annual", "Sick", "Family")
    ]
    return bar_chart(labels, series)


def absenteeism_chart(report):
    labels = [row["month"].strftime("%b %y") for row in report.months]
    series = [
        {
            "name": "Absenteeism",
            "css": "bar-absent",
            "values": [row["bucket"].absenteeism for row in report.months],
        }
    ]
    return bar_chart(labels, series, unit="%")
