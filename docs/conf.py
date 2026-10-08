from __future__ import annotations

import tomllib
from pathlib import Path

project = "Simjecture"
author = "Bowen Zhu"
copyright = "2026, Bowen Zhu and contributors"
release = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())[
    "project"
]["version"]

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]

root_doc = "index"
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 3

exclude_patterns = [
    "_build",
]

autosummary_generate = True
autodoc_typehints = "description"

html_theme = "furo"
html_title = "Simjecture"
html_baseurl = "https://drawingsword.com/simjecture/"
html_favicon = "../src/conjecture_solver/web/static/brand/favicon.svg"
html_theme_options = {
    "light_logo": "simjecture-lockup-light.svg",
    "dark_logo": "simjecture-lockup-dark.svg",
    "sidebar_hide_name": True,
    "source_repository": "https://github.com/tomzhu0225/simjecture/",
    "source_branch": "main",
    "source_directory": "docs/",
    "top_of_page_buttons": ["view", "edit"],
    "light_css_variables": {
        "color-brand-primary": "#6658d9",
        "color-brand-content": "#5443bb",
        "color-background-primary": "#ffffff",
        "color-background-secondary": "#f7f7fb",
        "color-foreground-primary": "#202332",
        "font-stack": (
            "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "
            "'Segoe UI', sans-serif"
        ),
    },
    "dark_css_variables": {
        "color-brand-primary": "#b5a7ff",
        "color-brand-content": "#c5baff",
        "color-background-primary": "#14151e",
        "color-background-secondary": "#1a1c27",
        "color-foreground-primary": "#efedf8",
    },
}

html_context = {
    "github_user": "tomzhu0225",
    "github_repo": "simjecture",
    "github_version": "main",
    "doc_path": "docs",
}

html_static_path = ["_static", "../src/conjecture_solver/web/static/brand"]
html_css_files = ["docs.css"]
templates_path = ["_templates"]
html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/project-links.html",
        "sidebar/navigation.html",
        "sidebar/ethical-ads.html",
        "sidebar/scroll-end.html",
    ],
}
