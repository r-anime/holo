from logging import debug, info, warning, error

import services

def main(config, db, **kwargs):
	_check_show_lengths(config, db, update_db=not config.debug)
	
def _check_show_lengths(config, db, update_db=True):
	shows = db.get_shows(missing_length=True)
	for show in shows:
		info("Updating episode count of {} ({})".format(show.name, show.id))
		length = None
		
		# Check all info handlers for an episode count
		# Some may not implement get_episode_count and return None
		for handler in services.get_link_handlers().values():
			info("  Checking {} ({})".format(handler.name, handler.key))
			
			# Get show link to site represented by the handler
			site = db.get_link_site(key=handler.key)
			link = db.get_link(show, site)
			if link is None:
				error("Failed to create link")
				continue
			
			# Validate length
			new_length = handler.get_episode_count(show, link, useragent=config.useragent)
			if new_length is not None:
				debug("    Lists length: {}".format(new_length))
				if length is not None and new_length != length:
					warning("    Conflict between lengths {} and {}".format(new_length, length))
				length = new_length
		
		# Length found, update database
		if length is not None:
			info("New episode count: {}".format(length))
			if update_db:
				db.set_show_episode_count(show, length)
			else:
				warning("Debug enabled, not updating database")
