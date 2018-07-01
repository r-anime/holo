from logging import debug, info, warning, error

import services

def main(config, db, **kwargs):
	# Find data not provided by the edit module
	_check_missing_stream_info(config, db, update_db=not config.debug)
	# Check for new show scores
	if config.record_scores:
		_check_new_episode_scores(config, db, update_db=not config.debug)
	# Show lengths aren't always known at the start of the season
	_check_show_lengths(config, db, update_db=not config.debug)
	# Check if shows have finished and disable them if they have
	_disable_finished_shows(config, db, update_db=not config.debug)
	
def _check_show_lengths(config, db, update_db=True):
	info("Checking show lengths")
	
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
			new_length = handler.get_episode_count(link, useragent=config.useragent)
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

def _disable_finished_shows(config, db, update_db=True):
	info("Checking for disabled shows")
	
	shows = db.get_shows()
	for show in shows:
		latest_episode = db.get_latest_episode(show)
		if latest_episode is not None and 0 < show.length <= latest_episode.number:
			info("  Disabling show \"{}\"".format(show.name))
			if latest_episode.number > show.length:
				warning("    Episode number ({}) greater than show length ({})".format(latest_episode.number, show.length))
			if update_db:
				db.set_show_enabled(show, enabled=False, commit=False)
	if update_db:
		db.save()

def _check_missing_stream_info(config, db, update_db=True):
	info("Checking for missing stream info")
	
	streams = db.get_streams(missing_name=True)
	for stream in streams:
		service_info = db.get_service(id=stream.service)
		info("Updating missing stream info of {} ({}/{})".format(stream.name, service_info.name, stream.show_key))
		
		service = services.get_service_handler(key=service_info.key)
		stream = service.get_stream_info(stream, useragent=config.useragent)
		if not stream:
			error("  Stream info not found")
			continue
		
		debug("  name={}".format(stream.name))
		debug("  key={}".format(stream.show_key))
		debug("  id={}".format(stream.show_id))
		if update_db:
			db.update_stream(stream, name=stream.name, show_id=stream.show_id, show_key=stream.show_key, commit=False)
	
	if update_db:
		db.commit()

def _check_new_episode_scores(config, db, update_db):
	info("Checking for new episode scores")
	
	shows = db.get_shows(enabled=True)
	for show in shows:
		latest_episode = db.get_latest_episode(show)
		if latest_episode is not None:
			info("For show {} ({}), episode {}".format(show.name, show.id, latest_episode .number))
			
			scores = db.get_episode_scores(show, latest_episode)
			# Check if any scores have been found rather than checking for each service
			if len(scores) == 0:
				for handler in services.get_link_handlers().values():
					info("  Checking {} ({})".format(handler.name, handler.key))
					
					# Get show link to site represented by the handler
					site = db.get_link_site(key=handler.key)
					link = db.get_link(show, site)
					if link is None:
						error("Failed to create link")
						continue
					
					new_score = handler.get_show_score(show, link, useragent=config.useragent)
					if new_score is not None:
						info("    Score: {}".format(new_score))
						db.add_episode_score(show, latest_episode, site, new_score, commit=False)
				
				if update_db:
					db.commit()
			else:
				info("  Already has scores, ignoring")
