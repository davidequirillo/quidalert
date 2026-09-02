# Instructions for developers and distributors

Install Git for Windows

[https://git-scm.com/install/windows](https://git-scm.com/install/windows)

Install VSCode IDE

[https://code.visualstudio.com/](https://code.visualstudio.com/)

Install Docker Desktop for Windows

[https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)

## Client

Install Flutter SDK

[https://docs.flutter.dev/get-started](https://docs.flutter.dev/get-started)

On terminal, go to "quidalert/client/flutter_app" folder and call these commands:

```bash
flutter clean

flutter pub get
```

Note: in some cases, in windows operative system, you must enable "developer mode" (in windows settings), otherwise the command "flutter pub get" could return an error.

### Customization & App Store Deployment

To publish your own instance of this application to the app stores (Google Play Store / Apple App Store), **you do not need to rename the project at the Flutter structural level** (e.g., `pubspec.yaml` or Dart `import` statements). 

You only need to configure the distribution identifiers by following these steps:

1. In-App Title (Top Bar): the visible app title inside the UI is centralized. Open `lib/config.dart` and update the variable:
```dart
const String appName = "Your Custom App Name";
```

2. Package Name / Bundle ID (Store Unique Identifier): to prevent store conflicts, you must set your own unique ID (e.g., com.yourdomain.appname). You can update this automatically using the included package.
```bash
dart run change_app_package_name:main com.yourdomain.yourapp
```

3. Display Name (Name under the phone icon):
- Android: Update the android:label value in android/app/src/main/AndroidManifest.xml.
- iOS: Update the CFBundleDisplayName entry in ios/Runner/Info.plist.

4. Customizing the App Icon (Optional): If you want to change the application icon:
- Replace the source image at `assets/icon/icon.png` with your new icon (recommended: PNG, 1024x1024px or higher, squared without pre-rounded corners).
- Automatically generate the launcher icons for Android and iOS by running these commands:

```bash
flutter pub get
dart run flutter_launcher_icons
```

In "lib/config.dart", change appName, and change apiUrl, to connect to the correct relative server.  
Change "competenceTerritory" too, to inform the public about the zone where your app can operate. 

### Push notifications setup

To receive push notifications, the app requires registration to **Firebase Cloud Messaging (FCM)**.

Push notifications are not enabled by default in this repository because each distributor must use their own Firebase project.

You must:

- Create a Firebase project at [https://console.firebase.google.com](https://console.firebase.google.com)

- In your developer machine, install Node.js latest LTS version, from [https://nodejs.org/en/download](https://nodejs.org/en/download)

- Install Firebase CLI using npm

    ```bash
   npm install -g firebase-tools
   ```

- In your terminal, do firebase login:

    ```bash
    firebase login
    ```
    This command will associate your firebase CLI to your Google account

- In your terminal, install the FlutterFire CLI:
   ```bash
   dart pub global activate flutterfire_cli 
   ```

- Run:

    ```bash
   flutterfire configure
   ```
   Follow the instructions: this will generate lib/firebase_options.dart and fetches other files from Google, for your environment.

- If "flutterfire configure" has not downloaded and placed automatically the following platform files, you must manually download them and place them:
    - android/app/google-services.json
    - ios/Runner/GoogleService-Info.plist

- About your backend (server-side)
    - Create a Service Account in Firebase Console (Google)
    - Download the serviceAccountKey.json
    - Configure it in your Python backend (see backend section, "sending push notification" subsection)

Without these steps, the application will not compile and will not run.

### About background location updates

This project uses the flutter_background_geolocation plugin.
The plugin works without a license in DEBUG builds.
However, a commercial license is required for RELEASE builds.

If you plan to distribute this app, you must purchase a single application license from Transistorsoft and add it to the AndroidManifest.xml file (see AndroidManifest.xml, license meta)

### Distribution

Compile the app, distribute it (or install it in the mobile/client device manually for testing purposes).

## Backend

Read default settings in config.py file to have an idea of base configuration variables, and read the comments contained in the file. NOTE: to modify these variables, it is not recommended to act here in this file, but it is recommended to modify them in the .env file (see the following explanation). 

See ".env.example" to read additional info about those environment configuration variables.

Copy ".env.example" to ".env" file, and edit .env file, to change the desired environment variables.

Conda environment is not required for our fastapi backend (because fastapi runs inside a container, see docker-compose.dev.yml), but it's useful in VSCode for the development.

Install miniconda:

[https://www.anaconda.com/download/success](https://www.anaconda.com/download/success)

On miniconda prompt (terminal), go to "quidalert/server/api_backend" folder and write:

```bash
conda env create -f environment.yml
```

To activate the created environment, call the following:

```bash
conda activate quidalert_env
```

FastAPI, Postgres DBMS, Redis, SMTP server (useful to send mail notification to users), minIO server (s3 bucket for file upload), are configured as containers. They are defined in "docker-compose.dev.yml" file (docker-compose.dev.yml for development, docker-compose.prod.yml for production), so read this file for more info about them.

To download these container images from internet, build them, and start them, you only need to write this single command:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Now, the backend and all related services are running as docker containers. 

To stop them:

```bash
docker compose -f docker-compose.dev.yml down
```

To start them without rebuild:

```bash
docker compose -f docker-compose.dev.yml up -d
```

NOTE: in development mode, there's a "real-time" mapping between the fastapi backend directory (server/api_backend) and the /app directory in the fastapi_backend_dev container (see docker-compose.dev.yml). Additionally, almost every change to the source code automatically reloads the uvicorn server (see Dockerfile.dev). This eliminates the need to rebuild and restart the fastapi_backend_dev container image (with --build option) every time we modify a piece of source code.

### Postgres container configuration

To build the entire database tables from existent migration sources, you can run the following command:

```bash
docker exec -it postgres_dbms_dev alembic upgrade head
```

### Redis container configuration

The application employs a dual-database strategy to optimize performance and scalability: while PostgreSQL serves as the primary relational database for standard queries and persistent data storage, Redis is utilized as a high-performance sidecar to handle intensive, high-frequency workloads. This is particularly critical for tasks such as the periodic ingestion of GPS coordinates from clients, where low-latency throughput is essential. 

To provide maximum deployment flexibility, the system supports both "single" and "cluster" modes for Redis, which can be easily toggled via the REDIS_MODE environment variable without requiring any architectural changes (see .env file).

Redis "cluster" mode features 16 logical shards (if you need, this number can be increased to a value in [32, 64, 96, 128], although 16 is the recommended value). Do not lower the number of shards: logical shards are 16 and they must remain that way, while the cluster redis nodes do not necessarily have to be 16, but they can be as few as 3, as defined in my personal docker-compose file, especially if you don't expect a high user load. However, for very heavy workloads, with a large number of users, it's recommended to have a number of Redis nodes equal to the number of logical shards, i.e., a RedisCluster composed of 16 redis nodes.  
IMPORTANT: don't change logical shards number when Redis database is not empty, to avoid serious data corruption or loss.

In Redis "single" mode, logical shards number is forced to 1 (Redis data all goes into one logical shard).

If you use Redis in "cluster" mode, you must join redis nodes. Note: use the password defined in .env file:

```bash
docker exec -it redis_node_1_dev redis-cli -a "testpassword123" --cluster create redis-node-1:7001 redis-node-2:7002 redis-node-3:7003 --cluster-replicas 0 --cluster-yes
```

### Bucket s3 (minio) configuration

Minio is used to upload files into it.

First of all you need to create two temporary keys (access key and secret key) for the administrator user. These keys must be the same used as "S3_USER" and "S3_PASS" in .env file. In other words, the access key is S3_USER value, and the secret key is S3_PASS value.

```bash
docker exec -it minio_storage_dev mc alias set local http://localhost:9000 admin password123
```

We can verify the operation using this list command:

```bash
docker exec -it minio_storage_dev mc alias list
```

Create an additional service account, choosing access key and secret key.

```bash
docker exec -it minio_storage_dev mc admin user svcacct add local admin --access-key "my-fastapi-complex-key" --secret-key "my-fastapi-complex-secret-123"
```

We can verify the operation using this list command:

```bash
docker exec -it minio_storage_dev mc admin user svcacct list local admin
```

These two keys ("my-fastapi-complex-key" and "my-fastapi-complex-secret-123"), must be inserted in .env file, assigning them to S3_ACCESS_KEY and S3_SECRET_KEY variables.

Now you must create the bucket. Go to http://localhost:9001, login as admin user, and create the bucket (see S3_BUCKET_NAME in .env).

### About SMTP

Some API, for example registration, login, password reset, etc., require a smtp server to send email messages to users. So, in a real production system, set the correct SMTP_HOST and SMTP_PORT in environment file (.env file).

For local testing/development purposes, there is already a fake local smtp server (called "mailpit" defined as a container in docker-compose.dev.yml). You can view the mail messages sent to the users using its web interface available at the following url: "http://localhost:8025". 

NOTE: mailpit does not support authentication and TLS, so in your development env file (.env) you must set SMTP_USER='', SMTP_PASS='', SMPT_USE_TLS='no'. See .env.example file for details.

There is a script useful to test email delivery.

```bash
docker exec -it fastapi_backend_dev python -m scripts.send_sample_mail --to_email recipient@example.com
```

As we just said, in development mode email messages will be displayed in the local mailpit web application (http://localhost:8025).

### Sending push notifications to clients

To be able to send push notifications to the clients, the backend need to connect to FCM cloud using the account secret key assigned to it by the FCM platform.

In your Firebase Project web console, you must go to "Account Service" and generate private key (service Account Key). Download the json file and place it in your backend folder renaming it as "firebase_keys.json" (the path of this file will be specified as an environment variable, FIREBASE_CONFIG_FPATH)

### Project debugging (run)

Clone repository 

Go to quidalert local folder and write the following command to open the entire project workspace with VS Code:

```bash
code .quidalert.code-workspace
```

NOTE: code workspace has been configured to ignore some useless folders from the programming IDE view (for example “build” directories)

To run (debug) client, inside VS Code IDE start the Android emulator, wait for the emulator to fully boot, and then go to VS Code menu -> View -> Run.
- Choose "Debug client (Android Emulator)" and click to play to debug the client.

The backend is already running (it has started when we have done "docker compose -f docker-compose.dev.yml up -d") and if we modify the python code in the backend directory of this project, the code in the container will be modified too (due to fastapi container volume mapping defined in docker-compose.dev.yml file, which is the docker-compose file used only for development). 

NOTES ABOUT THE CLIENT:
- "Debug client (Android Emulator)" requires Android SDK (Android Studio) with Android Studio "command line tools" (downloadable from the settings section of Android Studio IDE), and at least one Android emulator device created (for example Pixel 8 emulator).

Flutter Web device (Chrome) and Windows are not supported at the moment.

### Run the client

You can launch the client via VSCode launcher (see debugging/run section).

IMPORTANT: at database empty, using the client flutter app, register the first user (admin) using your custom password you have placed in ADMIN_PASS environment variable.  
After that, you can reset the password at runtime using the client app functionality labeled "forgot password?", and choose a new desired password.

### Server-side seeding scripts

In server/api_backend/scripts folder there are some seeding scripts, useful to populate the database with fake users (pass --help option as input argument to these scripts to see some useful details):

```bash
docker exec -it fastapi_backend_dev python -m scripts.seed_users
```

There is also a script to populate Redis database with random gps locations and other temp data for fake users. Note, fake gps locations will be considered expired after a certain period (more or less 48 hours) and consequently they will be deleted, so, after that period, if you want to assign new random locations to fake users you will need to run the same script. 

```bash
docker exec -it fastapi_backend_dev python -m scripts.seed_redis_data
```

There is a script to assign the same FCM token (related to your client device logged user) to all fake users (whose email ends with "@example.com"), to send all push notifications destined to them in bulk to your device.  
Note: use this feature with caution as your single device will receive notifications intended for all fake users, thus bombarding your device with notifications.

```bash
docker exec -it fastapi_backend_dev python -m scripts.seed_fcm_tokens --email device-logged-user-email
```

IMPORTANT NOTE: scripts related to fake users are very good for development, and they can also be used in production because they don't alter the real users in the database. However, be careful: if your database grows and the number of real users becomes very high, using these scripts could cause significant efficiency issues. In .env file, you can configure FAKE_USER_SCRIPTS_ENABLED='no' to avoid accidentally running one of them. 

### Automatic test cases

To automatically test the FastAPI backend (API endpoints and various internal functions), we use a SQLite database and a Redis cache that are separate from the development and production environments. The S3 test bucket is also separate, and no notifications or emails are sent during any automated test cases. So, don't worry about running this useful command for automatically run unit and integration tests.

```bash
docker exec -it fastapi_backend_dev pytest -v -s
```

## A simple production environment (server-side)

VPS: Debian 12.0 "Bookworm"

Connect to VPS using ssh:

```bash
ssh root@quidalert.example.com
```

Update debian and install some useful packets:

```bash
apt update && apt upgrade
apt install -y curl ca-certificates gnupg git
```

### Install docker engine

In the VPS machine, install docker engine from official docker repository

Installation instruction from: https://docs.docker.com/engine/install/debian/

### Git project clone 

In the VPS machine, make the project directory e clone the repository

```bash
cd /opt
mkdir -p quidalert
chown -R $USER:$USER /opt/quidalert
cd /opt/quidalert
git clone https://github.com/davidequirillo/quidalert.git .
```

### Configure environment

Go to /opt/quidalert/server folder and create .env file from .env.example

```bash
cp env.example .env
chmod 600 .env
```

Using "nano" text editor, edit .env file, setting environment variables for production (APP_MODE="production", etc., etc. ).  
IMPORTANT SECURITY NOTICE: env.example file, for convenience, contains simple strings for credentials (passwords, keys, salts and peppers), but in production we must change them and use complex passwords, complex secret keys, complex peppers.

### Firebase credentials

Go to /opt/quidalert/server/api_backend folder and put firebase_keys.json file inside it (this is the private file downloaded from our Firebase account, which contains the credentials useful to connect to FCM server).

### Run docker compose (production version)

We run docker compose command with our production yml file as input (docker-compose.prod.yml) to start the containers, using --build option to build the container images before starting them. The build option (--build) is useful to construct the container images.

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Now, the backend and all related services are running as docker containers.

To stop them:

```bash
docker compose -f docker-compose.prod.yml down
```

To start them without rebuild:

```bash
docker compose -f docker-compose.prod.yml up -d
```

NOTE: in production mode, if we make a change to the fastapi backend source code, or more generally we sync the project directory with a new version of the remote repository (git pull), and the updates affect the fastapi backend or other containers, we need to rebuild the container images with the --build option.

### Postgres db init

To initialize your Postgres database, run this command:

```bash
docker exec -it fastapi_backend alembic upgrade head
```

### Join Redis Cluster nodes

Redis is configured in cluster mode. To join Redis Cluster nodes, run the following command:

```bash
REDIS_PASS='your_redis_password_from_env'
docker exec -it redis_node_1 redis-cli -a "${REDIS_PASS}" --cluster create \
  redis-node-1:6379 \
  redis-node-2:6379 \
  redis-node-3:6379 \
  --cluster-replicas 0 \
  --cluster-yes
```

### S3 bucket (minio) configuration

First of all we need to create two temporary keys (access key and secret key) for the administrator user. These keys must be the same used as "S3_USER" and "S3_PASS" in .env file. In other words, the access key is S3_USER value ("admin"), and the secret key is S3_PASS value ("a complex password for production").

```bash
S3_PASS='your_s3_password_from_env'
docker exec -it minio_storage mc alias set local http://localhost:9000 admin "${S3_PASS}"
```

We can verify the operation using this list command. 

```bash
docker exec -it minio_storage mc alias list
```

After that, we create an additional service account, choosing access key and secret key.

```bash
S3_AKEY='your_s3_access_key_from_env'
S3_SKEY='your_s3_secret_key_from_env'
docker exec -it minio_storage mc admin user svcacct add local admin --access-key "${S3_AKEY}" --secret-key "${S3_SKEY}"
```

We verify the operation using this list command

```bash
docker exec -it minio_storage mc admin user svcacct list local admin
```

Now we must create the bucket: to do it, we must connect to the web minio administration console, but from the outside this service is not reachable, so we must do a ssh tunnel to connect to the minio webconsole located in the VPS, from the vps itself, via ssh tunnel coming from our local machine.

In our local machine, we run the following command, to start a ssh tunnel from our local machine to the remote VPS machine.
Note: before running the following command, we need to make sure that port 9001 on our local PC is not being used by any other service.

```bash
ssh -L 9001:localhost:9001 root@quidalert.example.com
```

Now, with the web browser in our local machine, we connect to the following url

http://localhost:9001

Thanks to the ssh tunnel, the remote web console of the s3 bucket, located in the VPS, will open. We login with minio credentials (S3_USER value and S3_PASS value, defined in .env file, in the vps), and we create "quidalert-uploads" bucket.

### A note about .env security

The .env file, which contains the environment variables required for the FastAPI backend and various related services to function properly, is located outside of the containers and is owned exclusively by the system's root user (the Debian machine root user). This ensures that the passwords and keys contained in the .env file are basically secure.

However, for added security, you can remove these critical environment variables (passwords, secret keys, peppers) from the .env file, encrypt them and use Docker Secrets to manage them securely.

### SMTP server

To be able to send email messages to clients, the VPS backend must connect to a SMTP server. We can use a SMTP server provided by Resend online platform. We create an account on this platform.

https://resend.com/

By following the instructions provided by the platform immediately after creating the account, we receive the "Resend API key" required to send email messages (from our VPS) and we declare the domain from which we send our emails, verifying it by adding some DNS entries in our domain configuration.

After that, we won't need to change anything in our fastapi backend code. We'll just need to set the SMTP environment variables to the correct values (SMTP server, user, password, etc.) in the .env file.

```bash
SMTP_HOST='smtp.resend.com'
SMTP_PORT=587
SMTP_USER='resend'
SMTP_PASS='re_12345_YourResendReceivedAPIKey'
SMTP_FROM='noreply@example.com'
SMTP_FROM_NAME='Quidalert'
SMTP_USE_TLS='yes'
```

There is a script useful to test email delivery from our production VPS.

```bash
docker exec -it fastapi_backend python -m scripts.send_sample_mail --to_email recipient@example.com
```

## Run the client (in production mode)

### Case 1: Android emulator

Start VS Code, inside VS Code start the Android Emulator, wait for the emulator to fully boot.

In your terminal, execute the following command:

```bash
flutter run --dart-define=API_URL=https://quidalert.example.com -d emulator-5554
```

This way, the apiUrl configuration variable, used by the client, will be set with this environment variable (API_URL) and not with the default fallback variable contained in the config.dart file (used for development).

Note: obviously, replace "quidalert.example.com" with your production public server name.

### Case 2: Android real device

In progress...
