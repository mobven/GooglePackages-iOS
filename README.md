# GooglePackages-iOS

Firebase for Swift Package Manager as **prebuilt XCFrameworks**, taken from the official
[manual-install distribution](https://firebase.google.com/docs/ios/installation-methods#integrate-manually),
instead of compiling `firebase-ios-sdk` from source in every project.

Each Firebase version lives on its own branch, named after it: `firebase-ios-<major>-<minor>-<patch>`
(e.g. `firebase-ios-13-2-0`). The xcframeworks are attached to the GitHub release `firebase-<version>`
and `Package.swift` downloads them by URL and checksum, so the git repository itself stays small.

## Usage

```swift
.package(url: "https://github.com/mobven/GooglePackages-iOS.git", branch: "firebase-ios-13-2-0"),
```

```swift
.product(name: "FirebaseAnalytics", package: "GooglePackages-iOS"),
.product(name: "FirebaseCrashlytics", package: "GooglePackages-iOS"),
```

| Product | Contents |
|---|---|
| `FirebaseAnalytics` | Analytics + Firebase core |
| `FirebaseAuth` | Auth |
| `FirebaseCrashlytics` | Crashlytics |
| `FirebaseDatabase` | Realtime Database |
| `FirebaseMessaging` | Cloud Messaging |
| `FirebasePerformance` | Performance Monitoring |
| `GoogleTagManager` | Tag Manager binary + Analytics |

Every Firebase product also brings the `Firebase` umbrella module, so both `import Firebase` and
`import FirebaseAnalytics` work. The app target needs `-ObjC` in **Other Linker Flags**
(Firebase's requirement for static frameworks).

**Crashlytics dSYM upload:** point the run-script phase at the copy shipped in this package:

```sh
"${BUILD_DIR%/Build/*}/SourcePackages/checkouts/GooglePackages-iOS/Tools/Crashlytics/run"
```

GoogleSignIn is not part of the Firebase 13 zip and is therefore not offered on these branches;
the source-based GoogleSignIn helper remains on `main` / `1.0.0`.

## Updating to a new Firebase version

Requires Python 3.9+ and Xcode (the version Firebase's README names).

1. Download `https://github.com/firebase/firebase-ios-sdk/releases/download/<version>/Firebase.zip`.
2. Branch off the previous version: `git switch -c firebase-ios-<x-y-z>`.
3. Generate a manifest against local copies and verify that every product builds and links:
   ```sh
   python3 -I Scripts/firebase-release/release.py --zip Firebase.zip --version <x.y.z> --mode local
   cd Scripts/firebase-release/SmokeConsumer
   xcodebuild build-for-testing -scheme SmokeConsumer -destination 'generic/platform=iOS Simulator'
   ```
4. Generate the release zips and the final `Package.swift`, commit, push, then publish the zips
   (the script prints both commands):
   ```sh
   python3 -I Scripts/firebase-release/release.py --zip Firebase.zip --version <x.y.z> --mode release
   git add -A && git commit && git push -u origin firebase-ios-<x-y-z>
   gh release create firebase-<x.y.z> --target firebase-ios-<x-y-z> dist/*.xcframework.zip
   ```
   Announce the branch only after the release exists: until then its binary URLs return 404.
5. Run the smoke build once more; it now downloads the published zips and checks their checksums.

To change which SDKs are offered, edit `SDKS` in `Scripts/firebase-release/release.py`; which
xcframeworks each SDK needs is read from the zip's `METADATA.md`. GoogleTagManager comes from
Google's own binary URL (`GOOGLE_TAG_MANAGER` in the same file).

### Generator tests

```sh
cd Scripts/firebase-release && python3 -m unittest discover -s tests -t .
```
