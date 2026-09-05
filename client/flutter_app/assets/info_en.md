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

Note: the system is optimized to locally detect only GPS positions related to significant movements (about 250 meters), thus ensuring maximum battery and data savings, especially when the user remains in the same area. Furthermore, not all GPS positions detected by the device will be sent to the server, but only the most significant ones (stationary positions preceded by long movements, e.g., "the user goes to the bar and sits at a table." Only this last position will be sent to the server, only once).

Note: the server will temporarily store only the last GPS location received for each user, not their entire tracking history. If the user logs out, their GPS location will no longer be updated, and after a few days, the system will automatically delete this old location.

[Legal terms](/terms)

[Account registration](/register)

[Login](/login)