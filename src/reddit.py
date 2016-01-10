from logging import debug, info, error, exception
import praw, requests
from requests.auth import HTTPBasicAuth

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
	
	try:
		info("Connecting to reddit...")
		r = praw.Reddit(user_agent=_config.useragent)
		if _config.r_username is None or _config.r_password is None:
			return None
		
		debug("  oauth key = {}".format(_config.r_oauth_key))
		debug("  oauth secret = {}".format(_config.r_oauth_secret))
		debug("  username = {}".format(_config.r_username))
		debug("  password = {}{}{}".format(_config.r_password[0], "******", _config.r_password[-1]))
		client_auth = HTTPBasicAuth(_config.r_oauth_key, _config.r_oauth_secret)
		headers = {"User-Agent": _config.useragent}
		data = {"grant_type": "password", "username": _config.r_username, "password": _config.r_password}
		response = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, headers=headers, data=data)
		if not response.ok:
			error("Received error code {}: {}".format(response.status_code, response.reason))
			return None
		response_content = response.json()
		if "error" in response_content and response_content["error"] != 200:
			error("Received error: {}".format(response_content["error"]))
			return None
		
		token = response_content["access_token"]
		if response_content["token_type"] != "bearer":
			error("Received wrong type of token, wtf reddit")
			return None
		r.set_oauth_app_info(_config.r_oauth_key, _config.r_oauth_secret, "http://example.com/unused/redirect/uri")
		r.set_access_credentials(_oauth_scopes, access_token=token)
		r.config.api_request_delay = 1
		
		info("Done!")
		return r
	
	except Exception as e:
		print("failed! Couldn't connect: {}".format(e))
		raise e

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
		info("  title = {}".format(title))
		info("  body = {}".format(body))
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
