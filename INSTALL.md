# Installation

## End-Users

### Client

Download Dynalert App from the app store (Play Store for Android devices or Apple Store for iOS devices). (under construction)

### Server (for admin)

(under construction)

## Developers only 

Install Git for Windows

[https://git-scm.com/install/windows]: (https://git-scm.com/install/windows)

Install VSCode IDE

[https://code.visualstudio.com/]: (https://code.visualstudio.com/)

### Client

Install Flutter SDK

[https://docs.flutter.dev/get-started]: (https://docs.flutter.dev/get-started)

### Server

Install miniconda:

[https://www.anaconda.com/download/success]: (https://www.anaconda.com/download/success)

On miniconda prompt (terminal), go to dynalert folder and write:

```
conda env create -f server/environment.yml
```

```
conda activate dynalert_env
```

### Debugging (run)

Clone repository 

Go to dynalert local folder and write the following command to open the entire project workspace with VS Code:

```
code .dynalert.code-workspace
```

NOTE: code workspace has been configured to ignore some useless folders from the programming IDE view (for example “build” directories)

To run (debug) client and server, go to VS Code menu -> View -> Run.
- Choose "Debug - Client (Flutter)" and click to play to debug the client.
- Choose "Debug - Server (Python)" and click to play to debug the server.

Obviously they can be executed together, in parallel, to test the entire system.
