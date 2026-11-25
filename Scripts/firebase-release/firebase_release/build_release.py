"""Use case: turn a Firebase distribution into this package's files for one Firebase version."""
import pathlib
import shutil
from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Tuple

try:
    from typing import Protocol
except ImportError:  # pragma: no cover - Python < 3.8
    Protocol = object

from .dependency_graph import parse_metadata
from .manifest import UMBRELLA_PATH, ArtifactSource, ManifestSettings, render_manifest
from .release_plan import ExternalProduct, ReleasePlan, SourceTarget, plan_release

CRASHLYTICS_TOOLS_PATH = "Tools/Crashlytics"
_CRASHLYTICS = "FirebaseCrashlytics"


class Distribution(Protocol):
    metadata: str
    umbrella_header: pathlib.Path
    crashlytics_tools: List[pathlib.Path]

    def extract_frameworks(self, names: Iterable[str]) -> Mapping[str, pathlib.Path]: ...


class ArtifactStore(Protocol):
    def store(self, frameworks: Mapping[str, pathlib.Path]) -> ArtifactSource: ...


@dataclass(frozen=True)
class ReleaseConfig:
    sdks: Tuple[str, ...]
    settings: ManifestSettings
    external_products: Tuple[ExternalProduct, ...] = field(default_factory=tuple)
    source_targets: Tuple[SourceTarget, ...] = field(default_factory=tuple)


def build_release(distribution: Distribution, store: ArtifactStore, package_root: pathlib.Path,
                  config: ReleaseConfig) -> ReleasePlan:
    package_root = pathlib.Path(package_root)
    plan = plan_release(parse_metadata(distribution.metadata), config.sdks,
                        config.external_products, config.source_targets)
    artifacts = store.store(distribution.extract_frameworks(plan.binaries))

    umbrella_dir = _reset(package_root / UMBRELLA_PATH)
    if plan.needs_umbrella:
        _install_umbrella(distribution.umbrella_header, umbrella_dir)
    tools_dir = _reset(package_root / CRASHLYTICS_TOOLS_PATH)
    if _CRASHLYTICS in plan.binaries:
        _install_tools(distribution.crashlytics_tools, tools_dir)
    (package_root / "Package.swift").write_text(render_manifest(plan, artifacts, config.settings))
    return plan


def _reset(directory: pathlib.Path) -> pathlib.Path:
    """Generated directories are rebuilt from scratch so files of an older version never linger."""
    if directory.exists():
        shutil.rmtree(directory)
    return directory


def _install_umbrella(header: pathlib.Path, target: pathlib.Path) -> None:
    (target / "include").mkdir(parents=True)
    shutil.copy2(header, target / "include" / "Firebase.h")
    (target / "Firebase.c").write_text("// Anchor so SPM builds the Firebase umbrella target (Firebase.h).\n")


def _install_tools(tools: Iterable[pathlib.Path], target: pathlib.Path) -> None:
    target.mkdir(parents=True)
    for tool in tools:
        shutil.copy2(tool, target / tool.name)
