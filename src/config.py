import configparser
from logging import warning

class WhitespaceFriendlyConfigParser(configparser.ConfigParser):
	def get(self, section, option, *args, **kwargs):
		val = super().get(section, option, *args, **kwargs)
		return val.strip('"')

class Config:
	def __init__(self):
		self.debug = False
		self.module = None
		self.database = None
		self.useragent = None
		self.ratelimit = 1.0
		
		self.subreddit = None
		self.backend = None

		self.r_username = None
		self.r_password = None
		self.r_oauth_key = None
		self.r_oauth_secret = None
		
		self.l_instance = None
		self.l_username = None
		self.l_password = None

		self.services = dict()
		
		self.new_show_types = list()
		self.record_scores = False
		
		self.discovery_primary_source = None
		self.discovery_secondary_sources = list()
		self.discovery_stream_sources = list()
		
		self.post_title = None
		self.post_title_with_en = None
		self.post_title_postfix_final = None
		self.post_flair_id = None
		self.post_flair_text = None
		self.post_body = None
		self.batch_thread_post_title = None
		self.batch_thread_post_title_with_en = None
		self.batch_thread_post_body = None
		self.post_formats = dict()
	
def from_file(file_path):
	if file_path.find(".") < 0:
		file_path += ".ini"
	
	parsed = WhitespaceFriendlyConfigParser()
	success = parsed.read(file_path, encoding='utf-8')
	if len(success) == 0:
		print("Failed to load config file")
		return None
	
	config = Config()
	
	if "data" in parsed:
		sec = parsed["data"]
		config.database = sec.get("database", None)
	
	if "connection" in parsed:
		sec = parsed["connection"]
		config.useragent = sec.get("useragent", None)
		config.ratelimit = sec.getfloat("ratelimit", 1.0)
	
	if "reddit" in parsed:
		sec = parsed["reddit"]
		config.backend = "reddit"
		config.subreddit = sec.get("subreddit", None)
		config.r_username = sec.get("username", None)
		config.r_password = sec.get("password", None)
		config.r_oauth_key = sec.get("oauth_key", None)
		config.r_oauth_secret = sec.get("oauth_secret", None)
	
	if "lemmy" in parsed:
		sec = parsed["lemmy"]
		config.backend = "lemmy"
		config.subreddit = sec.get("community", None)
		config.l_instance = sec.get("instance", None)
		config.l_username = sec.get("username", None)
		config.l_password = sec.get("password", None)

	if "options" in parsed:
		sec = parsed["options"]
		config.debug = sec.getboolean("debug", False)
		from data.models import str_to_showtype
		config.new_show_types.extend(map(lambda s: str_to_showtype(s.strip()), sec.get("new_show_types", "").split(" ")))
		config.record_scores = sec.getboolean("record_scores", False)
	
	if "options.discovery" in parsed:
		sec = parsed["options.discovery"]
		config.discovery_primary_source = sec.get("primary_source", None)
		config.discovery_secondary_sources = sec.get("secondary_sources", "").split(" ")
		config.discovery_stream_sources = sec.get("stream_sources", "").split(" ")
	
	if "post" in parsed:
		sec = parsed["post"]
		config.post_title = sec.get("title", None)
		config.post_title_with_en = sec.get("title_with_en", None)
		config.post_title_postfix_final = sec.get("title_postfix_final", None)
		config.post_flair_id = sec.get("flair_id", None)
		config.post_flair_text = sec.get("flair_text", None)
		config.post_body = sec.get("body", None)
		config.post_poll_title = sec.get("poll_title", None)
		config.batch_thread_post_title = sec.get("batch_thread_title", None)
		config.batch_thread_post_title_with_en = sec.get("batch_thread_title_with_en", None)
		config.batch_thread_post_body = sec.get("batch_thread_body", None)
		for key in sec:
			if key.startswith("format_") and len(key) > 7:
				config.post_formats[key[7:]] = sec[key]
	
	# Services
	for key in parsed:
		if key.startswith("service."):
			service = key[8:]
			config.services[service] = parsed[key]
	
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
		return "subreddit/community missing"
	if config.backend == "reddit":
		if is_bad_str(config.r_username):
			return "reddit username missing"
		if is_bad_str(config.r_password):
			return "reddit password missing"
		if is_bad_str(config.r_oauth_key):
			return "reddit oauth key missing"
		if is_bad_str(config.r_oauth_secret):
			return "reddit oauth secret missing"
	elif config.backend == "lemmy":
		if is_bad_str(config.l_instance):
			return "lemmy instance missing"
		if is_bad_str(config.l_username):
			return "lemmy username missing"
		if is_bad_str(config.l_password):
			return "lemmy password missing"
	else:
		return "no backend configured"
	if is_bad_str(config.post_title):
		return "post title missing"
	if is_bad_str(config.post_body):
		return "post title missing"
	return False
