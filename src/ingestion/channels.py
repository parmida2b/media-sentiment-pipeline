"""
channels.py — helper for iterating the categorized YouTube channel registry
(Parmida)

The registry itself lives in config/config.yaml (youtube.channels /
youtube.channel_priority_order), not here, so switching config.yaml's topic
is the ONE place that needs editing — this module is just a pure iteration
helper over whatever registry gets passed in.
"""


def iter_channels(registry: dict, priority_order: list[str]):
    """Yield (category, channel_dict) in priority_order, then any remaining
    categories in registry not mentioned in priority_order."""
    seen = set()
    for category in priority_order:
        seen.add(category)
        for channel in registry.get(category, []):
            yield category, channel
    for category, channel_list in registry.items():
        if category in seen:
            continue
        for channel in channel_list:
            yield category, channel
