from logging import debug, info, warning, error

import services

def main(config, db, **kwargs):
	#check_new_shows(config, db, update_db=not config.debug)
	check_new_shows(config, db)

# New shows

def check_new_shows(config, db, update_db=True):
	info("Checking for new shows")
	for raw_show in _get_new_season_shows(config):
		if not db.has_link(raw_show.site_key, raw_show.show_key):
			# Link doesn't doesn't exist in db
			debug("New show link: {} on {}".format(raw_show.show_key, raw_show.site_key))
			
			# Check if related to existing show
			shows = db.search_show_ids_by_names(raw_show.name, *raw_show.more_names)
			show_id = None
			# Show doesn't exist; add it
			if len(shows) == 0:
				debug("  Show not found, adding to database")
				if update_db:
					show_id = db.add_show(raw_show, commit=False)
			elif len(shows) == 1:
				show_id = shows[0]
			else:
				warning("  More than one show found, ids={}".format(shows))
				show_id = shows[-1]
			
			# Add link to show
			if show_id and update_db:
				db.add_link(raw_show, show_id)
	
	if update_db:
		db.commit()

def _get_new_season_shows(config):
	# Only checks link sites because their names are preferred
	# Names on stream sites are unpredictable and many times in english
	for handler in services.get_link_handlers().values():
		info("  Checking {} ({})".format(handler.name, handler.key))
		raw_shows = handler.get_seasonal_shows(useragent=config.useragent)
		for raw_show in raw_shows:
			yield raw_show

# New streams

def check_new_streams(config, db, update_db=True):
	# Stream sites (like Crunchyroll)
	for handler in services.get_service_handlers().values():
		info("  Checking {} ({})".format(handler.name, handler.key))
		raw_shows = handler.get_seasonal_shows(useragent=config.useragent)
		for raw_show in raw_shows:
			if db.has_stream(raw_show.site_key, raw_show.show_key):
				debug("Stream already exists for {} on {}".format(raw_show.show_key, raw_show.site_key))
			elif update_db:
				pass
