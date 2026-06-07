# App info

This is a network alerting app: the user can send an alert/help request to the relative server, writing a description of the event. The server, based on the alert description, will send a push notification to the closest chief (the head of the rescue operations), and to all geolocalized nearby persons. 

To use this application, you must do the following steps:

- First of all, you must accept its "Legal Terms".

- After that, you must go to the competent local authority to declare (authorize) your email address.

- Then, you can do the account registration, using this app.

- Finally, you can do Login (the app will ask the acceptance of notifications and background gps location in "always allow")

## Grant location access 

To send a help (alert) request, the app will access your GPS location, instantly. 

To receive alerts from others nearby, the app needs to update your position in background approximately every 30 minutes, even when the app is closed, so gps location permission must be set to "always allow" (not "only allow when the app is open"). This background process will start automatically once you have successfully logged in, and will be immediately stopped if you decide to logout, to disconnect from the server. 

Note: to maximize battery efficiency, the system only sends updates when a significant change in location is detected.

Note: the server will temporarily store, for each user, only the last received gps position, not the complete tracking history. If the user does a logout, their gps location will no longer be refreshed, and after a few days the system will automatically delete this old location.

[Legal terms](/terms)

[Account registration](/register)

[Login](/login)