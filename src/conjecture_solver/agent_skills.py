"""Expose shipped research skills consistently to API and native CLI agents."""

from .mvp_skills import discover_builtin_mvp_resources


def research_skills():
    return discover_builtin_mvp_resources()[0]


def skill_context():
    catalogue = research_skills()
    lines = [
        "AVAILABLE SIMJECTURE RESEARCH SKILLS",
        "Before operating a scientific tool, read the relevant SKILL.md and only the linked "
        "references needed for the task. Reuse its examples and documented interfaces instead "
        "of rediscovering the integration from host source code.",
        "Native CLI agents: read the absolute paths below with your file tools. "
        "Built-in API agents: call read_skill(name, path='SKILL.md'); "
        "pass a relative reference/example path to read further resources.",
        "A skill is documentation, not proof of installation or scientific qualification. "
        "Use the installed capability's actual name and build; examples may describe a "
        "different build. For an interactive demonstration, keep preparation proportionate, "
        "run a bounded exploratory case, and report limitations. Independent evidence "
        "requirements apply when claiming validated research results.",
    ]
    for descriptor in catalogue.descriptors():
        path = catalogue.root / descriptor["name"] / descriptor["entrypoint"]
        lines.append(f"- {descriptor['name']}: {descriptor['description']}\n  {path}")
    return "\n".join(lines)
