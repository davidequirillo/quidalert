# App info

This is a network alerting app, useful to receive help: the user can send an alert/help request to the server, writing a description of the event. The server, will propagate the alert, sending a notification to the closest chief (the head of the rescue operations), and to all geolocalized nearby persons. 

To use this application, you must do the following steps:

- You must go to the competent local authority to declare (authorize) your email address.

- Then, you can do the account registration, using this app.

- Finally, you can do Login.

## Grant location access 

To send a help (alert) request, the app will access your GPS location, instantly. 

Conversely, to receive alerts from other users nearby, the app needs notifications enabled and to periodically update your GPS location in the background, even when the app is hidden or closed.  
The user will then be asked for the following permissions:
- Allow notifications
- Precise GPS location (and then "Allow all the time")
- Allow motion activity tracking
- You will be asked to set the battery mode to "Unrestricted" in the app's settings panel.

This background tracking process will start automatically only after you have successfully logged in, and will be stopped immediately if you decide to disconnect from the server (logout).

Note: To ensure maximum battery life, the system almost never queries the GPS location system when stationary, while when moving it is optimized to only detect GPS positions for significant distances (at least 250 meters). Additionally, the distance traveled required to trigger GPS fixes progressively increases as speed increases, so at high speeds the device will not continuously query the GPS, but only occasionally.

Note: the server will temporarily store only the last GPS location received for each user, not their entire tracking history. If the user logs out, their GPS location will no longer be updated, and after a few days, the server will automatically delete this old location.

## [Login](/login)

## [Account registration](/register)

## [Legal terms](/terms)
