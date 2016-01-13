#!/usr/bin/env python3

# Metadata
name = "Holo"
description = "episode discussion bot"
version = "0.1"

# Imports
import os
from pathlib import Path

from data import database
import services

# Ensure proper files can be access if running with cron
os.chdir(str(Path(__file__).parent.parent))

# Utilities

def get_database(the_database):
	db = database.living_in(the_database)
	if db:
		db.register_services(services.get_service_handlers())
		#db.setup_test_data()
	return db

# Do the things
def main(config):
	from logging import info, warning, error, exception
	
	# Set things up
	db = get_database(config.database)
	if not db:
		error("Cannot continue running without a database")
		return
	
	# Run the requested module
	try:
		if config.module == "episodefind":
			info("Finding new episodes")
			import module_find_episodes as m
			m.main(config, db)
		elif config.module == "showfind":
			info("Finding new shows")
			import module_find_shows as m
			m.main(config, db)
		elif config.module == "showupdate":
			info("Updating shows")
			import module_update_shows as m
			m.main(config, db)
		else:
			warning("This should never happen or you broke it!")
	except:
		exception("Unknown exception or error")
		db.rollback()
	
	db.close()
	
if __name__ == "__main__":
	# Parse args
	import argparse
	parser = argparse.ArgumentParser(description="{}, {}".format(name, description))
	parser.add_argument("--no-input", dest="no_input", action="store_true", help="run without stdin and write to a log file")
	parser.add_argument("-m", "--module", dest="module", nargs=1, choices=["episodefind", "showupdate", "showfind"], default="episodefind", help="runs the specified module")
	parser.add_argument("-c", "--config", dest="config_file", nargs=1, default="config.ini", help="use or create the specified database location")
	parser.add_argument("-d", "--database", dest="db_name", nargs=1, default=None, help="use or create the specified database location")
	parser.add_argument("-s", "--subreddit", dest="subreddit", nargs=1, default=None, help="set the subreddit on which to make posts")
	parser.add_argument("-v", "--version", action="version", version="{} v{}, {}".format(name, version, description))
	args = parser.parse_args()
	
	# Load config file
	import config as config_loader
	c = config_loader.from_file(args.config_file)
	
	# Override config with args
	c.module = args.module
	if args.db_name is not None:
		c.database = args.db_name
	if args.subreddit is not None:
		c.subreddit = args.subreddit
	
	# Start
	import logging
	if args.no_input:
		from datetime import datetime
		log_file = "logs/"+datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + ".log"
		logging.basicConfig(
			format="%(asctime)s | %(levelname)s | %(message)s",
			datefmt="%Y-%m-%d %H:%M:%S",
			level=logging.INFO, filename=log_file)
	else:
		logging.basicConfig(format="%(levelname)s | %(message)s", level=logging.DEBUG)
	logging.getLogger("requests").setLevel(logging.WARNING)
	
	from logging import warning
	err = config_loader.validate(c)
	if err:
		warning("Configuration state invalid: {}".format(err))
	main(c)
