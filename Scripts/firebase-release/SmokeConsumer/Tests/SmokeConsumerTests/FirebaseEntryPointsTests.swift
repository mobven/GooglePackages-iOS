import SmokeConsumer
import XCTest

final class FirebaseEntryPointsTests: XCTestCase {
    func testEveryFirebaseProductIsReachable() {
        XCTAssertEqual(FirebaseEntryPoints.types.count, 7)
        XCTAssertTrue(FirebaseEntryPoints.acceptsTagManagerFunction(nil))
    }
}
