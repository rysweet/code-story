"""Sphinx configuration for Code Story documentation."""

import os
import sys
from datetime import datetime

# Add project root to path for autodoc extension
sys.path.insert(0, os.path.abspath(".."))

# Project information
project = "Code Story"
copyright = f"{datetime.now().year}, Code Story Team"
author = "Code Story Team"
release = "0.1.0"

# General configuration
extensions = [
    # Core Sphinx extensions
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",  # Support for Google and NumPy style docstrings
    "sphinx.ext.githubpages",
    # Markdown support
    "myst_parser",  # Markdown support
    # Additional extensions
    "sphinxcontrib.mermaid",  # Diagrams
    "sphinx_copybutton",  # Copy button for code blocks
    "sphinx_design",  # UI components
    "sphinx_tabs.tabs",  # Tabbed content
]

# Auto-generate API documentation settings
autoclass_content = "both"  # Include both class and __init__ docstrings
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"

# Napoleon settings (for Google style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_attr_annotations = True

# MyST parser settings for Markdown
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "html_admonition",
    "html_image",
    "linkify",  # Re-enabled after adding linkify-it-py to dependencies
    "replacements",
    "smartquotes",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 3

# Templates path
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML output settings
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = "Code Story Documentation"
html_logo = None  # Add a logo image path if available
html_favicon = None  # Add a favicon path if available

# Add custom CSS
html_css_files = [
    "custom.css",
]

# Theme options
html_theme_options = {
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
    "style_nav_header_background": "#2c3e50",
    # Toc options
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
}

# Copybutton settings
copybutton_selector = "div:not(.no-copy)>div.highlight pre"
copybutton_prompt_text = r">>> |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# File type support
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
