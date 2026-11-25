"""Where the xcframeworks of a release live, and how Package.swift points at them.

LocalArtifactStore: copies them into the package (path binary targets), for building before publishing.
ReleaseArtifactStore: zips them for a GitHub release (url + checksum binary targets), for consumers.
"""
import hashlib
import pathlib
import shutil
import subprocess
from typing import Dict, Mapping

Frameworks = Mapping[str, pathlib.Path]


class MissingChecksum(KeyError):
    def __str__(self) -> str:
        return self.args[0]


class LocalArtifacts:
    def __init__(self, directory: str):
        self._directory = directory

    def binary_target(self, name: str) -> str:
        return f'.binaryTarget(name: "{name}", path: "{self._directory}/{name}.xcframework")'


class LocalArtifactStore:
    def __init__(self, package_root: pathlib.Path, directory: str):
        self._target = pathlib.Path(package_root) / directory
        self._directory = directory

    def store(self, frameworks: Frameworks) -> LocalArtifacts:
        if self._target.exists():
            shutil.rmtree(self._target)
        self._target.mkdir(parents=True)
        for name, source in frameworks.items():
            shutil.copytree(source, self._target / f"{name}.xcframework", symlinks=True)
        return LocalArtifacts(self._directory)


class ReleaseArtifacts:
    def __init__(self, base_url: str, checksums: Mapping[str, str]):
        self._base_url = base_url.rstrip("/")
        self._checksums = dict(checksums)

    def binary_target(self, name: str) -> str:
        if name not in self._checksums:
            raise MissingChecksum(f"No release zip was built for '{name}'")
        return (f'.binaryTarget(name: "{name}", url: "{self._base_url}/{asset_name(name)}", '
                f'checksum: "{self._checksums[name]}")')


class ReleaseArtifactStore:
    def __init__(self, output_dir: pathlib.Path, base_url: str):
        self._output_dir = pathlib.Path(output_dir)
        self._base_url = base_url

    def store(self, frameworks: Frameworks) -> ReleaseArtifacts:
        if self._output_dir.exists():
            shutil.rmtree(self._output_dir)
        self._output_dir.mkdir(parents=True)
        checksums: Dict[str, str] = {}
        for name, source in frameworks.items():
            archive = self._output_dir / asset_name(name)
            # ditto keeps symlinks and puts <name>.xcframework at the zip root, as SPM requires;
            # --norsrc keeps macOS resource forks (__MACOSX/) out of the archive.
            subprocess.run(["ditto", "-c", "-k", "--norsrc", "--keepParent", str(source), str(archive)],
                           check=True)
            checksums[name] = sha256(archive)
        return ReleaseArtifacts(self._base_url, checksums)


def asset_name(framework: str) -> str:
    return f"{framework}.xcframework.zip"


def sha256(path: pathlib.Path) -> str:
    """Same value as `swift package compute-checksum`."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
