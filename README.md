# Dynalert

*"Together we are stronger"*

NOTE: at the moment, this project is in an early non-functional stage, and is under development.

Dinalert is a network alert manager: when the server receives an alert from a connected client (mostly a mobile device), it takes some decisions based on alert description, and then it sends a push notification to all geolocalized nearby clients.
Clients can receive different notification instructions based on user account type (citizen, military, police, firemen, civil protection, medics).

This system can be largely extended to manage virtually all alert types, in order to have a security defensive system that works 360 degrees, giving specific real-time instructions to user groups when an alert happens, receiving signals from network sensors (for example, smoke or meteo sensors), eventually sending active commands to some devices (patrol drones, or others), to help and lead peoples to safe zones, and working in a parallel way too, if many alert happen at the same time. Ideally the system could use artificial intelligence ("algorithmic" machine alearning or neural networks) to optimize the active response to any events.

For this reasons, this project is intended for the public entities/governements (municipalities, states, regions, countries), which can install the server on a real machine or infrastructure, and can compile and redistribute the client to end users. 

For simple testing, the server-side system can also be installed on a generic machine, to which all clients will connect (just set the server name in the client configuration file before compiling and installing the client on a mobile or desktop device).

## 💡 Concepts

Each user is allowed to send an alert, but we must find a solution about alert validation (user credibility), for example a system based on votes for standard users and manual assignment for specific user groups (for example max reliability for alerts coming from civil protection users, public officers can give max reliability to some standard users, etc.).

Admins will connect to the server via a desktop app to do additional real-time operations (such as sending a message to specific users, viewing streaming video coming from a client or from a drone flying over the event location).

Idea of server-side architecture: 1 server (nginx) and 3 backends (api backend, website backend, streaming signaling server). 

## 🔌 Installation

See INSTALL.md

## 🔒 Disclaimer

Dynalert must be used in compliance with the existing laws and regulations. The author assumes no responsibility for any damage caused by unethical, improper, incorrect, or unlawful use of the software, or by the inability to use it, or by any malfunction of it.

The author proposes this project as it is (only source code and text documentation), so the author does NOT collect any personal or sensible data from the end users of this software, from the server, or from any machines on which it will be installed.

See "disclaimer.md" file for all details.

## 📄 License

This project is released under the GPLv3 license.
See the LICENSE file for details.
