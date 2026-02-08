# Installation

## Technical users and developers

Install Git for Windows

[https://git-scm.com/install/windows](https://git-scm.com/install/windows)

Install VSCode IDE

[https://code.visualstudio.com/](https://code.visualstudio.com/)

Install Docker Desktop for Windows

[https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)

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

Note: in some cases, in windows operative system, you must enable "developer mode" (in windows settings), otherwise the command "flutter pub get" could return an error.

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

Change default settings in config.py file, and read the comments contained in the file, to know how to proceed with the env variables.

Copy ".env.example" to ".env" file and change the desired environment variables (useful for development).

See ".env.example" for additional info about those variables.

Postgres DBMS, SMTP server (useful to send mail notification to users), minIO server (s3 bucket for file upload), are configured as containers. They are defined in "docker-compose.yml" file, so read this file for more info about them.
To download them automatically, and start them, you only need to write this single command:
```
docker-compose up -d
```

Now you will have all the required servers ready to receive requests.

Do all migrations to postgres database (to build the entire database tables) from existent migration sources using the following command:
```
alembic upgrade head
```

Now you can start the backend and the client via VSCode launcher (see debugging/run section).

IMPORTANT: at database empty, using the client flutter app, register the first user (admin) using your custom password you have placed in ADMIN_PASS environment variable.  
After that, you can reset the password at runtime using the client app functionality labeled "forgot password?", and choose a new desired password.

NOTE: user registration, login, reset, require a smtp server to send some mail notifications to user email address. So, in a real production system, set the correct SMTP_HOST and SMTP_PORT in "config.py" file, or as environment variables.  
For local testing/development purposes, there is already a "fake" local smtp server (defined as a container in docker-compose.yml). You can view the mail messages sent to the user using its web interface available at the following url: "http://localhost:8025".

### Debugging (run)

Clone repository 

Go to quidalert local folder and write the following command to open the entire project workspace with VS Code:

```
code .quidalert.code-workspace
```

NOTE: code workspace has been configured to ignore some useless folders from the programming IDE view (for example “build” directories)

To run (debug) client and server, go to VS Code menu -> View -> Run.
- Choose "Debug - Client (Flutter) Windows" and click to play to debug the client.
- Choose "Debug - Server (Python)" and click to play to debug the server.

Obviously they can be executed together (client and server), in parallel, to test the entire system.

NOTES
- "Debug - Client (Flutter) Windows" requires Microsoft Visual Studio (C++ desktop development package).   
- "Debug - Client (Flutter) Android" requires Android SDK

Flutter Web device (Chrome) is not completely supported at the moment.

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
