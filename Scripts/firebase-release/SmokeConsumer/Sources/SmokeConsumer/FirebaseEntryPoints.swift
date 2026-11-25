import Firebase
import FirebaseAnalytics
import FirebaseAuth
import FirebaseCrashlytics
import FirebaseDatabase
import FirebaseMessaging
import FirebasePerformance
import GoogleTagManager

/// One public type per product, so the linker has to resolve every SDK.
public enum FirebaseEntryPoints {
    public static let types: [Any.Type] = [
        FirebaseApp.self,
        Analytics.self,
        Auth.self,
        Crashlytics.self,
        Database.self,
        Messaging.self,
        Performance.self,
    ]

    /// GoogleTagManager has no class to reference; using its protocol proves the module imports.
    public static func acceptsTagManagerFunction(_ function: (any TAGCustomFunction)?) -> Bool {
        function == nil
    }
}
