from logging import debug, info, warning, error
from datetime import date, datetime

import services
import reddit

def main(config, db):
	current_datetime = datetime.utcnow()
	current_weekday = current_datetime.weekday()  # Monday = 0, Sunday = 6
	current_hour = current_datetime.hour

	scheduled_show_ids = db.get_show_ids_for_rewatch(current_weekday, current_hour)
	if not scheduled_show_ids:
		info("No shows scheduled for a rewatch right now.")
		return

	debug("Found show ids for a rewatch: {}".format(scheduled_show_ids))
	for show_id in scheduled_show_ids:
		show = db.get_show(id=show_id)
		next_episode_number = 1
		latest_episode = db.get_latest_episode(show)
		if latest_episode is not None:
			next_episode_number = latest_episode.number + 1
		debug("Creating rewatch thread for {} episode {}".format(show.name, next_episode_number))

# end
