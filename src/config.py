import configparser

class Config:
	def __init__(self):
		self.module = None
		self.database = None
		self.useragent = None
		self.ratelimit = 1.0
		self.subreddit = None
		self.r_username = None
		self.r_password = None
		self.r_oauth_key = None
		self.r_oauth_secret = None
	
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
	
	return config

def validate(config):
	if config.database is None or len(config.database) == 0:
		return "database missing"
	if config.useragent is None or len(config.useragent) == 0:
		return "useragent missing"
	if config.ratelimit < 0:
		warning("Rate limit can't be negative, defaulting to 1.0")
		config.ratelimit = 1.0
	if config.subreddit is None or len(config.subreddit) == 0:
		return "subreddit missing"
	if config.r_username is None or len(config.r_username) == 0:
		return "reddit username missing"
	if config.r_password is None or len(config.r_password) == 0:
		return "reddit password missing"
	if config.r_oauth_key is None or len(config.r_oauth_key) == 0:
		return "reddit oauth key missing"
	if config.r_oauth_secret is None or len(config.r_oauth_secret) == 0:
		return "reddit oauth secret missing"
	return False
