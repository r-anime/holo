import configparser

class Config:
	def __init__(self):
		self.debug = False
		self.module = None
		self.database = None
		self.useragent = None
		self.ratelimit = 1.0
		
		self.subreddit = None
		self.r_username = None
		self.r_password = None
		self.r_oauth_key = None
		self.r_oauth_secret = None
		
		self.services = dict()
		
		self.new_show_types = list()
		
		self.post_title = None
		self.post_body = None
		self.post_formats = dict()
	
def from_file(file_path):
	print("Loading config file")
	config = Config()
	
	parsed = configparser.ConfigParser()
	success = parsed.read(file_path)
	if len(success) == 0:
		print("Failed to load config file")
		return config
	
	if "data" in parsed:
		sec = parsed["data"]
		config.database = sec.get("database", None)
	
	if "connection" in parsed:
		sec = parsed["connection"]
		config.useragent = sec.get("useragent", None)
		config.ratelimit = sec.getfloat("ratelimit", 1.0)
	
	if "reddit" in parsed:
		sec = parsed["reddit"]
		config.subreddit = sec.get("subreddit", None)
		config.r_username = sec.get("username", None)
		config.r_password = sec.get("password", None)
		config.r_oauth_key = sec.get("oauth_key", None)
		config.r_oauth_secret = sec.get("oauth_secret", None)
	
	if "service.mal" in parsed:
		sec = parsed["service.mal"]
		config.services["mal"] = {"username": sec.get("username", None), "password": sec.get("password", None)}
	
	if "service.anidb" in parsed:
		sec = parsed["service.anidb"]
		config.services["anidb"] = {"client": sec.get("client", None)}
	
	if "options" in parsed:
		sec = parsed["options"]
		config.debug = sec["debug"]
		from data.models import str_to_showtype
		config.new_show_types.extend(map(lambda s: str_to_showtype(s), sec.get("new_show_types", "").split(" ")))
	
	if "post" in parsed:
		sec = parsed["post"]
		config.post_title = sec.get("title", None)
		config.post_body = sec.get("body", None)
		for key in sec:
			if key.startswith("format_") and len(key) > 7:
				config.post_formats[key[7:]] = sec[key]
	
	return config

def validate(config):
	def is_bad_str(s):
		return s is None or len(s) == 0
	
	if is_bad_str(config.database):
		return "database missing"
	if is_bad_str(config.useragent):
		return "useragent missing"
	if config.ratelimit < 0:
		warning("Rate limit can't be negative, defaulting to 1.0")
		config.ratelimit = 1.0
	if is_bad_str(config.subreddit):
		return "subreddit missing"
	if is_bad_str(config.r_username):
		return "reddit username missing"
	if is_bad_str(config.r_password):
		return "reddit password missing"
	if is_bad_str(config.r_oauth_key):
		return "reddit oauth key missing"
	if is_bad_str(config.r_oauth_secret):
		return "reddit oauth secret missing"
	if is_bad_str(config.post_title):
		return "post title missing"
	if is_bad_str(config.post_body):
		return "post title missing"
	return False
