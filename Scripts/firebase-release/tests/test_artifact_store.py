import hashlib
import os
import pathlib
import tempfile
import unittest
import zipfile

from firebase_release.artifact_store import LocalArtifactStore, MissingChecksum, ReleaseArtifactStore, ReleaseArtifacts


def make_xcframework(root: pathlib.Path, name: str) -> pathlib.Path:
    framework = root / f"{name}.xcframework"
    versions = framework / "macos-arm64" / f"{name}.framework" / "Versions"
    (versions / "A").mkdir(parents=True)
    (versions / "A" / name).write_bytes(b"binary-" + name.encode())
    os.symlink("A", versions / "Current")
    (framework / "Info.plist").write_text("<plist/>")
    return framework


class LocalArtifactStoreTests(unittest.TestCase):
    def test_copies_frameworks_into_the_package_and_references_them_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            source = make_xcframework(tmp / "zip", "FirebaseCore")
            package_root = tmp / "package"
            package_root.mkdir()

            artifacts = LocalArtifactStore(package_root, "LocalArtifacts").store({"FirebaseCore": source})

            copied = package_root / "LocalArtifacts" / "FirebaseCore.xcframework"
            self.assertTrue((copied / "Info.plist").exists())
            self.assertTrue((copied / "macos-arm64" / "FirebaseCore.framework" / "Versions" / "Current").is_symlink())
            self.assertEqual(
                artifacts.binary_target("FirebaseCore"),
                '.binaryTarget(name: "FirebaseCore", path: "LocalArtifacts/FirebaseCore.xcframework")',
            )

    def test_replaces_frameworks_left_from_an_earlier_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            package_root = tmp / "package"
            stale = package_root / "LocalArtifacts" / "Stale.xcframework"
            stale.mkdir(parents=True)

            LocalArtifactStore(package_root, "LocalArtifacts").store(
                {"FirebaseCore": make_xcframework(tmp / "zip", "FirebaseCore")}
            )

            self.assertFalse(stale.exists())


class ReleaseArtifactStoreTests(unittest.TestCase):
    def test_zips_each_framework_with_the_xcframework_at_the_top_and_symlinks_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            source = make_xcframework(tmp / "zip", "FirebaseCore")

            ReleaseArtifactStore(tmp / "dist", "https://example.com/download/firebase-13.2.0").store(
                {"FirebaseCore": source}
            )

            with zipfile.ZipFile(tmp / "dist" / "FirebaseCore.xcframework.zip") as archive:
                names = archive.namelist()
                self.assertTrue(all(name.startswith("FirebaseCore.xcframework/") for name in names))
                link = archive.getinfo("FirebaseCore.xcframework/macos-arm64/FirebaseCore.framework/Versions/Current")
                self.assertEqual((link.external_attr >> 16) & 0o170000, 0o120000)

    def test_references_each_zip_by_release_url_and_its_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            source = make_xcframework(tmp / "zip", "FirebaseCore")

            artifacts = ReleaseArtifactStore(tmp / "dist", "https://example.com/download/firebase-13.2.0").store(
                {"FirebaseCore": source}
            )

            checksum = hashlib.sha256((tmp / "dist" / "FirebaseCore.xcframework.zip").read_bytes()).hexdigest()
            self.assertEqual(
                artifacts.binary_target("FirebaseCore"),
                '.binaryTarget(name: "FirebaseCore", '
                'url: "https://example.com/download/firebase-13.2.0/FirebaseCore.xcframework.zip", '
                f'checksum: "{checksum}")',
            )


class ReleaseArtifactsTests(unittest.TestCase):
    def test_refuses_a_binary_it_has_no_checksum_for(self):
        with self.assertRaises(MissingChecksum):
            ReleaseArtifacts("https://example.com", {}).binary_target("FirebaseCore")


if __name__ == "__main__":
    unittest.main()
