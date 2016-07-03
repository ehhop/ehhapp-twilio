# ehhapp-twilio

twilio implementation of the EHHOP-phone tree

This provides TwiML to a Twilio app. Phone tree greetings are in the `assets` directory. App is deployable to heroku.

## Deployment Details

To really run this thing you'll want the following resources in your infrastructure:

* Google OAuth 2.0
* A very special Google Spreadsheet
* Twilio
* Box
* sqllite
* redis

## Read the Documentation

We use Sphinx. To build the documentation, navigate into the docs directory, and run `sphinx-build -b html _src _build` where '\_src' and '\_build' are the source directory (where all the rst files are) and the build directory (where the html ends up) respectively.

If you have `make`, just `make html`.

## Contributing

You can test the setup by calling the demo number set up at 862-242-5952.

6/21/16: See ehhapp-twilio/issues for up-to-date TODOs.

2/8/2016: Left TODOS:
* DEBUG all the things
* test for secure message delivery flow
* improve options to reach a live person (who to call? queue?)
* secure message delivery needs to have options for X hours instead of next day, call back every day at same time if not delivered

9/4/2015: All paths have been enabled but there may still be some bugs.

### Getting started

To run it on localhost use:

`python run.py`
