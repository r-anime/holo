from logging import debug, info, error

import services
import reddit

def main(config, db, **kwargs):
	reddit.init_reddit(config)
	
	# Check services for new episodes
	for service_key in db.get_services(enabled=True):
		service = services.get_service(service_key)
		streams = db.get_service_streams(service=service)
		debug("{} streams found".format(len(streams)))
		for stream in streams:
			info("Checking stream \"{}\"".format(stream.site_key))
			debug(stream)
			
			# Check latest episode
			episode = service.get_latest_episode(stream.site_key, useragent=config.useragent)
			debug(episode)
			info("  Is live: {}".format(episode.is_live))
			
			if episode.is_live:
				# Adjust episode number with offset and check if already in database
				episode_num = episode.number - stream.remote_offset
				info("  Adjusted num: {}".format(episode_num))
				already_seen = db.stream_has_episode(stream, episode_num)
				info("  Already seen: {}".format(already_seen))
				
				# New episode!
				if not already_seen:
					post_url = _create_reddit_post(config, db, stream, episode)
					info("  Post URL: {}".format(post_url))
					if post_url is not None:
						db.store_episode(stream.show, episode_num, post_url)
					else:
						error("  Episode not submitted")

def _create_reddit_post(config, db, stream, episode):
	title, body = _create_post_contents(config, db, stream, episode)
	new_post = reddit.submit_text_post(config.subreddit, title, body)
	if new_post is not None:
		debug("Post successful")
		return reddit.get_shortlink_from_id(new_post.id)
	
	error("Failed to submit post")
	return None

def _create_post_contents(config, db, stream, episode):
	show = db.get_show(stream=stream)
	
	title = _format_post_text(config.post_title, show, episode, stream)
	body = _format_post_text(config.post_body, show, episode, stream)
	return title, body

def _format_post_text(text, show, episode, stream):
	episode_num = episode.number + stream.display_offset
	formatted = text.format(name=show.name, episode=episode_num, episode_name=episode.name)
	formatted = formatted.strip()
	return formatted
