import pygubu
import sys, os, yaml
from collections import OrderedDict

def represent_ordereddict(dumper, data):
	value = []
	for item_key, item_value in data.items():
		node_key = dumper.represent_data(item_key)
		node_value = dumper.represent_data(item_value)
		value.append((node_key, node_value))
	return yaml.nodes.MappingNode("tag:yaml.org,2002:map", value)
yaml.add_representer(OrderedDict, represent_ordereddict)

current_file = "default.yaml"
current_docs = []
current_doc = 0

info_keys = ["mal", "anidb", "anilist"]
stream_keys = ["crunchyroll", "funimation"]

def load_current_file():
	print("Loading current file: {}".format(current_file))
	global current_docs, current_doc
	try:
		with open(current_file, "r", encoding="UTF-8") as f:
			current_docs = list(yaml.load_all(f))
		current_doc = len(current_docs)
	except FileNotFoundError:
		pass
	except yaml.YAMLError:
		print("Failed to parse edit file")

def save_current_file():
	print("Saving current file: {}".format(current_file))
	def order_dict(d):
		return OrderedDict([
			("title", d["title"]),
			("type", d["type"]),
			("has_source", d["has_source"]),
			("info", OrderedDict([
				(key, d["info"][key] if key in d["info"] else "") for key in info_keys
			])),
			("streams", OrderedDict([
				(key, d["streams"][key] if key in d["streams"] else "") for key in stream_keys
			]))
		])
	
	try:
		sorted_docs = [order_dict(doc) for doc in current_docs]
		with open(current_file, "w", encoding="UTF-8") as f:
			yaml.dump_all(sorted_docs, f, default_flow_style=False, indent=4, allow_unicode=True)
	except:
		from traceback import print_exc
		print_exc()
		return False
	return True

class Application:
	def __init__(self):
		self.builder = pygubu.Builder()
		self.builder.add_from_file("editor.ui")
		self.mainwindow = self.builder.get_object("mainwindow")
		
		self.builder.connect_callbacks(self)
		self.mainwindow.protocol("WM_DELETE_WINDOW", self.on_close_window)
	
	def _get_inputs(self):
		title = self.builder.get_variable("name")
		atype = self.builder.get_variable("type")
		has_source = self.builder.get_variable("has_source")
		return title, atype, has_source, \
			   {key: self.builder.get_variable(key+"_url") for key in info_keys}, \
			   {key: self.builder.get_variable(key+"_url") for key in stream_keys}
	
	def set_doc(self):
		self.clear_doc()
		
		print("Loading doc {}".format(current_doc))
		self.update_title()
		doc = current_docs[current_doc]
		
		title, atype, has_source, info_urls, stream_urls = self._get_inputs()
		title.set(doc["title"])
		atype.set(doc["type"])
		has_source.set(doc["has_source"])
		if "info" in doc:
			info = doc["info"]
			for key in info_keys:
				if key in info:
					info_urls[key].set(info[key])
		if "streams" in doc:
			streams = doc["streams"]
			for key in stream_keys:
				if key in streams:
					stream_urls[key].set(streams[key])
	
	def clear_doc(self):
		title, atype, has_source, info_urls, stream_urls = self._get_inputs()
		title.set("")
		atype.set("tv")
		has_source.set(True)
		for _, url in info_urls.items():
			url.set("")
		for _, url in stream_urls.items():
			url.set("")
	
	def update_title(self):
		updating = "creating" if current_doc >= len(current_docs) else "updating"
		file_name = os.path.basename(current_file)
		file_label = self.builder.get_object("open_label")
		file_label["text"] = "{} ({} shows), {}".format(file_name, len(current_docs), updating)
	
	def on_find_button_clicked(self):
		global current_doc
		find_text = self.builder.get_variable("find_text").get().lower()
		if len(find_text) > 0:
			for (i, doc) in enumerate(current_docs):
				name = doc["title"].lower()
				if find_text in name:
					current_doc = i
					self.set_doc()
		else:
			current_doc = 0
			if len(current_docs) > 0:
				self.set_doc()
			else:
				self.clear_doc()
	
	def on_save_button_clicked(self):
		global current_doc
		self.store_state()
		if save_current_file():
			current_doc = len(current_docs)
			self.update_title()
			self.clear_doc()
	
	def on_next_button_clicked(self):
		global current_doc
		self.store_state()
		if save_current_file():
			current_doc += 1
			self.update_title()
			if current_doc < len(current_docs):
				self.set_doc()
			else:
				self.clear_doc()
	
	def on_close_window(self, event=None):
		self.mainwindow.destroy()
	
	def store_state(self):
		global current_docs
		title, atype, has_source, info_urls, stream_urls = self._get_inputs()
		
		title = title.get()
		print("  title={}".format(title))
		atype = atype.get()
		print("  type={}".format(atype))
		has_source = has_source.get()
		print("  has_source={}".format(has_source))
		
		info = {}
		for key in info_keys:
			url = info_urls[key].get() if key in info_urls else ""
			print("  {}={}".format(key, url))
			info[key] = url
			
		streams = {}
		for key in stream_keys:
			url = stream_urls[key].get() if key in stream_urls else ""
			print("  {}={}".format(key, url))
			streams[key] = url
		
		show = {
			"title": title,
			"type": atype,
			"has_source": has_source,
			"info": info,
			"streams": streams
		}
		if current_doc >= len(current_docs):
			print("Appending")
			current_docs.append(show)
			print("  New length: {}".format(len(current_docs)))
		else:
			print("Setting to {}".format(current_doc))
			current_docs[current_doc] = show
	
	def run(self):
		load_current_file()
		self.update_title()
		self.clear_doc()
		
		self.mainwindow.mainloop()

if __name__ == "__main__":
	if len(sys.argv) > 1:
		current_file = sys.argv[1]
		print("Using file: {}".format(current_file))
	
	app = Application()
	app.run()
