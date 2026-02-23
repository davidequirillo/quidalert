# Quidalert

*"Together we are stronger"*

NOTE: at the moment, this project is in an early non-functional stage, and is under development.

Quidalert is a network alert manager: when the server receives an alert from a connected client (mostly a mobile device, or a desktop device), it takes some decisions based on alert description, and then it sends a push notification to all geolocalized nearby clients.
Clients can receive different notification instructions based on user account role (citizen, military, police, firemen, civil protection, medics).

This system can be largely extended to manage virtually all alert types, in order to have a security defensive system that works 360 degrees, giving specific real-time instructions to user groups when an alert happens, receiving signals from network sensors (for example, smoke or meteo sensors), eventually sending active commands to some devices (patrol drones, or others), to help and lead peoples to safe zones, and working in a parallel way too, if many alert happen at the same time. Ideally the system could use artificial intelligence ("algorithmic" machine alearning or neural networks) to optimize the active response to any events.

For this reasons, this project is intended for the public entities/governements (municipalities, states, regions, countries), which can install the server on a real machine or infrastructure, and can compile and redistribute the client to end users. 

For simple testing, the server-side system can also be installed on a generic machine, to which all clients will connect (just set the server name in the client configuration file before compiling and installing the client on a mobile or desktop device).

## 💡 Concepts

Each user is allowed to send an alert, but we must find a solution about alert validation (user credibility), for example a system based on votes.

User account registration will be admitted using a white list prepared by admins and by officers.  
The whitelist, in addition to preventing spam or other similar abuses, is useful for preventing users outside the system territorial jurisdiction from registering and sending alerts, or more generally, it prevents fake alerts.

Admin and officers can modify (promote) other users, for example they can change their role (promoting them from "citizen" to "firefighter").  
A note about officers: unlike admins, who can edit everyone, officers can only modify their users, that is, the users they have whitelisted. Furthermore, officers can't promote other users (not even those authorized by them) to "admin", to "officer", or to "chief".

Chief users will connect to the server using the desktop version of the client app, to do additional real-time operations (such as sending a message to specific units, sending an alert to all users inside a location radius, viewing streaming video coming from a user device or from a drone flying over the event location, etc.).

Idea of a server-side architecture: 1 server (reverse proxy, ex. "nginx") and 3 backends (api backend, website backend, streaming signaling server).  
The reverse proxy will be seen by the client as the only server to connect to.
This architecture can obviously be composed of many docker (or similar) containers working in clusters: for example, 1 reverse proxy (load balancer), 10 FastApi, 3 dbms (Postgres), 3 dbms (Redis), 1 website and 1 streaming server.

## 🌍 Notes about GPS location

When the user does a "gps location test" (pressing the relative button), or when he sends a help (alert) request, the client app will access the device GPS coordinates, instantly, using the relative platform calls, and after that it will translate the coordinates to an address, using default platform free services. In case of alerts, the position will be sent to the server.

To receive alerts from others nearby, the app needs to update the user position locally (only gps coordinates in this case, without address translation) and send it to the server, approximately every 30 minutes, even when the app is closed. This background process will start automatically once the user does a successful login, and will be immediately stopped if he decides to logout from the server.

Note: to maximize the device battery efficiency and to avoid server overloading, the app only requests a position update when a significant change in location is detected and enough time is passed.

Note: the server will store, for each user, only the last received gps position, not the complete history.

## 🔌 Installation

See INSTALL.md

## 🔒 Disclaimer

Quidalert must be used in compliance with the existing laws and regulations. The author assumes no responsibility for any damage caused by unethical, improper, incorrect, or unlawful use of the software, or by the inability to use it, or by any malfunction of it.

The author proposes this project as it is (only source code and textual documentation), without providing the physical infrastructure on which the software will run.

The author does NOT collect any personal or sensible data from the end users of this software, from the server, or from any machines on which it will be installed.

User personal data, during registration and use of the software, will be collected by the server to which the mobile application (the client) will be connected at runtime. Therefore, please refer to the terms of use and privacy policy that will be returned by that server, and shown on the client device upon initial connection.

## 📄 License

This project is released under the GPLv3 license.
See the LICENSE file for details.
