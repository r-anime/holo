from logging import debug, info

from services import crunchyroll

def main(db):
	cr = crunchyroll.Service()
	streams = db.get_service_streams(service=cr)
	debug("{} streams found".format(len(streams)))
	for stream in streams:
		info("Checking stream \"{}\"".format(stream.show_key))
		debug(stream)
		episode = cr.get_latest_episode(stream.show_key)
		debug(episode)
		info("  Is live: {}".format(episode.is_live))
