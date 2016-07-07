#######
Journal
#######

Circle CI automatically spins up an Ubuntu 14.04 box that clones our repo, installs a virtualenv, reads our requirements.txt, and then executes a command to run some tests. We can configure almost any step of this process through the admin dashboard and a circle.yml file.

pytest is a Python package that extends unittest by offering us a cleaner syntax with which to write tests, some autoloading and finding of tests, and more. Relevant to running a tool like Circle CI is the question of how pytest finds tests. This goes as follows:


