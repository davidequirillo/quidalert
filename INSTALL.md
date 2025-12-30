# Installation

## Technical users and developers

Install Git for Windows

[https://git-scm.com/install/windows](https://git-scm.com/install/windows)

Install VSCode IDE

[https://code.visualstudio.com/](https://code.visualstudio.com/)

### Client

Install Flutter SDK

[https://docs.flutter.dev/get-started](https://docs.flutter.dev/get-started)

On terminal, go to "quidalert/client/flutter_app" folder:

Change apiBaseUrl in "lib/config.dart", to connect to the correct server, (TODO: TLS/SSL certificate support). Compile the app and distribute it (or install it in the client device).

### Server

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

Copy ".env.example" to ".env" file and change environment variables (useful for development).

Change settings for production in config.py file.

Initialize alembic
```
alembic init migrations
```

Do all migrations (to build the entire database) using migration sources previously created from the models
```
alembic upgrade head
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
