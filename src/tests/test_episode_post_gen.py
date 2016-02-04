import logging
from logging import error, info

logging.basicConfig(format="%(levelname)s | %(message)s", level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)

# Load config file
import os
from pathlib import Path
os.chdir(str(Path(__file__).parent.parent.parent))

import config as config_loader
config = config_loader.from_file("config.ini")

from data import database
import services

# Set things up
db = database.living_in(config.database)
if not db:
	error("Cannot continue running without a database")
	exit()

services.setup_services(config)

# Do the things

from datetime import datetime
from module_find_episodes import _create_post_contents
from data.models import Episode

stream = db.get_stream(id=1)
show = db.get_show(stream=stream)
date = datetime.now()
episode = Episode(6, "Test Episode", "http://redd.it/12345", date)
title, body = _create_post_contents(config, db, show, stream, episode)

#info("Title:\n\n{}\n\n".format(title))
#info("Body:\n\n{}\n\n".format(body))
