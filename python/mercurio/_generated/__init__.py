"""Generated typed Mercurio metamodel facades."""

from .base import ElementFacade, ElementView
from .facades import (
    METAMODEL_CLASSES,
    METAMODEL_CLASS_BY_KIND,
    METAMODEL_CLASS_BY_METATYPE,
    class_for,
    facade,
    wrap,
)

__all__ = [
    "ElementFacade",
    "ElementView",
    "METAMODEL_CLASSES",
    "METAMODEL_CLASS_BY_KIND",
    "METAMODEL_CLASS_BY_METATYPE",
    "class_for",
    "facade",
    "wrap",
]

for _cls in METAMODEL_CLASSES:
    globals().setdefault(_cls.__name__, _cls)
    if _cls.__name__ not in __all__:
        __all__.append(_cls.__name__)
if METAMODEL_CLASSES:
    del _cls
