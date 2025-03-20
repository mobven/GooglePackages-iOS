//
//  GoogleSignIn.swift
//  GooglePackages
//
//  Created by Rashid Ramazanov on 8.12.2024.
//

import FirebaseAuth
import FirebaseCore
import GoogleSignIn
import SwiftUI
import UIKit

public struct GoogleUser {
    public let uid: String
}

public enum GoogleSignIn {
    public static func signIn() async throws -> GoogleUser {
        guard let clientID = FirebaseApp.app()?.options.clientID else {
            fatalError("Missing client id in FirebaseApp options")
        }

        let config = GIDConfiguration(clientID: clientID)
        GIDSignIn.sharedInstance.configuration = config

        guard let windowScene = await UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let rootViewController = await windowScene.windows.first?.rootViewController else {
            fatalError("Unable to access root view controller.")
        }

        let result = try await GIDSignIn.sharedInstance.signIn(withPresenting: rootViewController)

        guard let idToken = result.user.idToken?.tokenString else {
            throw NSError(domain: "GooglePackages", code: 401, userInfo: [
                NSLocalizedDescriptionKey: "Missing ID Token"
            ])
        }

        let credential = GoogleAuthProvider.credential(
            withIDToken: idToken,
            accessToken: result.user.accessToken.tokenString
        )

        return try await firebaseSignIn(credential: credential)
    }

    private static func firebaseSignIn(credential: AuthCredential) async throws -> GoogleUser {
        let user = try await Auth.auth().signIn(with: credential)
        return GoogleUser(uid: user.user.uid)
    }

    public static func openUrl(_ url: URL) {
        GIDSignIn.sharedInstance.handle(url)
    }

    public static func signOut() throws {
        try Auth.auth().signOut()
        GIDSignIn.sharedInstance.signOut()
    }
}
