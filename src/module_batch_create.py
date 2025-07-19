from logging import debug, info, warning, error
from datetime import date, timedelta

import services
from data.models import Stream, Episode
import reddit, lemmy

from module_find_episodes import _create_post, _edit_post, _format_post_text

def main(config, db, show_name, episode_count):
	int_episode_count = int(episode_count)
	if config.backend == "reddit":
		reddit.init_reddit(config)
	elif config.backend == "lemmy":
		lemmy.init_lemmy(config)

	show = db.get_show_by_name(show_name)
	if not show:
		raise IOError(f"Show {show_name} does not exist!")
	stream = Stream.from_show(show)

	post_urls = list()
	for i in range(1, int_episode_count+1):
		int_episode = Episode(i, None, None, None)
		post_url = _create_post(config, db, show, stream, int_episode, submit=not config.debug)
		info("  Post URL: {}".format(post_url))
		if post_url is not None:
			post_url = post_url.replace("http:", "https:")
			db.add_episode(show, int_episode.number, post_url)
		else:
			error("  Episode not submitted")
		post_urls.append(post_url)

	for editing_episode in db.get_episodes(show):
		_edit_post(config, db, show, stream, editing_episode, editing_episode.link, submit=not config.debug)

	megathread_title, megathread_body = _create_megathread_content(config, db, show, stream, episode_count)

	if not config.debug:
		if config.backend == "reddit":
			megathread_post = reddit.submit_text_post(config.subreddit, megathread_title, megathread_body)
		elif config.backend == "lemmy":
			megathread_post = lemmy.submit_text_post(config.subreddit, megathread_title, megathread_body)
	else:
                megathread_post = None
		
	if megathread_post is not None:
		debug("Post successful")
		if config.backend == "reddit":
			megathread_url = reddit.get_shortlink_from_id(megathread_post.id).replace("http:", "https:")
		elif config.backend == "lemmy":
			megathread_url = lemmy.get_shortlink_from_id(megathread_post['id']).replace("http:", "https:")
	else:
		error("Failed to submit post")
		megathread_url = None

	db.set_show_enabled(show, False, commit=not config.debug)

	for i, url in enumerate(post_urls):
		info(f"Episode {i}: {url}")
	info(f"Megathread: {megathread_url}")


def _create_megathread_content(config, db, show, stream, episode_count):
	title = _create_megathread_title(config, show, episode_count)
	title = _format_post_text(config, db, title, config.post_formats, show, Episode(episode_count, None, None, None), stream)
	info("Title:\n"+title)

	body = _format_post_text(config, db, config.batch_thread_post_body, config.post_formats, show, Episode(episode_count, None, None, None), stream)
	info("Body:\n"+body)
	return title, body

def _create_megathread_title(config, show, episode_count):
	if show.name_en:
		title = config.batch_thread_post_title_with_en
	else:
		title = config.batch_thread_post_title

	return title
