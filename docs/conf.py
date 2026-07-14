project = "Mercurio Python SDK"
author = "Mercurio Contributors"

extensions = ["myst_parser"]

source_suffix = {
    ".md": "markdown",
}
exclude_patterns = ["_build"]
templates_path: list[str] = []

html_theme = "furo"
html_title = "Mercurio Python SDK"
html_static_path: list[str] = []

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
]
nitpicky = True
