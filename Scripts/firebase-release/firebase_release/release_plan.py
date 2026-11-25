"""Decides which SPM products and binary targets a release exposes. Pure: no I/O."""
from dataclasses import dataclass
from typing import Iterable, Tuple

from .dependency_graph import DependencyGraph

UMBRELLA_TARGET = "Firebase"
_FIREBASE_MARKER = "FirebaseCore"


@dataclass(frozen=True)
class ExternalBinary:
    """A binary Google hosts outside the Firebase zip (e.g. GoogleTagManager)."""
    name: str
    url: str
    checksum: str


@dataclass(frozen=True)
class ExternalProduct:
    name: str
    binary: ExternalBinary
    requires_sdk: str


@dataclass(frozen=True)
class SourceTarget:
    """A target with Swift sources in this repo that builds on some SDKs."""
    name: str
    sdks: Tuple[str, ...]


@dataclass(frozen=True)
class PlannedProduct:
    name: str
    targets: Tuple[str, ...]


@dataclass(frozen=True)
class PlannedSourceTarget:
    name: str
    dependencies: Tuple[str, ...]


@dataclass(frozen=True)
class ReleasePlan:
    products: Tuple[PlannedProduct, ...]
    source_targets: Tuple[PlannedSourceTarget, ...]
    binaries: Tuple[str, ...]
    external_binaries: Tuple[ExternalBinary, ...]

    @property
    def needs_umbrella(self) -> bool:
        return _FIREBASE_MARKER in self.binaries


def plan_release(
    graph: DependencyGraph,
    sdks: Iterable[str],
    external_products: Iterable[ExternalProduct] = (),
    source_targets: Iterable[SourceTarget] = (),
) -> ReleasePlan:
    binaries = set()

    def targets_for(sdk_names: Iterable[str]) -> Tuple[str, ...]:
        frameworks = sorted({framework for sdk in sdk_names for framework in graph.frameworks_for(sdk)})
        binaries.update(frameworks)
        umbrella = (UMBRELLA_TARGET,) if _FIREBASE_MARKER in frameworks else ()
        return umbrella + tuple(frameworks)

    products = [PlannedProduct(name=sdk, targets=targets_for([sdk])) for sdk in sdks]
    externals = list(external_products)
    products += [
        PlannedProduct(name=external.name, targets=targets_for([external.requires_sdk]) + (external.binary.name,))
        for external in externals
    ]
    planned_sources = [
        PlannedSourceTarget(name=source.name, dependencies=targets_for(source.sdks)) for source in source_targets
    ]
    return ReleasePlan(
        products=tuple(products),
        source_targets=tuple(planned_sources),
        binaries=tuple(sorted(binaries)),
        external_binaries=tuple(external.binary for external in externals),
    )
