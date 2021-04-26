from logging import debug, info, error, exception
import praw

# Initialization

_r = None
_config = None

def init_reddit(config):
	global _config
	_config = config

def _connect_reddit():
	if _config is None:
		error("Can't connect to reddit without a config")
		return None
	
	return praw.Reddit(client_id=_config.r_oauth_key, client_secret=_config.r_oauth_secret,
					username=_config.r_username, password=_config.r_password,
					user_agent=_config.useragent,
					check_for_updates=False)

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
		new_post = _r.subreddit(subreddit).submit(title,
		                                          selftext=body,
							  flair_id=_config.post_flair_id,
							  flair_text=_config.post_flair_text,
							  send_replies=False)
		return new_post
	except:
		exception("Failed to submit text post")
		return None

def edit_text_post(url, body):
	_ensure_connection()
	try:
		info(f"Editing post {url}")
		post = get_text_post(url)
		post.edit(body)
		return post
	except:
		exception("Failed to submit text post")
		return None

def get_text_post(url):
	_ensure_connection()
	try:
		new_post = _r.submission(url=url)
		return new_post
	except:
		exception("Failed to retrieve text post")
		return None

#NOTE: PRAW3 stuff
#def send_modmail(subreddit, title, body):
#	_ensure_connection()
#	_r.send_message("/r/"+subreddit, title, body)
#
#def send_pm(user, title, body, from_sr=None):
#	_ensure_connection()
#	_r.send_message(user, title, body, from_sr=from_sr)
#
#def reply_to(thing, body, distinguish=False):
#	_ensure_connection()
#	
#	reply = thing.reply(body)
#	
#	if distinguish and reply is not None:
#		response = reply.distinguish()
#		if len(response) > 0 and len(response["errors"]) > 0:
#			error("Failed to distinguish: {}".format(response["errors"]))

# Utilities

def get_shortlink_from_id(id):
	return "http://redd.it/{}".format(id)
