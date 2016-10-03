from logging import debug, info, error
from datetime import date, timedelta

import services
from data.models import Stream
import reddit

def main(config, db, **kwargs):
	reddit.init_reddit(config)
	
	has_new_episode = []
	
	# Check services for new episodes
	enabled_services = db.get_services(enabled=True)
	for service in enabled_services:
		service_handler = services.get_service_handler(service)
		
		streams = db.get_streams(service=service)
		debug("{} streams found".format(len(streams)))
		for stream in streams:
			show = db.get_show(stream=stream)
			if show is None or not show.enabled:
				continue
				
			info("Checking stream \"{}\"".format(stream.show_key))
			debug(stream)
			
			# Check latest episode
			episode = service_handler.get_latest_episode(stream, useragent=config.useragent)
			if not episode:
				info("  Show/episode not found")
				continue
			
			if _process_new_episode(config, db, show, stream, episode):
				has_new_episode.append(show)
	
	# Check generic services
	other_shows = set(db.get_shows(missing_stream=True)) | set(db.get_shows(delayed=True))
	if len(other_shows) > 0:
		info("Checking generic services for {} shows".format(len(other_shows)))
	for show in other_shows:
		info("  Checking show {} ({})".format(show.name, show.id))
		stream = Stream.from_show(show)
		for service in enabled_services:
			service_handler = services.get_service_handler(service)
			if service_handler.is_generic:
				debug("    Checking service {}".format(service_handler.name))
				episode = service_handler.get_latest_episode(stream, useragent=config.useragent)
				if not episode:
					debug("    No episode found")
					continue
				
				if _process_new_episode(config, db, show, stream, episode):
					has_new_episode.append(show)
				
				break
		else:
			info("  No episode found")
	
	debug("")
	debug("Summary of shows with new episodes:")
	for show in has_new_episode:
		debug("  {}".format(show.name))
	debug("")

#yesterday = date.today() - timedelta(days=1)

def _process_new_episode(config, db, show, stream, episode):
	debug("Processing new episode")
	debug(episode)
	
	info("  Date: {}".format(episode.date))
	info("  Is live: {}".format(episode.is_live))
	#if episode.is_live and (episode.date is None or episode.date.date() > yesterday):
	if episode.is_live:
		# Adjust episode to internal numbering
		int_episode = stream.to_internal_episode(episode)
		info("  Adjusted num: {}".format(int_episode.number))
		if int_episode.number < 0:
			error("Episode number cannot be negative")
			return False
		
		# Check if already in database
		#already_seen = db.stream_has_episode(stream, episode.number)
		latest_episode = db.get_latest_episode(show)
		info("  Latest ep num: {}".format("none" if latest_episode is None else latest_episode.number))
		already_seen = latest_episode is not None and latest_episode.number >= int_episode.number
		info("  Already seen: {}".format(already_seen))
		
		# New episode!
		if not already_seen:
			post_url = _create_reddit_post(config, db, show, stream, int_episode, submit=not config.debug)
			info("  Post URL: {}".format(post_url))
			if post_url is not None:
				db.add_episode(stream.show, int_episode.number, post_url)
				if show.delayed:
					db.set_show_delayed(show, False)
			else:
				error("  Episode not submitted")
			
			return True
	else:
		info("  Episode not live")
	
	return False

def _create_reddit_post(config, db, show, stream, episode, submit=True):
	display_episode = stream.to_display_episode(episode)
	
	title, body = _create_post_contents(config, db, show, stream, display_episode)
	if submit:
		new_post = reddit.submit_text_post(config.subreddit, title, body)
		if new_post is not None:
			debug("Post successful")
			return reddit.get_shortlink_from_id(new_post.id)
		else:
			error("Failed to submit post")
	return None

def _create_post_contents(config, db, show, stream, episode):
	title = _create_post_title(config, show, episode)
	title = _format_post_text(db, title, config.post_formats, show, episode, stream)
	info("Title:\n"+title)
	body = _format_post_text(db, config.post_body, config.post_formats, show, episode, stream)
	info("Body:\n"+body)
	return title, body

def _format_post_text(db, text, formats, show, episode, stream):
	#TODO: change to a more block-based system (can exclude blocks without content)
	if "{spoiler}" in text:
		text = safe_format(text, spoiler=_gen_text_spoiler(formats, show))
	if "{streams}" in text:
		text = safe_format(text, streams=_gen_text_streams(db, formats, show))
	if "{links}" in text:
		text = safe_format(text, links=_gen_text_links(db, formats, show))
	if "{discussions}" in text:
		text = safe_format(text, discussions=_gen_text_discussions(db, formats, show, stream))
	
	episode_name = ": {}".format(episode.name) if episode.name else ""
	text = safe_format(text, show_name=show.name, episode=episode.number, episode_name=episode_name)
	return text.strip()

def _create_post_title(config, show, episode):
	title = config.post_title
	if episode.number == show.length and config.post_title_postfix_final:
		title += config.post_title_postfix_final
	return title

# Generating text parts

def _gen_text_spoiler(formats, show):
	if show.has_source:
		return formats["spoiler"]
	return ""

def _gen_text_streams(db, formats, show):
	debug("Generating stream text for show {}".format(show))
	streams = db.get_streams(show=show)
	if len(streams) > 0:
		stream_texts = list()
		for stream in streams:
			if stream.active:
				service = db.get_service(id=stream.service)
				if service.enabled and service.use_in_post:
					service_handler = services.get_service_handler(service)
					text = safe_format(formats["stream"], service_name=service.name, stream_link=service_handler.get_stream_link(stream))
					stream_texts.append(text)
		
		return "\n".join(stream_texts)
	else:
		return "*None*"

def _gen_text_links(db, formats, show):
	debug("Generating stream text for show {}".format(show))
	links = db.get_links(show=show)
	link_texts = list()
	for link in links:
		site = db.get_link_site(id=link.site)
		if site.enabled:
			link_handler = services.get_link_handler(site)
			text = safe_format(formats["link"], site_name=site.name, link=link_handler.get_link(link))
			link_texts.append(text)
			
	return "\n".join(link_texts)

def _gen_text_discussions(db, formats, show, stream):
	episodes = db.get_episodes(show)
	debug("Num previous episodes: {}".format(len(episodes)))
	if len(episodes) > 0:
		table = [formats["discussion_header"]]
		for episode in episodes:
			episode = stream.to_display_episode(episode)
			score = db.get_episode_score_avg(show, episode)
			table.append(safe_format(formats["discussion"], episode_num=episode.number, episode_link=episode.link, episode_score=score if score else ""))
		return "\n".join(table)
	else:
		return formats["discussion_none"]

# Helpers

class _SafeDict(dict):
	def __missing__(self, key):
		return "{"+key+"}"

def safe_format(s, **kwargs):
	"""
	A safer version of the default str.format(...) function.
	Ignores unused keyword arguments and unused '{...}' placeholders instead of throwing a KeyError.
	:param s: The string being formatted
	:param kwargs: The format replacements
	:return: A formatted string
	"""
	return s.format_map(_SafeDict(**kwargs))
