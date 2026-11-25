// swift-tools-version: 6.0
// Builds and links every product of the generated GooglePackages manifest, the way an app would.
// Run after release.py:  xcodebuild build-for-testing -scheme SmokeConsumer -destination 'generic/platform=iOS Simulator'

import PackageDescription

let products = [
    "FirebaseAnalytics", "FirebaseAuth", "FirebaseCrashlytics", "FirebaseDatabase",
    "FirebaseMessaging", "FirebasePerformance", "GoogleTagManager"
]

let package = Package(
    name: "SmokeConsumer",
    platforms: [.iOS(.v15)],
    products: [.library(name: "SmokeConsumer", targets: ["SmokeConsumer"])],
    dependencies: [.package(name: "GooglePackages", path: "../../..")],
    targets: [
        .target(
            name: "SmokeConsumer",
            dependencies: products.map { .product(name: $0, package: "GooglePackages") },
            linkerSettings: [.unsafeFlags(["-Xlinker", "-ObjC"])]
        ),
        .testTarget(name: "SmokeConsumerTests", dependencies: ["SmokeConsumer"], linkerSettings: [.unsafeFlags(["-Xlinker", "-ObjC"])])
    ]
)
