"""Explicitly enabled installed Python skills. No model-controlled imports/downloads.

An entry point in wingent.skills supplies register(registry). Enabling native Python
code is an administrator trust decision, NOT a sandbox or an action approval.
"""

from importlib.metadata import entry_points


def load_skills(registry, enabled=()):
    enabled = tuple(enabled)
    if len(set(enabled)) != len(enabled):
        raise ValueError('Duplicate enabled skill names.')
    candidates = entry_points(group='wingent.skills') if enabled else []
    loaded = []
    for name in enabled:
        matches = [entry for entry in candidates if entry.name == name]
        if len(matches) != 1:
            raise ValueError(f'Enabled skill must have exactly one installed entry point: {name}')
        # Stage registrations; no partial registry mutation if a plugin fails or replaces tools.
        from app.tools import ToolRegistry
        staged = ToolRegistry()
        staged.tools = registry.tools.copy()
        staged.capabilities = registry.capabilities.copy()
        matches[0].load()(staged)
        if any(staged.tools.get(key) is not value for key, value in registry.tools.items()):
            raise ValueError(f'Skill attempted to replace an existing tool: {name}')
        registry.tools = staged.tools
        registry.capabilities = staged.capabilities
        loaded.append(name)
    return loaded
