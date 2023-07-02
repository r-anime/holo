from logging import debug, info, warning, error, exception
from pythorhead import Lemmy

# Initialization

_l = None
_config = None

def init_lemmy(config):
	global _config
	_config = config

def _connect_lemmy():
	if _config is None:
		error("Can't connect to lemmy without a config")
		return None
	lemmy = Lemmy(_config.l_instance)
	return lemmy if lemmy.log_in(_config.l_username, _config.l_password) else None

def _ensure_connection():
	global _l
	if _l is None:
		_l = _connect_lemmy()
	return _l is not None


def _get_post_id_from_shortlink(url):
	_ensure_connection()
	return int(url.split('/')[-1])

def _extract_post_response(post_data):
	if not post_data or not post_data['post_view'] or not post_data['post_view']['post']:
		exception("Bad post response: {}", post_data)
	return post_data['post_view']['post']

# Thing doing

def submit_text_post(community, title, body):
	_ensure_connection()
	info("Submitting post to {}", community)
	community_id = _l.discover_community(community)
	if not community_id:
		exception("Community {} not found", community)
	response = _l.post.create(community_id, title, body=body)
	return _extract_post_response(response)

def edit_text_post(url, body):
	_ensure_connection()
	post_id = _get_post_id_from_shortlink(url)
	try:
		info("Editing post {}", url)
		response = _l.post.edit(post_id, body=body)
		return _extract_post_response(response)
	except:
		exception("Failed to submit text post")
		return None

def get_text_post(url):
	_ensure_connection()
	post_id = _get_post_id_from_shortlink(url)
	try:
		response = _l.post.get(post_id)
		return _extract_post_response(response)
	except:
		exception("Failed to retrieve text post")
		return None

# Utilities

def get_shortlink_from_id(id):
	_ensure_connection()
	return f"{_config.l_instance}/post/{id}"
