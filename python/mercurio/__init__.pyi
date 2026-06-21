from typing import Any

from .authoring import ModelBuilder
from .runtime import Model
from .session import (
    AnalysisQuery,
    CellRunReport,
    CompiledModel,
    PartDefRef,
    PartUsageRef,
    ProjectSession,
    SemanticRef,
    SemanticQuery,
    SimulationConfiguration,
    SmallEdit,
    StaleSemanticRefError,
    TradeStudy,
    TransactionBuilder,
    Variant,
    VariantBaseChangedError,
)

__version__: str

def open(
    path: str,
    *,
    executable: str | None = None,
    timeout: float = 60.0,
) -> Model: ...

def open_project(
    path: str,
    *,
    validate: bool = True,
) -> ProjectSession: ...

def __getattr__(name: str) -> Any: ...

__all__: list[str]
