# Installation

## Technical users and developers

Install Git for Windows

[https://git-scm.com/install/windows](https://git-scm.com/install/windows)

Install VSCode IDE

[https://code.visualstudio.com/](https://code.visualstudio.com/)

### Client

Install Flutter SDK

[https://docs.flutter.dev/get-started](https://docs.flutter.dev/get-started)

On terminal, go to "quidalert/client/flutter_app" folder and call these commands:

```
flutter clean

flutter pub get

dart run rename_app:main all="My App Name"
```
Note: the last renaming instruction, is useful to change the "distribution app name" with a new custom desired name ("My App Name" for example), and it's necessary only if you want to distribute the app to the public (for android store, ios store, etc.). Otherwise, for testing purposes, this specific renaming is optional.

In "lib/config.dart", change appName (facultative), and change apiBaseUrl, to connect to the correct relative server.  
Change "competenceTerritory" too, to inform the public about the zone where your app can operate. 

Compile the app, distribute it (or install it in the mobile/client device manually).

### Backend

Install miniconda:

[https://www.anaconda.com/download/success](https://www.anaconda.com/download/success)

On miniconda prompt (terminal), go to "quidalert/server/api_backend" folder and write:

```
conda env create -f environment.yml
```

```
conda activate quidalert_env
```

Install Postgres DBMS and create database "quidalert_db".

Change default settings in config.py file.

Copy ".env.example" to ".env" file and change the desired environment variables (useful for development).

For security reasons, the following variables are omitted in config.py. Instead, They must be set as system/service environment variables (in production) or in .env file (in development):

APP_MODE ("development" or "production")  
ADMIN_PASS  
OTP_PEPPER, EMAIL_PEPPER, JWT_SECRET_KEY

See ".env.example" for additional info about those variables.

Initialize alembic
```
alembic init migrations
```

Do all migrations (to build the entire database) from existent migration sources using the following command:
```
alembic upgrade head
```

IMPORTANT: at database empty, using the client flutter app, register the first user (admin) using your custom password you have placed in ADMIN_PASS environment variable.  
After that, you can reset the password at runtime using the client app functionality labeled "forgot password?", and choose a new desired password.

NOTE: User registration requires a smtp server to send activation code to user email address. So, in a real production system, set correct SMTP_HOST and SMTP_PORT in "config.py" file or as environment variables.  
For local testing/development purposes, we can set a fake local smtp server (see .env file) which prints the mail on the screen, as the following:

```
python -m aiosmtpd -n -l localhost:1025
```

### Debugging (run)

Clone repository 

Go to quidalert local folder and write the following command to open the entire project workspace with VS Code:

```
code .quidalert.code-workspace
```

NOTE: code workspace has been configured to ignore some useless folders from the programming IDE view (for example “build” directories)

To run (debug) client and server, go to VS Code menu -> View -> Run.
- Choose "Debug - Client (Flutter)" and click to play to debug the client.
- Choose "Debug - Server (Python)" and click to play to debug the server.

Obviously they can be executed together, in parallel, to test the entire system.

### Notes about production (run)

In the backend machine (behind nginx reverse proxy):

```
uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In nginx reverse proxy machine we do this, to forward the request id to the backend framework:

```
map $http_x_request_id $req_id {
    default $http_x_request_id;
    ""      $request_id;
}

proxy_set_header X-Request-ID $req_id;
```
To log the request_id in nginx too:

```
log_format main_ext '$remote_addr - $remote_user [$time_local] '
                   '"$request" $status $body_bytes_sent '
                   'req_id=$req_id '
                   '"$http_user_agent"';

access_log /var/log/nginx/access.log main_ext;
```
