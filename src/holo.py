#!/usr/bin/env python3

# Metadata
name = "Holo"
description = "episode discussion bot"
version = "0.1"

# Imports
import os
import logging
from logging import debug, info, warning, error, exception
from services import crunchyroll

# Ensure proper files can be access if running with cron
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def main():
	cr = crunchyroll.Service()
	#episode = cr.get_latest_episode("active-raid")
	#episode = cr.get_latest_episode("kiznaiver")
	episode = cr.get_latest_episode("aokana-four-rhythm-across-the-blue")
	#episode = cr.get_latest_episode("tabi-machi-late-show")
	print(episode)
	
if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="{}, {}".format(name, description))
	parser.add_argument("--pasloe", dest="no_input", action="store_true", help="run without stdin and write to a log file")
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
	
	main()
