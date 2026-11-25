import pathlib
import tempfile
import unittest
import zipfile

from firebase_release.distribution import FirebaseDistribution, InvalidDistribution

METADATA = "## FirebaseAnalytics\n- FirebaseCore.xcframework\n"


def write_firebase_tree(archive: zipfile.ZipFile) -> None:
    archive.writestr("Firebase/METADATA.md", METADATA)
    archive.writestr("Firebase/Firebase.h", "// umbrella")
    archive.writestr("Firebase/FirebaseCrashlytics/run", "#!/bin/sh")
    archive.writestr("Firebase/FirebaseCrashlytics/upload-symbols", "binary")
    for folder in ("FirebaseAnalytics", "FirebaseCrashlytics"):
        archive.writestr(f"Firebase/{folder}/FirebaseCore.xcframework/Info.plist", folder)
    archive.writestr("Firebase/FirebaseFirestore/grpc.xcframework/Info.plist", "big")


def flat_zip(path: pathlib.Path) -> pathlib.Path:
    with zipfile.ZipFile(path, "w") as archive:
        write_firebase_tree(archive)
    return path


def nested_zip(path: pathlib.Path) -> pathlib.Path:
    """The GitHub release asset wraps the real zip together with build logs."""
    inner = flat_zip(path.parent / "inner.zip")
    with zipfile.ZipFile(path, "w") as archive:
        archive.write(inner, "13_2_0/Firebase-13.2.0-latest.zip")
        archive.writestr("build_logs/FirebaseCore-iphoneos.txt", "log")
    inner.unlink()
    return path


class FirebaseDistributionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def open(self, zip_path):
        return FirebaseDistribution.open(zip_path, self.tmp / "work")

    def test_reads_metadata_from_a_flat_zip(self):
        self.assertEqual(self.open(flat_zip(self.tmp / "Firebase.zip")).metadata, METADATA)

    def test_reads_metadata_from_the_release_asset_that_nests_the_real_zip(self):
        self.assertEqual(self.open(nested_zip(self.tmp / "Firebase.zip")).metadata, METADATA)

    def test_exposes_umbrella_header_and_crashlytics_tools(self):
        distribution = self.open(flat_zip(self.tmp / "Firebase.zip"))
        self.assertEqual(distribution.umbrella_header.read_text(), "// umbrella")
        self.assertEqual(
            sorted(path.name for path in distribution.crashlytics_tools), ["run", "upload-symbols"]
        )

    def test_extracts_only_the_requested_frameworks_once_each(self):
        distribution = self.open(flat_zip(self.tmp / "Firebase.zip"))
        frameworks = distribution.extract_frameworks(["FirebaseCore"])
        self.assertEqual(list(frameworks), ["FirebaseCore"])
        self.assertTrue((frameworks["FirebaseCore"] / "Info.plist").exists())
        self.assertFalse(any(self.tmp.rglob("grpc.xcframework")))

    def test_names_a_framework_missing_from_the_zip(self):
        distribution = self.open(flat_zip(self.tmp / "Firebase.zip"))
        with self.assertRaises(InvalidDistribution) as raised:
            distribution.extract_frameworks(["FirebaseCore", "Nope"])
        self.assertIn("Nope", str(raised.exception))

    def test_rejects_a_file_that_is_not_a_firebase_zip(self):
        bogus = self.tmp / "Firebase.zip"
        bogus.write_text("Not Found")
        with self.assertRaises(InvalidDistribution):
            self.open(bogus)


if __name__ == "__main__":
    unittest.main()
