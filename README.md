# ehhapp-twilio

twilio implementation of the EHHOP-phone tree

This provides TwiML to a Twilio app. Phone tree greetings are in the `assets` directory. App is deployable to heroku.

You can test the setup by calling the demo number set up at 862-242-5952.

9/4/2015: All paths have been enabled but there may still be some bugs.
2/8/2016: Left TODOS:
* DEBUG all the things
* test for secure message delivery flow
* improve options to reach a live person (who to call? queue?)
* secure message delivery needs to have options for X hours instead of next day, call back every day at same time if not delivered

## Deployment Details

To really run this thing you'll want the following resources in your infrastructure:

* Google OAuth 2.0
* A very special Google Spreadsheet
* Twilio
* Box
* sqllite
* redis
