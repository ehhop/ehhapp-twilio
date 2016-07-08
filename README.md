[![CircleCI](https://circleci.com/gh/ehhop/ehhapp-twilio/tree/master.svg?style=svg)](https://circleci.com/gh/ehhop/ehhapp-twilio/tree/master)

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

## Contributing

You can test the setup by calling the demo number set up at 862-242-5952.

6/21/16: See ehhapp-twilio/issues for up-to-date TODOs.

2/8/2016: Left TODOS:
* DEBUG all the things
* test for secure message delivery flow
* improve options to reach a live person (who to call? queue?)
* secure message delivery needs to have options for X hours instead of next day, call back every day at same time if not delivered

9/4/2015: All paths have been enabled but there may still be some bugs.

### Python Version

This was developed on a Debian 7 server using Python 2.7.11 packages. It is recommended that anyone contributing to this codebase use [pyenv][pyenv] to manage different python versions. Until tests are written verifying compatability across different python versions, the `.python-version` file specifies which version this code is intended to run under.

### Virtualenv

Packages can and should be isolated from system site-packages in a virtualenv. Run `virtualenv venv` and then `source venv/bin/activate` before doing anything else.

### Dependencies

We use the `requirements.txt` file to specify required packages. Run `pip install -r requirements.txt` to get what you need.

### Run Tests

Test are currently written in full-blow `unittest` syntax. Our CI tool will run `py.test tests.py`. Why have we chosen [pytest][pytest] over [nose][nose]? It "feels" better maintained.

### Read the Documentation

We use Sphinx. To build the documentation, navigate into the docs directory, and run `sphinx-build -b html _src _build` where '\_src' and '\_build' are the source directory (where all the rst files are) and the build directory (where the html ends up) respectively.

If you have `make`, just `make html`.

### Launch It

To run it on localhost use:

`python run.py`

---

<!-- Links -->
[pyenv]: https://github.com/yyuu/pyenv
[pytest]: http://pytest.org/latest/
[nose]: http://nose.readthedocs.io/en/latest/
