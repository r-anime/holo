#!/usr/bin/env python3

# Metadata
name = "Holo"
description = "episode discussion bot"
version = "0.1"

# Imports
import os, sys
from pathlib import Path
import logging
from logging import info, warning, error
import database

# Ensure proper files can be access if running with cron
os.chdir(str(Path(__file__).parent.parent))

# Do the things
def main(module, db_name):
	db = database.living_in(db_name)
	
	try:
		if module == "episodefind":
			info("Finding new episodes")
			import module_find_episodes as m
			m.main(db)
		elif module == "showfind":
			info("Finding new shows")
			import module_find_shows as m
			m.main(db)
		elif module == "showupdate":
			info("Updating shows")
			import module_update_shows as m
			m.main(db)
		else:
			warning("This should never happen or you broke it!")
	except:
		e = sys.exc_info()[0]
		error("Unknown exception or error", e)
		db.rollback()
	
	db.close()
	
if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="{}, {}".format(name, description))
	parser.add_argument("--no-input", dest="no_input", action="store_true", help="run without stdin and write to a log file")
	parser.add_argument("-m", "--module", dest="module", nargs=1, choices=["episodefind", "showupdate", "showfind"], default="episodefind", help="runs the specified module")
	parser.add_argument("-d", "--database", dest="db_name", nargs=1, default="database.sqlite", help="use or create the specified database location")
	parser.add_argument("-v", "--version", action="version", version="{} v{}, {}".format(name, version, description))
	args = parser.parse_args()
	
	if args.no_input:
		from datetime import datetime
		log_file = datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + ".log"
		logging.basicConfig(
			format="%(asctime)s | %(levelname)s | %(message)s",
			datefmt="%Y-%m-%d %H:%M:%S",
			level=logging.INFO, filename=log_file)
	else:
		logging.basicConfig(format="%(levelname)s | %(message)s", level=logging.DEBUG)
	logging.getLogger("requests").setLevel(logging.WARNING)
	
	main(args.module, args.db_name)
