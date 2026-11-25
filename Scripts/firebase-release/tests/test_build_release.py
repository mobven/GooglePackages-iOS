import os
import pathlib
import tempfile
import unittest

from firebase_release.build_release import ReleaseConfig, build_release
from firebase_release.manifest import ManifestSettings
from firebase_release.release_plan import ExternalBinary, ExternalProduct, SourceTarget

METADATA = """\
## FirebaseAnalytics
- FirebaseCore.xcframework

## FirebaseCrashlytics (~> FirebaseAnalytics)
- FirebaseCrashlytics.xcframework

## GoogleSignIn
- GoogleSignIn.xcframework
"""


class FakeDistribution:
    def __init__(self, root: pathlib.Path):
        self.metadata = METADATA
        self.umbrella_header = root / "Firebase.h"
        self.umbrella_header.write_text("#import <FirebaseCore/FirebaseCore.h>\n")
        run = root / "run"
        run.write_text("#!/bin/sh\n")
        run.chmod(0o755)
        self.crashlytics_tools = [run]
        self.requested = None

    def extract_frameworks(self, names):
        self.requested = list(names)
        return {name: pathlib.Path(f"/zip/{name}.xcframework") for name in self.requested}


class FakeArtifacts:
    def binary_target(self, name):
        return f'.binaryTarget(name: "{name}", path: "stored/{name}")'


class FakeStore:
    def __init__(self):
        self.stored = None

    def store(self, frameworks):
        self.stored = dict(frameworks)
        return FakeArtifacts()


def config(sdks):
    return ReleaseConfig(
        sdks=tuple(sdks),
        external_products=(ExternalProduct(
            name="GoogleTagManager",
            binary=ExternalBinary(name="GoogleTagManager", url="https://example.com/gtm.zip", checksum="abc"),
            requires_sdk="FirebaseAnalytics",
        ),),
        source_targets=(SourceTarget(name="GooglePackages", sdks=("GoogleSignIn",)),),
        settings=ManifestSettings(package_name="GooglePackages", firebase_version="13.2.0", ios_version="15"),
    )


class BuildReleaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self._tmp.name)
        (tmp / "zip").mkdir()
        self.package = tmp / "package"
        self.package.mkdir()
        self.distribution = FakeDistribution(tmp / "zip")
        self.store = FakeStore()

    def tearDown(self):
        self._tmp.cleanup()

    def build(self, sdks=("FirebaseCrashlytics",)):
        return build_release(self.distribution, self.store, self.package, config(sdks))

    def test_stores_exactly_the_planned_binaries(self):
        self.build()
        self.assertEqual(self.distribution.requested, ["FirebaseCore", "FirebaseCrashlytics", "GoogleSignIn"])
        self.assertEqual(list(self.store.stored), ["FirebaseCore", "FirebaseCrashlytics", "GoogleSignIn"])

    def test_writes_a_manifest_that_uses_the_stored_artifacts(self):
        self.build()
        manifest = (self.package / "Package.swift").read_text()
        self.assertIn('.binaryTarget(name: "FirebaseCrashlytics", path: "stored/FirebaseCrashlytics")', manifest)
        self.assertIn('.library(name: "GoogleTagManager"', manifest)

    def test_installs_the_umbrella_header_and_an_anchor_source(self):
        self.build()
        umbrella = self.package / "Sources" / "Firebase"
        self.assertEqual(
            (umbrella / "include" / "Firebase.h").read_text(), "#import <FirebaseCore/FirebaseCore.h>\n"
        )
        self.assertTrue((umbrella / "Firebase.c").exists())

    def test_installs_executable_crashlytics_tools_for_the_build_phase(self):
        self.build()
        run = self.package / "Tools" / "Crashlytics" / "run"
        self.assertTrue(os.access(run, os.X_OK))

    def test_skips_umbrella_and_crashlytics_tools_when_not_needed(self):
        build_release(self.distribution, self.store, self.package, ReleaseConfig(
            sdks=("GoogleSignIn",),
            settings=ManifestSettings(package_name="GooglePackages", firebase_version="13.2.0", ios_version="15"),
        ))
        self.assertFalse((self.package / "Sources" / "Firebase").exists())
        self.assertFalse((self.package / "Tools" / "Crashlytics").exists())

    def test_replaces_files_left_by_the_previous_version(self):
        stale = self.package / "Tools" / "Crashlytics" / "stale-tool"
        stale.parent.mkdir(parents=True)
        stale.write_text("old")
        self.build()
        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
