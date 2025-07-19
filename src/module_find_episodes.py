from logging import debug, info, warning, error
from datetime import date, timedelta

import services
from data.models import Stream
import reddit, lemmy

def main(config, db, **kwargs):
	if config.backend == "reddit":
		reddit.init_reddit(config)
	elif config.backend == "lemmy":
		lemmy.init_lemmy(config)
	
	has_new_episode = []
	
	# Check services for new episodes
	enabled_services = db.get_services(enabled=True)

	for service in enabled_services:
		try:
			service_handler = services.get_service_handler(service)

			streams = db.get_streams(service=service)
			debug("{} streams found".format(len(streams)))

			recent_episodes = service_handler.get_recent_episodes(streams, useragent=config.useragent)
			info(f"{len(recent_episodes)} episodes for active shows on service {service}")

			for stream, episodes in recent_episodes.items():
				show = db.get_show(stream=stream)
				if show is None or not show.enabled:
					continue

				info("Checking stream \"{}\"".format(stream.show_key))
				debug(stream)

				if not episodes:
					info("  Show/episode not found")
					continue

				for episode in sorted(episodes, key=lambda e: e.number):
					if _process_new_episode(config, db, show, stream, episode):
						has_new_episode.append(show)
		except IOError:
			error(f'Error while getting shows on service {service}')

	# Check generic services
	# Note : selecting only shows with missing streams avoids troll torrents,
	# but also can cause delays if supported services are later than unsupported ones
	#other_shows = set(db.get_shows(missing_stream=True)) | set(db.get_shows(delayed=True))
	other_shows = set(db.get_shows(missing_stream=False)) | set(db.get_shows(delayed=True))
	if len(other_shows) > 0:
		info("Checking generic services for {} shows".format(len(other_shows)))

	other_streams = [Stream.from_show(show) for show in other_shows]
	for service in enabled_services:
		try:
			service_handler = services.get_service_handler(service)
			if service_handler.is_generic:
				debug("    Checking service {}".format(service_handler.name))
				recent_episodes = service_handler.get_recent_episodes(other_streams, useragent=config.useragent)
				info(f"{len(recent_episodes)} episodes for active shows on generic service {service}")

				for stream, episodes in recent_episodes.items():
					show = db.get_show(stream=stream)
					if show is None or not show.enabled:
						continue

					info("Checking stream \"{}\"".format(stream.show_key))
					debug(stream)

					if not episodes:
						info("  No episode found")
						continue

					for episode in sorted(episodes, key=lambda e: e.number):
						if _process_new_episode(config, db, show, stream, episode):
							has_new_episode.append(show)
		except IOError:
			error(f'Error while getting shows on service {service}')

	debug("")
	debug("Summary of shows with new episodes:")
	for show in has_new_episode:
		debug("  {}".format(show.name))
	debug("")

#yesterday = date.today() - timedelta(days=1)

def _process_new_episode(config, db, show, stream, episode):
	debug("Processing new episode")
	debug(episode)
	
	debug("  Date: {}".format(episode.date))
	debug("  Is live: {}".format(episode.is_live))
	#if episode.is_live and (episode.date is None or episode.date.date() > yesterday):
	if episode.is_live:
		# Adjust episode to internal numbering
		int_episode = stream.to_internal_episode(episode)
		debug("  Adjusted num: {}".format(int_episode.number))
		if int_episode.number <= 0:
			error("Episode number must be positive")
			return False
		
		# Check if already in database
		#already_seen = db.stream_has_episode(stream, episode.number)
		latest_episode = db.get_latest_episode(show)
		already_seen = latest_episode is not None and latest_episode.number >= int_episode.number
		episode_number_gap = latest_episode is not None and latest_episode.number > 0 and int_episode.number > latest_episode.number + 1
		debug("  Latest ep num: {}".format("none" if latest_episode is None else latest_episode.number))
		debug(f"  Already seen: {already_seen}")
		debug(f"  Gap between episodes: {episode_number_gap}")

		info(f"  Posted on {episode.date}, " +
			 f"number {int_episode.number}, " +
			 f"{'already seen' if already_seen else 'new'}, " +
			 f"{'gap between episodes' if episode_number_gap else 'expected number'}")
		
		# New episode!
		if not already_seen and not episode_number_gap:
			post_url = _create_post(config, db, show, stream, int_episode, submit=not config.debug)
			info("  Post URL: {}".format(post_url))
			if post_url is not None:
				post_url = post_url.replace("http:", "https:")
				db.add_episode(stream.show, int_episode.number, post_url)
				if show.delayed:
					db.set_show_delayed(show, False)
				# Edit the links in previous episodes
				editing_episodes = db.get_episodes(show)
				if len(editing_episodes) > 0:
					edit_history_length = int(4 * 13 / 2) # cols x rows / 2
					editing_episodes.sort(key=lambda x: x.number)
					for editing_episode in editing_episodes[-edit_history_length:]:
						_edit_post(config, db, show, stream, editing_episode, editing_episode.link, submit=not config.debug)
			else:
				error("  Episode not submitted")
			
			return True
	else:
		info("  Episode not live")
	
	return False

def _create_post(config, db, show, stream, episode, submit=True):
	display_episode = stream.to_display_episode(episode)
	
	title, body = _create_post_contents(config, db, show, stream, display_episode)
	if submit:
		if config.backend == "reddit":
			new_post = reddit.submit_text_post(config.subreddit, title, body)
			if new_post is not None:
				debug("Post successful")
				return reddit.get_shortlink_from_id(new_post.id)
		elif config.backend == "lemmy":
			new_post = lemmy.submit_text_post(config.subreddit, title, body)
			if new_post is not None:
				debug("Post successful")
				return lemmy.get_shortlink_from_id(new_post['id'])

		error("Failed to submit post")
	return None

def _edit_post(config, db, show, stream, episode, url, submit=True):
	display_episode = stream.to_display_episode(episode)
	
	_, body = _create_post_contents(config, db, show, stream, display_episode, quiet=True)
	if submit:
		if config.backend == "reddit":
			reddit.edit_text_post(url, body)
		if config.backend == "lemmy":
			lemmy.edit_text_post(url, body)
	return None

def _create_post_contents(config, db, show, stream, episode, quiet=False):
	title = _create_post_title(config, show, episode)
	title = _format_post_text(config, db, title, config.post_formats, show, episode, stream)
	info("Title:\n"+title)
	body = _format_post_text(config, db, config.post_body, config.post_formats, show, episode, stream)
	if not quiet: info("Body:\n"+body)
	return title, body

def _format_post_text(config, db, text, formats, show, episode, stream):
	#TODO: change to a more block-based system (can exclude blocks without content)
	if "{spoiler}" in text:
		text = safe_format(text, spoiler=_gen_text_spoiler(formats, show))
	if "{streams}" in text:
		text = safe_format(text, streams=_gen_text_streams(db, formats, show))
	if "{links}" in text:
		text = safe_format(text, links=_gen_text_links(db, formats, show))
	if "{discussions}" in text:
		text = safe_format(text, discussions=_gen_text_discussions(db, formats, show, stream))
	if "{aliases}" in text:
		text = safe_format(text, aliases=_gen_text_aliases(db, formats, show))
	if "{poll}" in text:
		text = safe_format(text, poll=_gen_text_poll(db, config, formats, show, episode))
	
	episode_name = ": {}".format(episode.name) if episode.name else ""
	episode_alt_number = "" if stream.remote_offset == 0 else f" ({episode.number + stream.remote_offset})"
	text = safe_format(text, show_name=show.name, show_name_en=show.name_en, episode=episode.number, episode_alt_number=episode_alt_number, episode_name=episode_name)
	return text.strip()

def _create_post_title(config, show, episode):
	if show.name_en:
		title = config.post_title_with_en
	else:
		title = config.post_title

	if episode.number == show.length and config.post_title_postfix_final:
		title += ' ' + config.post_title_postfix_final
	return title

# Generating text parts

def _gen_text_spoiler(formats, show):
	debug("Generating spoiler text for show {}, spoiler is {}".format(show, show.has_source))
	if show.has_source:
		return formats["spoiler"]
	return ""

def _gen_text_streams(db, formats, show):
	debug("Generating stream text for show {}".format(show))
	stream_texts = list()

	streams = db.get_streams(show=show)
	for stream in streams:
		if stream.active:
			service = db.get_service(id=stream.service)
			if service.enabled and service.use_in_post:
				service_handler = services.get_service_handler(service)
				text = safe_format(formats["stream"], service_name=service.name, stream_link=service_handler.get_stream_link(stream))
				stream_texts.append(text)
		
	lite_streams = db.get_lite_streams(show=show)
	for lite_stream in lite_streams:
		text = safe_format(formats["stream"], service_name=lite_stream.service_name, stream_link=lite_stream.url)
		stream_texts.append(text)

	if len(stream_texts) > 0:
		return "\n".join(stream_texts)
	else:
		return "*None*"

def _gen_text_links(db, formats, show):
	debug("Generating stream text for show {}".format(show))
	links = db.get_links(show=show)
	link_texts = list()
	link_texts_bottom = list() # for links that come last, e.g. official and subreddit
	for link in links:
		site = db.get_link_site(id=link.site)
		if site.enabled:
			link_handler = services.get_link_handler(site)
			if site.key == "subreddit":
				text = safe_format(formats["link_reddit"], link=link_handler.get_link(link))
			else:
				text = safe_format(formats["link"], site_name=site.name, link=link_handler.get_link(link))
			if site.key == "subreddit" or site.key == "official":
				link_texts_bottom.append(text)
			else:
				link_texts.append(text)

	return "\n".join(link_texts) + '\n' + '\n'.join(link_texts_bottom)

def _gen_text_discussions(db, formats, show, stream):
	episodes = db.get_episodes(show)
	debug("Num previous episodes: {}".format(len(episodes)))
	N_LINES = 13
	n_episodes = 4 * N_LINES # maximum 4 columns
	if len(episodes) > n_episodes:
		debug(f'Clipping to most recent {n_episodes} episodes')
		episodes = episodes[-n_episodes:]
	if len(episodes) > 0:
		table = []
		for episode in episodes:
			episode = stream.to_display_episode(episode)
			poll_handler = services.get_default_poll_handler()
			poll = db.get_poll(show, episode)
			if poll is None:
				score = None
				poll_link = None
			elif poll.has_score:
				score = poll.score
				poll_link = poll_handler.get_results_link(poll)
			else:
				score = poll_handler.get_score(poll)
				poll_link = poll_handler.get_results_link(poll)
			score = poll_handler.convert_score_str(score)
			table.append(safe_format(formats["discussion"], episode=episode.number, link=episode.link, score=score, poll_link=poll_link if poll_link else "http://localhost")) # Need valid link even when empty

		num_columns = 1 + (len(table) - 1) // N_LINES
		format_head, format_align = formats["discussion_header"], formats["discussion_align"]
		table_head = '|'.join(num_columns * [format_head]) + '\n' + '|'.join(num_columns * [format_align])
		table = ['|'.join(table[i::N_LINES]) for i in range(N_LINES)]
		return table_head + "\n" + "\n".join(table)
	else:
		return formats["discussion_none"]

def _gen_text_aliases(db, formats, show):
	aliases = db.get_aliases(show)
	if len(aliases) == 0:
		return ""
	return safe_format(formats["aliases"], aliases=", ".join(aliases))

def _gen_text_poll(db, config, formats, show, episode):
	handler = services.get_default_poll_handler()
	title = config.post_poll_title.format(show = show.name, episode = episode.number)

	poll = db.get_poll(show, episode)
	if poll is None:
		poll_id = handler.create_poll(title, headers = {'User-Agent': config.useragent}, submit=not config.debug)
		if poll_id:
			site = db.get_poll_site(key=handler.key)
			db.add_poll(show, episode, site, poll_id)
			poll = db.get_poll(show, episode)

	if poll is not None:
		poll_url = handler.get_link(poll)
		poll_results_url = handler.get_results_link(poll)
		return safe_format(formats["poll"], poll_url=poll_url, poll_results_url=poll_results_url)
	else:
		return ""

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
