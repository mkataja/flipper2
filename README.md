Flipper ircbot
==============

Requirements
------------

* Python 3.5
* [irc](http://pypi.python.org/pypi/irc) - IRC protocol client library for Python 
* [SQLAlchemy](http://www.sqlalchemy.org/)
* [pytz](http://pytz.sourceforge.net/) - World Timezone Definitions for Python
* [Beautiful Soup 4](http://www.crummy.com/software/BeautifulSoup/)
* [Flask](http://flask.pocoo.org/)

### Installing with pip

    pip install -r requirements.txt

You also need a driver for your database of choice. For PostgreSQL:

    pip install psycopg2

### Optional dependencies

* [Data files](../../../flipper_data) for importer scripts and talkcommand.

#### Importing data files using scripts

    $ cd scripts
    $ PYTHONPATH=../src python markov_import_flat_file.py
    $ PYTHONPATH=../src python markov_import_xml.py
