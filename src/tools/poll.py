import requests


_poll_url = 'https://youpoll.me'
_scale = 10

def create_poll(config, show, episode):
	"""
	Create a new poll and return its address.
	:param show: name of the show
	:param episode: episode number
	:return: URL of the poll or None
	"""

	headers = {'User-Agent': config.useragent}
	params = {
		'address': '',
		'poll-1[question]': config.post_poll_title.format(show = show, episode = episode),
		'poll-1[option1]': '',
		'poll-1[option2]': '',
		'poll-1[min]': '1',
		'poll-1[max]': _scale,
		'poll-1[voting-system]': '0',
		'poll-1[approval-validation-type]': '0',
		'poll-1[approval-validation-value]': '1',
		'poll-1[rating]': '',
		'voting-limits-dropdown': '2',
		'reddit-link-karma': '0',
		'reddit-comment-karma': '0',
		'reddit-days-old': '0',
		'responses-input': '',
		}

	resp = requests.post(_poll_url, data = params, headers = headers)

	if resp.ok:
		return resp.url
	else:
		return None
