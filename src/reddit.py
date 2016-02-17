from logging import debug, info, error, exception
import praw, praw_script_oauth

# Initialization

_r = None
_config = None
_oauth_scopes = {"identity", "read", "submit"}

def init_reddit(config):
	global _config
	_config = config

def _connect_reddit():
	if _config is None:
		error("Can't connect to reddit without a config")
		return None
	
	return praw_script_oauth.connect(_config.r_oauth_key, _config.r_oauth_secret, _config.r_username, _config.r_password, oauth_scopes=_oauth_scopes, useragent=_config.useragent)

def _ensure_connection():
	global _r
	if _r is None:
		_r = _connect_reddit()
	return _r is not None

# Thing doing

def submit_text_post(subreddit, title, body):
	_ensure_connection()
	try:
		info("Submitting post to {}".format(subreddit))
		new_post = _r.submit(subreddit, title, text=body, send_replies=False)
		return new_post
	except:
		exception("Failed to submit text post")
		return None

def send_modmail(subreddit, title, body):
	_ensure_connection()
	_r.send_message("/r/"+subreddit, title, body)

def send_pm(user, title, body, from_sr=None):
	_ensure_connection()
	_r.send_message(user, title, body, from_sr=from_sr)

def reply_to(thing, body, distinguish=False):
	_ensure_connection()
	
	reply = None
	if isinstance(thing, praw.objects.Submission):
		reply = thing.add_comment(body)
	elif isinstance(thing, praw.objects.Inboxable):
		reply = thing.reply(body)
	
	if distinguish and reply is not None:
		response = reply.distinguish()
		if len(response) > 0 and len(response["errors"]) > 0:
			error("Failed to distinguish: {}".format(response["errors"]))

# Utilities

def get_shortlink_from_id(id):
	return "http://redd.it/{}".format(id)
