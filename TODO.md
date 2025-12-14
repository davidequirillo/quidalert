## Notes

- There's no rush (avoid anxiety),

- All developers should use the same environment as much as possible (VS Code IDE, Android emulator, Chrome, conda, etc.) for the following reasons: 
    - it's the most widely used and supported environment at the moment, and it's "light".
    - it's simpler and more convenient to manage (development and debugging tasks are already defined by us, and the Git repository is more easy to manage)

- Don't ask questions to AI/LLM that give away clues relative to this project, for now.

# TODO

- The user opens the mobile application for the first time and the general disclaimer appears in a page. It must be accepted to go on (it appears only the first time, after that the user acceptance is stored). 

- REQUIREMENT: we must do a choice (use a unique server or two server, one for api calls and one for effective traffic). 

- The user opens the mobile application (after the general disclaimer), and a page is shown, in which the user must insert the server name and port. So, the mobile application will do an api call to the server, to get the terms of use and privacy policy contents. The user must accept them to go on. The user choice is stored.

- After that, a login page appears. In the login page there is a button to change the server. There is also a link to reset password, and a link to register the account (registration api).

- Implement the registration page

- Implement the reset password function (it sends an activation code to the user)

- Implement the activation procedure (to complete user registration)

- Implement Login procedure (details to define, under construction).

- A simple testing system (to test the server and the client. For example a script that calls the sub-test systems, one for the server, and one for the client)

- After the login, the application listen continuously for push notifications (alarms coming from the server)

- Alarm page: this is the main page (the home page, after login). It has only 1 text field (similar to a textarea). It's the "description" field, "OK" button, and "Reset" button. It has an attachment button and a "camera" button (respectively to attach a file or to make a photo).
