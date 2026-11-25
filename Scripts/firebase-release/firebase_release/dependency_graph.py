"""Which xcframeworks each SDK of the Firebase zip needs, as published in its METADATA.md."""
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

_SECTION = re.compile(r"^## (?P<name>\S+)(?: \(~> (?P<requires>\S+)\))?\s*$")
_FRAMEWORK = re.compile(r"^- (?P<name>\S+)\.xcframework\s*$")


class UnknownSdk(KeyError):
    def __str__(self) -> str:
        return self.args[0]


@dataclass(frozen=True)
class SdkSpec:
    name: str
    frameworks: Tuple[str, ...]
    requires: Optional[str]


class DependencyGraph:
    def __init__(self, sdks: Dict[str, SdkSpec]):
        self._sdks = sdks

    def sdk_names(self) -> Tuple[str, ...]:
        return tuple(self._sdks)

    def frameworks_for(self, sdk: str) -> Tuple[str, ...]:
        frameworks = set()
        current: Optional[str] = sdk
        while current is not None:
            spec = self._spec(current)
            frameworks.update(spec.frameworks)
            current = spec.requires
        return tuple(sorted(frameworks))

    def _spec(self, sdk: str) -> SdkSpec:
        if sdk not in self._sdks:
            raise UnknownSdk(f"Unknown SDK '{sdk}'. Available: {', '.join(self._sdks)}")
        return self._sdks[sdk]


def parse_metadata(text: str) -> DependencyGraph:
    sections: Dict[str, Tuple[Optional[str], list]] = {}
    current = None
    for line in text.splitlines():
        section = _SECTION.match(line)
        if section:
            current = section["name"]
            sections[current] = (section["requires"], [])
            continue
        framework = _FRAMEWORK.match(line)
        if framework and current is not None:
            sections[current][1].append(framework["name"])
    return DependencyGraph({
        name: SdkSpec(name=name, frameworks=tuple(frameworks), requires=requires)
        for name, (requires, frameworks) in sections.items()
        if frameworks
    })
