from logging import debug, info, warning, error

import services
from data.models import ShowType

def main(config, db, output_yaml, output_file=None, **kwargs):
	if output_yaml and output_file:
		debug("Using output file: {}".format(output_file))
		create_season_config(config, db, output_file)
	#check_new_shows(config, db, update_db=not config.debug)
	#check_new_shows(config, db)
	#match_show_streams(config, db, update_db=not config.debug)
	#match_show_streams(config, db)
	#check_new_streams(config, db, update_db=not config.debug)
	#check_new_streams(config, db)

# New shows

from collections import OrderedDict
import yaml

# Retain order of OrderedDict when dumping yaml
represent_dict_order = lambda self, data:  self.represent_mapping('tag:yaml.org,2002:map', data.items())
yaml.add_representer(OrderedDict, represent_dict_order)  

def create_season_config(config, db, output_file):
	info("Checking for new shows")
	shows = []
	
	link_handlers = services.get_link_handlers()
	service_handlers = services.get_service_handlers()
	
	for site in db.get_link_sites():
		if site.key not in link_handlers:
			warning("Link site handler for {} not installed".format(site.key))
			continue
		
		site_handler = link_handlers.get(site.key)
		for raw_show in site_handler.get_seasonal_shows(useragent=config.useragent):
			if raw_show.show_type is not ShowType.UNKNOWN and raw_show.show_type not in config.new_show_types:
				debug("  Show isn't an allowed type ({})".format(raw_show.show_type))
				debug("    name={}".format(raw_show.name))
				continue
			#if raw_show.name in shows:
			#	debug("  Show already seen")
			#	debug("    name={}".format(raw_show.name))
			#	continue
			
			debug("New show: {}".format(raw_show.name))
			
			d = OrderedDict([
				("title", raw_show.name),
				("type", raw_show.show_type.name.lower()),
				("has_source", raw_show.has_source),
				("info", OrderedDict([(i, "") for i in sorted(link_handlers.keys())])),
				("streams", OrderedDict([(s, "") for s in sorted(service_handlers.keys()) if not service_handlers[s].is_generic and s in ["crunchyroll", "funimation"]]))
			])
			shows.append(d)
	
	debug("Outputting new shows")
	with open(output_file, "w", encoding="utf-8") as f:
		yaml.dump_all(shows, f, explicit_start=True, default_flow_style=False)

def check_new_shows(config, db, update_db=True):
	info("Checking for new shows")
	for raw_show in _get_new_season_shows(config, db):
		if raw_show.show_type is not ShowType.UNKNOWN and raw_show.show_type not in config.new_show_types:
			debug("  Show isn't an allowed type ({})".format(raw_show.show_type))
			debug("    name={}".format(raw_show.name))
			continue
			
		if not db.has_link(raw_show.site_key, raw_show.show_key):
			# Link doesn't doesn't exist in db
			debug("New show link: {} on {}".format(raw_show.show_key, raw_show.site_key))
			
			# Check if related to existing show
			shows = db.search_show_ids_by_names(raw_show.name, *raw_show.more_names)
			show_id = None
			if len(shows) == 0:
				# Show doesn't exist; add it
				debug("  Show not found, adding to database")
				if update_db:
					show_id = db.add_show(raw_show, commit=False)
			elif len(shows) == 1:
				show_id = shows.pop()
			else:
				# Uh oh, multiple matches
				#TODO: make sure this isn't triggered by multi-season shows
				warning("  More than one show found, ids={}".format(shows))
				#show_id = shows[-1]
			
			# Add link to show
			if show_id and update_db:
				db.add_link(raw_show, show_id, commit=False)
		
		if update_db:
			db.commit()

def _get_new_season_shows(config, db):
	# Only checks link sites because their names are preferred
	# Names on stream sites are unpredictable and many times in english
	handlers = services.get_link_handlers()
	for site in db.get_link_sites():
		if site.key not in handlers:
			warning("Link site handler for {} not installed".format(site.key))
			continue
		
		handler = handlers.get(site.key)
		info("  Checking {} ({})".format(handler.name, handler.key))
		raw_shows = handler.get_seasonal_shows(useragent=config.useragent)
		for raw_show in raw_shows:
			yield raw_show

# New streams

def check_new_streams(config, db, update_db=True):
	info("Checking for new streams")
	for raw_stream in _get_new_season_streams(config, db):
		if not db.has_stream(raw_stream.service_key, raw_stream.show_key):
			debug("  {}".format(raw_stream.name))
			
			# Search for a related show
			shows = db.search_show_ids_by_names(raw_stream.name)
			show_id = None
			if len(shows) == 0:
				debug("    Show not found")
			elif len(shows) == 1:
				show_id = shows.pop()
			else:
				# Uh oh, multiple matches
				#TODO: make sure this isn't triggered by multi-season shows
				warning("    More than one show found, ids={}".format(shows))
			
			# Add stream
			if update_db:
				db.add_stream(raw_stream, show_id, commit=False)
		else:
			debug("  Stream already exists for {} on {}".format(raw_stream.show_key, raw_stream.service_key))
	
	if update_db:
		db.commit()

def _get_new_season_streams(config, db):
	handlers = services.get_service_handlers()
	for service in db.get_services():
		if service.key not in handlers:
			warning("Service handler for {} not installed".format(service.key))
			continue
		
		if service.enabled:
			handler = handlers.get(service.key)
			info("  Checking {} ({})".format(handler.name, handler.key))
			raw_stream = handler.get_seasonal_streams(useragent=config.useragent)
			for raw_stream in raw_stream:
				yield raw_stream

# Match streams missing shows

def match_show_streams(config, db, update_db=True):
	info("Matching streams to shows")
	streams = db.get_streams(unmatched=True)
	
	if len(streams) == 0:
		debug("  No unmatched streams")
		return
	
	# Check each link site
	for site in db.get_link_sites():
		debug("  Checking service: {}".format(site.key))
		handler = services.get_link_handler(site)
		
		# Check remaining streams
		for stream in list(streams):								# Iterate over copy of stream list allow removals
			debug("    Checking stream: {}".format(stream.name))
			raw_shows = handler.find_show(stream.name, useragent=config.useragent)
			if len(raw_shows) == 1:
				# Show info found
				raw_show = raw_shows.pop()
				debug("      Found show: {}".format(raw_show.name))
				
				# Search stored names for show matches
				shows = db.search_show_ids_by_names(raw_show.name, *raw_show.more_names)
				if len(shows) == 1:
					# All the planets are aligned
					# Connect the stream and show and save the used name
					show_id = shows.pop()
					if update_db:
						db.update_stream(stream, show=show_id, active=True)
						db.add_show_names(stream.name, id=show_id, commit=False)
					streams.remove(stream)
				elif len(shows) == 0:
					warning("      No shows known")
				else:
					warning("      Multiple shows known")
			elif len(raw_shows) == 0:
				warning("    No shows found")
			else:
				warning("    Multiple shows found")
			
		if update_db:
			db.commit()
