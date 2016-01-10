from logging import debug, info, error

from services import crunchyroll

def main(config, db, **kwargs):
	cr = crunchyroll.Service()
	streams = db.get_service_streams(service=cr)
	debug("{} streams found".format(len(streams)))
	for stream in streams:
		info("Checking stream \"{}\"".format(stream.show_key))
		debug(stream)
		episode = cr.get_latest_episode(stream.show_key, useragent=config.useragent)
		debug(episode)
		info("  Is live: {}".format(episode.is_live))
		
		if episode.is_live:
			episode_num = episode.number - stream.remote_offset
			info("  Adjusted num: {}".format(episode_num))
			already_seen = db.stream_has_episode(stream, episode_num)
			info("  Already seen: {}".format(already_seen))
			if not already_seen:
				post_url = _create_reddit_post(stream, episode, subreddit=config.subreddit)
				info("  Post URL: {}".format(post_url))
				if post_url is not None:
					db.store_episode(stream.show, episode_num, post_url)
				else:
					error("  Episode not submitted")

def _create_reddit_post(stream, episode, subreddit=None):
	#TODO
	return "test.url"
