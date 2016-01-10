from datetime import datetime

class Show:
	def __init__(self, id, name, length, type):
		self.id = id
		self.name = name
		self.length = length
		self.type = type
	
	def __str__(self):
		return "Show: {} (id={}, type={}, len={})".format(self.name, self.id, self.type, self.length)

class Episode:
	def __init__(self, number, name, link, date):
		self.number = number
		self.name = name
		self.link = link
		self.date = datetime(*date[:6])
	
	def __str__(self):
		return "Episode: {} | Episode {}, {} ({})".format(self.date, self.number, self.name, self.link)
	
	@property
	def is_live(self, local=False):
		now = datetime.now() if local else datetime.utcnow()
		return now >= self.date

class Stream:
	def __init__(self, service, show, site_key, remote_offset, display_offset):
		self.service = service
		self.show = show
		self.site_key = site_key
		self.remote_offset = remote_offset
		self.display_offset = display_offset
	
	def __str__(self):
		return "Stream: {} ({}@{}), {} {}".format(self.show, self.site_key, self.service, self.remote_offset, self.display_offset)
