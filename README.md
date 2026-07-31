# Quidalert

*"Together we are stronger"*

NOTE: at the moment the project is under development.

Quidalert is a network alert manager: when the server receives an alert from a client (which runs the mobile app), it takes the alert description and the alert gps location, and then it sends a push notification to all geolocalized nearby clients and to the closest chief (called "chief manager"), to notify them about the alert.  
At this point a group chat will be automatically created by the system and will include the user who sent the alert, nearby users (these ones in read-only mode) and the "chief manager", who will be able to write messages to them, helping them.  
Obviously chief manager and nearby users will be able to see the alert gps coordinates with the related address in the map, to help the alert sender, if possible.

For this reasons, this project is mainly intended for the public entities/governements (municipalities, states, regions, countries), which can install the server-side components on a real cluster infrastructure, and can compile and offer the client app to end users.

For simple testing, the server-side system can also be installed on a single generic machine that simulates a cluster architecture, to which all clients will connect (in the client source code, in config.dart), just set the server name (or more precisely, API base url) before compiling and installing the client on a mobile device.

## 💡 Interesting features

User account registration will be admitted using a white list prepared in advance by admins and by officers.  
The whitelist, in addition to preventing spam or other similar abuses, is useful for preventing users outside the system territorial jurisdiction from registering and sending alerts, or more generally, it prevents fake alerts.

In addition, an algorithm has been implemented to punish fake alerts, using a voting mechanism whereby users who post fake alerts are punished by the chief manager (their reliability score is lowered, and when it reaches zero, they are no longer able to issue any alerts for a long type). Furthermore, alerted users who vote about an alert, are rewarded or punished based on the chief manager's closing vote (for example, if they confirm a fake alert, and the chief manager on the contrary deny it, their reliability score is lowered too).

Admin and officers can define users having specific roles, for example, medics, firefighters, policemen, alpinerescuers, etc. 
A little note about officers: unlike admins, who can edit everyone, officers have less privileges, for example they can only modify their own users, that is, the users they have whitelisted (in other words, the users they have authorized). Furthermore, officers can't promote other users to "admin", to "officer", or to "chief" (not even those authorized by them).

To put it simply, the fastest way to populate the database with a large number of users is the following: 
the administrator define the officers (for example the municipalities) adding their email to the white list, in bulk mode (using a simple CSV file), or adding them one by one. After that, officers can register their account using the app, and each of them can separately define their own citizens, medics, firefighter, etc. etc., white-listing them in bulk (CSV file) or one by one.  
This way, white-listed users can register their account whenever they want to login to the system.  
Administrator also define the chiefs (for example the "rescue operators" or "emergency workers"), white-listing them in the same way.  
Note: CSV file, used to add many emails in the whitelist in bulk, can be very simple, for example only one column, and many rows, where each row is the email address to insert in the whitelist. More complex CSV files are supported: the important thing is that one email address is present in each row.

Do you remember? Chief users are those who manage the alerts: when a generic user sends an alert, the server search the closest chief in the territory, and the nearby users residing in a certain radius (1 km) from the alert sender location.  
A note: chief users can also create general alerts or managed alerts with custom gps location (writing the alert gps coordinates manually, to target a specific area, to notify nearby users who are within that area).

Chief users will also be able to expand an existing alert, increasing the radius to many kilometers, with the aim to notify more specialized users (for example, expand the alert to all medics in 10 km, expand the alert to all firefighters in 50 km, etc. etc.).

## ⛓️ The architecture

The backend (server-side architecture) can obviously be composed of many docker containers working in clusters with the aim to distribute the processing load: for example, 1 reverse proxy (load balancer), 10 FastApi, 5 dbms (Postgres), 1 RedisCluster (a cluster of 16 nodes, working in parallel).

The reverse proxy (ex. "nginx") will be seen by the client as the only server to connect to.

## 🌍 Notes about GPS location

When the user does a "gps location test" (pressing the relative button), or when he sends a help (alert) request, the client app will access the device GPS coordinates, instantly, using the relative platform calls, and after that it will translate the coordinates to an address, using default platform free services. If it's an alert request, the position will be sent to the server.

To receive alerts from others nearby, the app needs to update the user position locally (only gps coordinates in this case, without address translation) and send it to the server, even when the app is closed. This background process will start automatically once the user does a successful login, and will be immediately stopped if he decides to logout from the server.

Note: to maximize the device battery efficiency and to avoid server overloading, the app only requests a position update when a significant change in location is detected and enough time is passed.

Note: the server will temporarily store, for each user, only the last received gps position, not the complete tracking history. If the user does a logout, their gps location will no longer be refreshed, and after a few days the system will automatically delete this old location.

## 🔌 Installation

See INSTALL.md

## 🔒 Disclaimer

Quidalert must be used in compliance with the existing laws and regulations. The author assumes no responsibility for any damage caused by unethical, improper, incorrect, or unlawful use of the software, or by the inability to use it, or by any malfunction of it.

The author proposes this project as it is (only source code and textual documentation), without providing the server physical infrastructure on which the software will run, and without providing the client app. 

The author does NOT collect any personal or sensible data from the end users of this software, from the server, or from any machines on which it will be installed.

User personal data, during registration and use of the software, will be collected by the hypothetical third-party who will decide to install the software in their own infrastructure and open it to the public, distributing the client app to the public.  
Therefore, end users must refer to the terms of use and privacy policy that will be returned by that hypothetical third-party server, and shown on the client device upon initial connection.

## ⚖️ License & Commercial Dependencies

This project is licensed under the **GNU GPL v3** with a specific exception for hardware-optimized location tracking. See the LICENSE file for details.  
Copyright (C) 2025-2026&nbsp;&nbsp;Davide Quirillo

### The "Flutter Background Geolocation" Exception
This application utilizes the [flutter_background_geolocation](https://github.com/transistorsoft/flutter-background-geolocation) plugin by Transistor Software. 
* **The Code:** My original source code is 100% Open Source under the GPL v3.
* **The Plugin:** While the plugin's Dart wrapper is open, its native SDKs require a **commercial license** for production/release builds.

**Important:** In accordance with Section 7 of the GPL v3, I have granted a specific exception in the `LICENSE` file. This allows you to compile and distribute this app with the Transistor Software SDK without violating the GPL, provided that all other parts of the application remain under the GPL v3. 

*Note: You are responsible for acquiring your own commercial license from Transistor Software if you intend to release a production version of this app.*
