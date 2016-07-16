# Journal

## 07/09/16

Tomorrow!

## 07/08/16

We can use the [entr][entr] utility to watch for changes to the \_src directory and automatically run `make html` as files change, i.e. when we log more stuff to the journal as the case may be. To make this efficient, you have to be able to dedicate a tmux pane or shell window to entr (or know how to manage background processes without forgetting about them). Then, go ahead and `cd` into the `docs` directory and run the following:

`ls -d _src/* | entr make html`

You pipe a list of filenames to `entr`, which will run `make html` whenever it detects a file change. To save you the headache of having to refresh the browser window you have open to the docs, you can also run in a different pane:

`ls -d _build/html/*.html | entr reload-browser $BROWSER_OF_CHOICE`

This sends a key-press to the browser and will refresh whatever the active tab is. This assumes the tab is open to wherever you are hosting the docs (usually localhost:8000 if you are using a Python's built-in `SimpleHTTPServer`).

## 07/07/16

Circle CI automatically spins up an Ubuntu 14.04 box that clones our repo, installs a virtualenv, reads our requirements.txt, and then executes a command to run some tests. We can configure almost any step of this process through the admin dashboard and a circle.yml file.

pytest is a Python package that extends unittest by offering us a cleaner syntax with which to write tests, some autoloading and finding of tests, and more. Relevant to running a tool like Circle CI is the question of how pytest finds tests. This goes as follows:

---

[entr]: http://entrproject.org/

