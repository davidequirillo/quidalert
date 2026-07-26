# Technical advice

- It is recommended to refresh at least once every 6 months to maintain the session, thus avoiding the needing of login, typing email and password.

- Remember to test your GPS position with the relative button, to be sure it's working correctly, so you can send alerts and receive nearby alerts. 

- At first launch or login, the app will ask for permission to receive notifications, permission to track your GPS location "while the app is in use" and then the app will ask to change the GPS tracking to "Allow all the time". Remember to set it to "Allow all the time", to give the application the ability to track the device GPS position even when the app is in background and not in use.

- To stop the background position tracking process and to not receive any notification anymore, you don't need to uninstall the app, but a "logout" is sufficient. However, doing so, you will no longer be able to receive or send any alerts, until a next eventual "login".

# Advice regarding alerts

- Remember to complete your profile so that chiefs can contact you if necessary, during an alert. Note: your address, email, phone number, and date of birth will not be visible to regular users, but only to chiefs and users with administrative privileges.

- To send an alert, you must fill in only the description field. The app uses built-in geopositioning systems to automatically get your location and associate it to the alert. However, to address some rare cases of inaccuracy and to make you easier to find, it would be better to give some information about the place where you are, if possible, adding it in the description. What the user enters in the form will be visible to all alerted users (chief and nearby users).

- The user, after sending an alert, will be able to write additional messages in the "messages" section (reachable on alert details page). So, don't worry if you accidentally forget to write something in the "description" field of the alert form. These messages will be visible to all alerted users (chief and nearby users). The alert chief can also post messages in the same section to provide alerted users with any helpful instructions.

# Vote, reliability and hero score

- The reliability score ranges from 0 to 100 and determines the alert radius. For example, if a user has a reliability score of 50, they can issue alerts with a radius reduced by half compared to the maximum. Those with a reliability score of zero cannot send alerts or vote on alerts for a while (but not forever, as the reliability score is increased slightly every 6 months until it reaches the maximum). However, in special cases, a user with administrative privileges can permanently report a user as unreliable.

- The hero score, on the other hand, has no specific purpose; it is merely symbolic: it is similar to the reliability score, but is increased according to the same criteria as the reliability score (it never decreases), except in rare punitive cases in which it is reset to zero. This score has no maximum limit.

- Users can rate alerts created by confirming or denying them. When the alert manager closes the alert, the reliability score of all users involved in the alert changes as follows.

- If the chief manager, upon closing, confirms the alert (since it is a genuine alert), the alert sender is rewarded, and their reliability score increases. All alerted users who confirmed the alert also receive a positive score, while those who denied the alert (mistakenly believing it to be false) are penalized (their reliability score decreases).

- If the chief manager, upon closing, denies the alert (since it is a false alert), the sender is penalized, and their reliability score decreases. All alerted users who confirmed the false alert are also penalized, while those who voted in agreement with the leader, denying the alert, are rewarded. In very serious cases of false alerts, the leader can deny the alert in a "punitive" manner, resetting the sender's trust score to zero and highly decreasing that of alerted users who confirmed the seriously false alert, while users who denied the alert receive a high bonus.

- Obviously, it is possible not to vote, or to vote "I don't know" if you are unsure, thus neither confirming nor denying the alert. In this case, there will be no penalty and no reward when the alert is closed.
