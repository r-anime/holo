from logging import info, error, exception
import praw, requests
from requests.auth import HTTPBasicAuth

# Initialization

_oauth_scopes = {"identity", "submit"}

def init_reddit_session(config):
	try:
		info("Connecting to reddit...", end=" ")
		r = praw.Reddit(user_agent=config.useragent)
		
		info("logging in...", end=" ")
		if config.r_username is None or config.r_password is None:
			return None
		
		client_auth = HTTPBasicAuth(config.r_oauth_key, config.r_oauth_secret)
		headers = {"User-Agent": config.useragent}
		data = {"grant_type": "password", "username": config.r_username, "password": config.r_password}
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
		r.set_oauth_app_info(config.r_oauth_id, config.r_oauth_secret, "http://example.com/unused/redirect/uri")
		r.set_access_credentials(_oauth_scopes, access_token=token)
		r.config.api_request_delay = 1
		
		info("done!")
		return r
	
	except Exception as e:
		print("failed! Couldn't connect: {}".format(e))
		raise e

def destroy_reddit_session(r):
	r.clear_authentication()

# Thing doing

def submit_text_post(r, subreddit, title, body):
	try:
		r.submit(subreddit, title, text=body, send_replies=False)
		return True
	except:
		exception("Failed to submit text post")
		return False

def send_modmail(r, subreddit, title, body):
	r.send_message("/r/"+subreddit, title, body)

def send_pm(r, user, title, body, from_sr=None):
	r.send_message(user, title, body, from_sr=from_sr)

def reply_to(thing, body, distinguish=False):
	reply = None
	if isinstance(thing, praw.objects.Submission):
		reply = thing.add_comment(body)
	elif isinstance(thing, praw.objects.Inboxable):
		reply = thing.reply(body)
	
	if distinguish and reply is not None:
		response = reply.distinguish()
		if len(response) > 0 and len(response["errors"]) > 0:
			error("Failed to distinguish: {}".format(response["errors"]))
