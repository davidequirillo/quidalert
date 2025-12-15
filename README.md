# Dynalert

*"Together we are stronger"*

Dinalert is a network alert manager: when the server receives an alert from a connected client (mostly a mobile device), it takes some decisions based on alert description, and then it sends a push notification to all geolocalized nearby clients.
Clients can receive different notification instructions based on user account type (citizen, military, police, firemen, civil protection).

This system can be largely extended to manage virtually all alert types, in order to have a security defensive system that works 360 degrees, giving specific real-time instructions to user groups when an alert happens, receiving signals from network sensors (for example, smoke or meteo sensors), eventually sending active commands to some devices (patrol drones, or others), to help and lead peoples to safe zones, and working in a parallel way too, if many alert happen at the same time. Ideally the system could use artificial intelligence ("algorithmic" machine alearning or neural networks) to optimize the active response to any events.

The server side system can be installed on a generic host, at which all properly configured clients will connect to (it’s sufficient to set server name in the client config file before installing the client on the relative device). 

## 💡 Concepts

Each user is allowed to send an alert, but we must find a solution about alert validation (user credibility), for example a system based on votes for standard users and manual assignment for specific user groups (for example max reliability for alerts coming from civil protection users, public officers can give max reliability to some standard users, etc.).

Admins will connect to the server via a desktop app to do additional real-time operations (such as sending a message to specific users, viewing streaming video coming from a client or from a drone flying over the event location).

## 🔌 Installation

See INSTALL.md

## 🔒 Ethical Disclaimer

Dynalert must be used in compliance with the laws and regulations in the place where it will be installed. See "disclaimer.md" file for details

## 📄 License

This project is released under the GPLv3 license.
See the LICENSE file for details.
