from __future__ import annotations

project = "Simjecture"
author = "Bowen Zhu"
copyright = "2026, Bowen Zhu and contributors"
release = "0.2.2"

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

exclude_patterns = [
    "_build",
]

autosummary_generate = True
autodoc_typehints = "description"

html_theme = "pydata_sphinx_theme"
html_title = f"{project} {release}"
html_theme_options = {
    "github_url": "https://github.com/tomzhu0225/simjecture",
    "show_toc_level": 2,
    "navigation_depth": 3,
    "collapse_navigation": True,
    "icon_links": [
        {
            "name": "Repository",
            "url": "https://github.com/tomzhu0225/simjecture",
            "icon": "fa-brands fa-github",
        }
    ],
}

html_context = {
    "github_user": "tomzhu0225",
    "github_repo": "simjecture",
    "github_version": "main",
    "doc_path": "docs",
}

html_static_path = ["_static"]
