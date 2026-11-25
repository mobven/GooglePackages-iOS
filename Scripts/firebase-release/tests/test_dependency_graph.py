import unittest

from firebase_release.dependency_graph import UnknownSdk, parse_metadata

METADATA = """\
## Dependency Graph

"(~> X)" below means that the SDK requires all of the xcframeworks from X.

## FirebaseAnalytics
- FirebaseAnalytics.xcframework
- FirebaseCore.xcframework
- GoogleUtilities.xcframework

## FirebaseAuth (~> FirebaseAnalytics)
- FirebaseAuth.xcframework
- GTMSessionFetcher.xcframework

## FirebaseFunctions (~> FirebaseAuth)
- FirebaseFunctions.xcframework

## GoogleSignIn
- GTMSessionFetcher.xcframework
- GoogleSignIn.xcframework

## Versions

               CocoaPod                | Version
---------------------------------------|---------
Firebase                               | 13.2.0
"""


class DependencyGraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = parse_metadata(METADATA)

    def test_lists_every_sdk_section(self):
        self.assertEqual(
            self.graph.sdk_names(),
            ("FirebaseAnalytics", "FirebaseAuth", "FirebaseFunctions", "GoogleSignIn"),
        )

    def test_standalone_sdk_resolves_to_its_own_frameworks(self):
        self.assertEqual(self.graph.frameworks_for("GoogleSignIn"), ("GTMSessionFetcher", "GoogleSignIn"))

    def test_sdk_with_requirement_includes_required_frameworks(self):
        self.assertEqual(
            self.graph.frameworks_for("FirebaseAuth"),
            ("FirebaseAnalytics", "FirebaseAuth", "FirebaseCore", "GTMSessionFetcher", "GoogleUtilities"),
        )

    def test_requirements_resolve_transitively(self):
        self.assertIn("FirebaseCore", self.graph.frameworks_for("FirebaseFunctions"))

    def test_unknown_sdk_names_the_available_ones(self):
        with self.assertRaises(UnknownSdk) as raised:
            self.graph.frameworks_for("FirebaseStorage")
        self.assertIn("FirebaseAuth", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
