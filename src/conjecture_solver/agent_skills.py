"""Expose shipped research skills consistently to API and native CLI agents."""

from pathlib import Path

from .mvp_skills import MVPSkillCatalog


def research_skills():
    # Installation guidance must remain readable while a runtime is incomplete.
    # Loading documentation must not validate unrelated capability executables.
    package = Path(__file__).resolve().parent
    bundled = package / "builtin_skills"
    return MVPSkillCatalog.discover(bundled if bundled.is_dir() else package.parents[1] / "skills")


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
