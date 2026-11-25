#!/usr/bin/env python3 -I
"""Regenerates this package from the official Firebase XCFramework zip.

  # 1) Build against local copies of the xcframeworks and verify (nothing to publish yet):
  python3 -I Scripts/firebase-release/release.py --zip ~/Downloads/Firebase.zip --version 13.2.0 --mode local

  # 2) Produce release zips + a Package.swift that downloads them by url + checksum:
  python3 -I Scripts/firebase-release/release.py --zip ~/Downloads/Firebase.zip --version 13.2.0 --mode release

The zip comes from https://github.com/firebase/firebase-ios-sdk/releases/download/<version>/Firebase.zip
(https://firebase.google.com/docs/ios/installation-methods#integrate-manually).
"""
import argparse
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from firebase_release.artifact_store import LocalArtifactStore, ReleaseArtifactStore  # noqa: E402
from firebase_release.build_release import ReleaseConfig, build_release  # noqa: E402
from firebase_release.distribution import FirebaseDistribution  # noqa: E402
from firebase_release.manifest import ManifestSettings  # noqa: E402
from firebase_release.release_plan import ExternalBinary, ExternalProduct  # noqa: E402

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[2]
IOS_VERSION = "15"  # Firebase 13 and GoogleTagManager 9 minimum.
# The SDKs of the Firebase zip this package exposes. GoogleSignIn is no longer in the zip (absent in 13.2.0).
SDKS = (
    "FirebaseAnalytics",
    "FirebaseAuth",
    "FirebaseCrashlytics",
    "FirebaseDatabase",
    "FirebaseMessaging",
    "FirebasePerformance",
)
# GoogleTagManager is not in the Firebase zip. Its own SPM wrapper depends on firebase-ios-sdk (source),
# so we take Google's binary directly. Source: google-tag-manager-ios-sdk 9.3.0 Package.swift.
GOOGLE_TAG_MANAGER = ExternalProduct(
    name="GoogleTagManager",
    binary=ExternalBinary(
        name="GoogleTagManager",
        url="https://dl.google.com/firebase/ios/tagmanager/swiftpm/9.2.0/GoogleTagManager.zip",
        checksum="95d4715d7588e1a8163a4563d81f2cc3b3f0baffe4cee56e552c4668e0cd292d",
    ),
    requires_sdk="FirebaseAnalytics",
)
LOCAL_ARTIFACTS_DIR = "LocalArtifacts"
RELEASE_ARTIFACTS_DIR = "dist"


def release_tag(version: str) -> str:
    return f"firebase-{version}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", required=True, type=pathlib.Path, help="Firebase.zip from the Firebase release")
    parser.add_argument("--version", required=True, help="Firebase version in the zip, e.g. 13.2.0")
    parser.add_argument("--mode", choices=("local", "release"), required=True)
    parser.add_argument("--repo", default="mobven/GooglePackages-iOS", help="GitHub repo hosting the release")
    args = parser.parse_args()

    tag = release_tag(args.version)
    if args.mode == "local":
        store = LocalArtifactStore(PACKAGE_ROOT, LOCAL_ARTIFACTS_DIR)
    else:
        store = ReleaseArtifactStore(PACKAGE_ROOT / RELEASE_ARTIFACTS_DIR,
                                     f"https://github.com/{args.repo}/releases/download/{tag}")
    config = ReleaseConfig(
        sdks=SDKS,
        external_products=(GOOGLE_TAG_MANAGER,),
        settings=ManifestSettings(
            package_name="GooglePackages",
            firebase_version=args.version,
            ios_version=IOS_VERSION,
        ),
    )
    with tempfile.TemporaryDirectory(prefix="firebase-release-") as work_dir:
        plan = build_release(FirebaseDistribution.open(args.zip, pathlib.Path(work_dir)), store, PACKAGE_ROOT,
                             config)

    print(f"Package.swift: {len(plan.products)} products, {len(plan.binaries)} xcframeworks "
          f"+ {len(plan.external_binaries)} external binary (mode: {args.mode}).")
    if args.mode == "release":
        branch = f"firebase-ios-{args.version.replace('.', '-')}"
        print("\nCommit and push the branch, then attach the zips to a release on it:")
        print(f"  git push -u origin {branch}")
        print(f"  gh release create {tag} --repo {args.repo} --target {branch} "
              f"--title 'Firebase {args.version} XCFrameworks' {RELEASE_ARTIFACTS_DIR}/*.xcframework.zip")


if __name__ == "__main__":
    main()
