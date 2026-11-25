import unittest

from firebase_release.dependency_graph import parse_metadata
from firebase_release.release_plan import UMBRELLA_TARGET, ExternalBinary, ExternalProduct, SourceTarget, plan_release

METADATA = """\
## FirebaseAnalytics
- FirebaseAnalytics.xcframework
- FirebaseCore.xcframework

## FirebaseAuth (~> FirebaseAnalytics)
- FirebaseAuth.xcframework
- GTMSessionFetcher.xcframework

## FirebaseDatabase (~> FirebaseAnalytics)
- FirebaseDatabase.xcframework

## GoogleSignIn
- GTMSessionFetcher.xcframework
- GoogleSignIn.xcframework
"""

TAG_MANAGER = ExternalProduct(
    name="GoogleTagManager",
    binary=ExternalBinary(name="GoogleTagManager", url="https://example.com/gtm.zip", checksum="abc"),
    requires_sdk="FirebaseAnalytics",
)


class ReleasePlanTests(unittest.TestCase):
    def setUp(self):
        self.graph = parse_metadata(METADATA)

    def product(self, plan, name):
        return next(product for product in plan.products if product.name == name)

    def test_each_selected_sdk_becomes_a_product_in_the_given_order(self):
        plan = plan_release(self.graph, sdks=["FirebaseAuth", "GoogleSignIn"])
        self.assertEqual([product.name for product in plan.products], ["FirebaseAuth", "GoogleSignIn"])

    def test_firebase_product_carries_umbrella_and_all_resolved_binaries(self):
        plan = plan_release(self.graph, sdks=["FirebaseAuth"])
        self.assertEqual(
            self.product(plan, "FirebaseAuth").targets,
            (UMBRELLA_TARGET, "FirebaseAnalytics", "FirebaseAuth", "FirebaseCore", "GTMSessionFetcher"),
        )

    def test_non_firebase_sdk_has_no_umbrella(self):
        plan = plan_release(self.graph, sdks=["GoogleSignIn"])
        self.assertEqual(self.product(plan, "GoogleSignIn").targets, ("GTMSessionFetcher", "GoogleSignIn"))

    def test_shared_frameworks_are_declared_once(self):
        plan = plan_release(self.graph, sdks=["FirebaseAuth", "GoogleSignIn"])
        self.assertEqual(
            plan.binaries,
            ("FirebaseAnalytics", "FirebaseAuth", "FirebaseCore", "GTMSessionFetcher", "GoogleSignIn"),
        )

    def test_only_selected_sdks_are_declared(self):
        plan = plan_release(self.graph, sdks=["FirebaseAuth"])
        self.assertNotIn("FirebaseDatabase", plan.binaries)

    def test_external_product_adds_its_binary_on_top_of_the_required_sdk(self):
        plan = plan_release(self.graph, sdks=[], external_products=[TAG_MANAGER])
        self.assertEqual(
            self.product(plan, "GoogleTagManager").targets,
            (UMBRELLA_TARGET, "FirebaseAnalytics", "FirebaseCore", "GoogleTagManager"),
        )
        self.assertEqual(plan.external_binaries, (TAG_MANAGER.binary,))
        self.assertEqual(plan.binaries, ("FirebaseAnalytics", "FirebaseCore"))

    def test_source_target_depends_on_the_union_of_its_sdks(self):
        wrapper = SourceTarget(name="GooglePackages", sdks=("FirebaseAuth", "GoogleSignIn"))
        plan = plan_release(self.graph, sdks=[], source_targets=[wrapper])
        self.assertEqual(
            plan.source_targets[0].dependencies,
            (UMBRELLA_TARGET, "FirebaseAnalytics", "FirebaseAuth", "FirebaseCore", "GTMSessionFetcher", "GoogleSignIn"),
        )
        self.assertIn("GoogleSignIn", plan.binaries)

    def test_umbrella_is_needed_only_when_a_firebase_sdk_is_selected(self):
        self.assertFalse(plan_release(self.graph, sdks=["GoogleSignIn"]).needs_umbrella)
        self.assertTrue(plan_release(self.graph, sdks=["FirebaseDatabase"]).needs_umbrella)


if __name__ == "__main__":
    unittest.main()
