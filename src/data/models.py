from datetime import datetime

class Show:
	def __init__(self, id, name, length, type, has_source):
		# Note: arguments are order-sensitive
		self.id = id
		self.name = name
		self.length = length
		self.type = type
		self.has_source = has_source == 1
	
	def __str__(self):
		return "Show: {} (id={}, type={}, len={})".format(self.name, self.id, self.type, self.length)

class Episode:
	def __init__(self, number, name, link, date):
		# Note: arguments are order-sensitive
		self.number = number
		self.name = name		# Not stored in database
		self.link = link
		self.date = datetime(*date[:6])
	
	def __str__(self):
		return "Episode: {} | Episode {}, {} ({})".format(self.date, self.number, self.name, self.link)
	
	@property
	def is_live(self, local=False):
		now = datetime.now() if local else datetime.utcnow()
		return now >= self.date

class Service:
	def __init__(self, id, key, name, enabled):
		# Note: arguments are order-sensitive
		self.id = id
		self.key = key
		self.name = name
		self.enabled = enabled == 1
		
	def __str__(self):
		return "Service: {} ({})".format(self.key, self.id, self.enabled)

class Stream:
	def __init__(self, service, show, site_key, site_name, remote_offset, display_offset, active):
		# Note: arguments are order-sensitive
		self.service = service
		self.show = show
		self.site_key = site_key
		self.site_name = site_name
		self.remote_offset = remote_offset
		self.display_offset = display_offset
		self.active = active
	
	def __str__(self):
		return "Stream: {} ({}@{}), {} {}".format(self.show, self.site_key, self.service, self.remote_offset, self.display_offset)
	
