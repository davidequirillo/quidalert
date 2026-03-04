plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    // Quidalert: useful for Firebase Cloud Messaging configuration
    id("com.google.gms.google-services")
}

android {
    namespace = "com.example.quidalert_flutter"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        // Quidalert: default version was VERSION_17
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
        // Quidalert: enable core desugaring and Java version
        isCoreLibraryDesugaringEnabled = true 
    }

    kotlinOptions {
        // Quidalert: default version was VERSION_17
        jvmTarget = JavaVersion.VERSION_1_8.toString()
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.example.quidalert_flutter"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

// Quidalert: dependencies, desugaring
dependencies {
    coreLibraryDesugaring ("com.android.tools:desugar_jdk_libs:2.1.5")
    implementation(platform("com.google.firebase:firebase-bom:34.9.0"))
}

flutter {
    source = "../.."
}
