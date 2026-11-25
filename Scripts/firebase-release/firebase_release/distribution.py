"""Reads the official Firebase.zip (https://firebase.google.com/docs/ios/installation-methods#integrate-manually).

Extraction uses `unzip`, which keeps the symlinks and permissions the signed xcframeworks rely on.
"""
import pathlib
import re
import subprocess
import zipfile
from typing import Dict, Iterable, List, Tuple

_ROOT = "Firebase"
_METADATA = f"{_ROOT}/METADATA.md"
_UMBRELLA_HEADER = f"{_ROOT}/Firebase.h"
_CRASHLYTICS_TOOLS = (f"{_ROOT}/FirebaseCrashlytics/run", f"{_ROOT}/FirebaseCrashlytics/upload-symbols")
_NESTED_ZIP = re.compile(r"^[^/]+/Firebase-[^/]*\.zip$")
_FRAMEWORK_ENTRY = re.compile(rf"^{_ROOT}/(?P<folder>[^/]+)/(?P<name>[^/]+)\.xcframework/")


class InvalidDistribution(Exception):
    pass


def _unzip(archive: pathlib.Path, patterns: Iterable[str], destination: pathlib.Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(["unzip", "-q", "-o", str(archive), *patterns, "-d", str(destination)], check=True)


class FirebaseDistribution:
    def __init__(self, archive: pathlib.Path, entries: List[str], work_dir: pathlib.Path):
        self._archive = archive
        self._entries = entries
        self._work_dir = work_dir
        self._root = work_dir / _ROOT

    @classmethod
    def open(cls, zip_path: pathlib.Path, work_dir: pathlib.Path) -> "FirebaseDistribution":
        archive = pathlib.Path(zip_path)
        work_dir = pathlib.Path(work_dir)
        if not zipfile.is_zipfile(archive):
            raise InvalidDistribution(f"{archive} is not a zip file (was the download complete?)")
        entries = cls._entries(archive)
        if _METADATA not in entries:
            archive, entries = cls._open_nested(archive, entries, work_dir)
        present = [name for name in (_METADATA, _UMBRELLA_HEADER, *_CRASHLYTICS_TOOLS) if name in entries]
        _unzip(archive, present, work_dir)
        return cls(archive, entries, work_dir)

    @staticmethod
    def _entries(archive: pathlib.Path) -> List[str]:
        with zipfile.ZipFile(archive) as opened:
            return opened.namelist()

    @classmethod
    def _open_nested(cls, archive: pathlib.Path, entries: List[str], work_dir: pathlib.Path
                     ) -> Tuple[pathlib.Path, List[str]]:
        nested = next((entry for entry in entries if _NESTED_ZIP.match(entry)), None)
        if nested is None:
            raise InvalidDistribution(f"{archive} has neither {_METADATA} nor a nested Firebase-*.zip")
        outer = work_dir / "outer"
        _unzip(archive, [nested], outer)
        inner = outer / nested
        inner_entries = cls._entries(inner)
        if _METADATA not in inner_entries:
            raise InvalidDistribution(f"{nested} inside {archive} has no {_METADATA}")
        return inner, inner_entries

    @property
    def metadata(self) -> str:
        return (self._root / "METADATA.md").read_text()

    @property
    def umbrella_header(self) -> pathlib.Path:
        return self._root / "Firebase.h"

    @property
    def crashlytics_tools(self) -> List[pathlib.Path]:
        tools = [self._work_dir / tool for tool in _CRASHLYTICS_TOOLS]
        return [tool for tool in tools if tool.exists()]

    def extract_frameworks(self, names: Iterable[str]) -> Dict[str, pathlib.Path]:
        """Extracts each xcframework once (the zip repeats shared ones in several SDK folders)."""
        folders = self._folders_by_framework()
        names = list(names)
        missing = [name for name in names if name not in folders]
        if missing:
            raise InvalidDistribution(f"Not in {self._archive.name}: {', '.join(missing)}")
        _unzip(self._archive, [f"{_ROOT}/{folders[name]}/{name}.xcframework/*" for name in names], self._work_dir)
        return {name: self._root / folders[name] / f"{name}.xcframework" for name in names}

    def _folders_by_framework(self) -> Dict[str, str]:
        folders: Dict[str, str] = {}
        for entry in sorted(self._entries):
            match = _FRAMEWORK_ENTRY.match(entry)
            if match:
                folders.setdefault(match["name"], match["folder"])
        return folders
