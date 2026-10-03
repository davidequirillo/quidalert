# Client usage tutorial

## Start application

When you first start the app, it asks for permission to send notifications.

<p align="center">
  <img src="client/screenshots/allow_notifications.png" alt="Allow notifications screenshot" width="256">
</p>

This permission must be allowed because alerts sent to the server are propagated to the "chief" and nearby users who are notifiable (device registered to accept notifications), so this permission is essential, not only to receive notifications, but also to technically be included in an alert. Click on "Allow".

The general information page will open. Read it carefully, as it contains useful details on how the system works and what you need to do to use it.

At the bottom of the page, you can click on "Legal Terms": this will open a page containing the terms and conditions of use, which you will need to accept after reading it.

NOTE: The same page can be reached by clicking on the menu at the top left.

<p align="center">
  <img src="client/screenshots/menu.png" alt="Menu screenshot" width="256">
</p>

After accepting the legal terms, the login page will open. To log in, you must be registered (have an account on the server), so click on the "Don't have an account? Sign up" link.

## Registration

Registration has one requirement, as explained on the "Info" page: the user's email address must have been authorized by the administrator or by the "officer" user, i.e. it must have been included in a white list, so make sure you have obtained this authorization.

Registration is simple: simply fill out the short form (first name, last name, email address, password). You must set a strong password, containing at least one uppercase character, one lowercase character, a symbol, and a number, and it must be sufficiently long.

<p align="center">
  <img src="client/screenshots/registration.png" alt="Registration screenshot" width="256">
</p>

Once you confirm your registration, an activation link will be sent to your email inbox. You must open the email and click on the activation link to complete the registration, so your account will be activated and you can do login.

NOTE: the activation link received by email expires after 24 hours. After this time, you will need to reopen the registration page, fill out the form again, and receive a new activation link.

## Login and 2FA

The login page can be reached from the "Info" page or from the menu (top left button).

You must enter the email address and password you chose during registration. The password can be clearly displayed as you type it for your convenience by enabling the appropriate checkbox.

<p align="center">
  <img src="client/screenshots/login.png" alt="Login screenshot" width="256">
</p>

Click Login. This will open another page titled "2FA," where you'll need to enter the verification code that will be sent to you shortly via email. Don't worry: this verification code is valid for 10 minutes, so you have plenty of time to open the email, read the code (or write it down on a piece of paper if you're comfortable doing so), and then enter it on the "2FA" verification page.

<p align="center">
  <img src="client/screenshots/2fa.png" alt="2FA screenshot" width="256">
</p>

Be careful, though, because you can't enter the verification code incorrectly more than three times, otherwise the login process will be blocked for 24 hours, and you'll have to try again the following day.

NOTE: the login procedure needs to be done only once, after which the system remembers the user's session for a long time.

## Grant geolocalization permissions

Now, be careful: immediately after logging in, a warning window will open, explaining that for the geolocation system to function properly, you must grant it the following permissions:
- precise GPS location
- allow physical activity
- allow all the time
- "unrestricted" battery

NOTE: the following procedure is simple but a bit tedious. Don't worry, though, because you only need to do it the first time, if completed correctly.

### Grant precise GPS location

<p align="center">
  <img src="client/screenshots/gps_precise.png" alt="GPS precise screenshot" width="256">
</p>

Click on "Always" (if displayed) or click on "While using the app".

### Allow physical activity

<p align="center">
  <img src="client/screenshots/gps_physical_activity.png" alt="Physical activity screenshot" width="256">
</p>

Allow physical activity (motion tracking): click on "Allow".

### Allow background GPS

To be notified about nearby alerts at any time, the device needs to periodically detect the user's GPS location in the background, even when the application has been closed, so you need to allow background GPS location detection by clicking on "Allow all the time".

<p align="center">
  <img src="client/screenshots/gps_all_the_time.png" alt="GPS all the time screenshot" width="256">
</p>

...and then in the settings page that opens automatically, you will still need to switch to "allow all the time". Then, after you are sure, you can click the "back" button on the top left to return to the app.

<p align="center">
  <img src="client/screenshots/gps_all_the_time_switch.png" alt="GPS all the time switch screenshot" width="256">
</p>

Now the device will automatically detect your GPS location occasionally, typically only when you've moved significantly (250 meters on foot, or a few kilometers or more when driving at car speeds) or when you experience a change in motion (movement followed by stationary, e.g., "I go to a café and sit at a table"), thus minimizing device battery consumption.

However, to ensure this background process isn't interrupted by the device power management mechanism, you should set the battery to "Unrestricted" in the "Battery" section of the system settings relative to Quidalert app. See the following section.

### Battery unrestricted

Click OK in the warning window that explains the "unrestricted" battery function.

The operating system settings page, specific to the Quidalert app, will now open.

<p align="center">
  <img src="client/screenshots/system_settings_quidalert_1.png" alt="System settings for Quidalert part1 screenshot" width="256">
</p>

Scroll down slightly and you'll find the "Battery" or "App Battery Usage" option.

<p align="center">
  <img src="client/screenshots/system_settings_quidalert_2.png" alt="System settings for Quidalert part2 screenshot" width="256">
</p>

Click to "Battery" or "App battery usage", and then switch to "Unrestricted"

<p align="center">
  <img src="client/screenshots/app_battery_usage.png" alt="App battery unrestricted screenshot" width="256">
</p>

Now you can go back by clicking on the "back" button in the top left corner, and then on the "back" button again until you return to the Quidalert app home page.

## Home page

This is the Quidalert home page

<p align="center">
  <img src="client/screenshots/home_page.png" alt="App battery unrestricted screenshot" width="256">
</p>

## Advice page

Remember to read the tips page (Quidalert home page, "Advice" button). It's very helpful, and contains important info regarding the session maintenance, the technical functioning of the geolocation system, and other information regarding alerts.

## Create an alert

To be continued... Under construction...

## For admins

Under construction...