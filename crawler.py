#!/usr/bin/env python

from collections import defaultdict
from time import time
import itertools
import re
import socks
import socket
import sqlite3 # WIP
import sys
import urllib.parse

def create_connection_noresolv(address, timeout=None, source_address=None):
	#sock = socket.socket() # torify
	sock = socks.socksocket()

	try:
		sock.connect(address)

	except socks.ProxyConnectionError:
		sys.stderr.write("Can't connect to TOR proxy, start tor service first\n\n")
		sys.exit(1)

	return sock

socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)

socket.socket = socks.socksocket
socket.create_connection = create_connection_noresolv

import urllib.request

debug = True

def debug_print(msg):
	if debug:
		print(msg)


class Database():
	def create_cursor(self):
		dbname = "/data/Desktop/test.db"

		self.db = sqlite3.connect(dbname)
		self.db_c = self.db.cursor()
		self.db.isolation_level = None # disable autocommit

		debug_print("Called create_cursor() with dbname " + repr(dbname))

		self.db_c.execute("BEGIN")


	# Table format:
	#
	# path: index, it's a relative path to a file in the link
	# title: the title of the page/file of the path
	# crawled: if the page wasn't crawled yet, is 0 or a previous session
	#		  self.crawler_id, else is crawler_id

	def create_table(self, link): # get link list
		self.db_c.execute("CREATE TABLE IF NOT EXISTS\"" + link + \
						  "\"(path text, title text, crawled int)")

		debug_print("Called create_table(" + repr(link) + ')')
		#self.db.commit()

	def path_crawled(self, link, path): # this function can be used even to check if path was scanned yet
		# if returns none, it means the path it's not in the table

		self.db_c.execute("SELECT crawled FROM \"" + link + \
								"\" WHERE path=\"" + path + '"')

		crawled = self.db_c.fetchone()

		if crawled: # debug
			debug_print(repr(path) + " found in table " + repr(link) + '\n')

		else: # debug
			debug_print("\033[1;31m" + repr(path) + " not found in table " + repr(link) + "\033[0m")

		return crawled

	def add_path(self, link, path, title=None, crawled=0): # title not yet implemented
		self.db_c.execute("INSERT INTO \"" + link + "\" VALUES(?,?,?)", \
		(path, "NOT IMPLEMENTED", crawled)) # added 0 because not scanned yet

		debug_print("added path " + repr(path) + " in table " + repr(link) + '\n')

	def close_db(self):
		self.db.commit()

		debug_print("Closed db")

		self.db.close()


# TODO: rename class
class Utils():
	def __init__(self):
		int_str = "()href=['\"]?(?![a-z]*:\/\/)([^'\" >]+)" # get internal urls only
		self.int_regex = re.compile(int_str, re.IGNORECASE)

		ext_str = "((?:https?:\/\/)?[2-7a-z]{16}\.onion)(\/+(?:[^\s<>\"])*)*" # get external urls
		self.ext_regex = re.compile(ext_str, re.IGNORECASE)

		url_str = "[2-7a-z]{16}\.onion" # get .onion addresses, excluding scheme
		self.url_regex = re.compile(url_str, re.IGNORECASE)

		scheme_str = "^https?:\/\/" # get scheme only
		self.scheme_regex = re.compile(scheme_str, re.IGNORECASE)

		# used to determine if a path was scanned or not in the current session
		self.crawler_id = int(time())

		self.db_obj = Database()
		self.db_obj.create_cursor()
		debug_print("Called create_cursor() from Utils.__init__()")

	def populate_db(self, regex, text, referer=None):
		for match in regex.finditer(text):
			link = match.group(1)
			path = match.group(2)

			if link == '':
				link = referer

			if not self.scheme_regex.match(link):
				link = "http://" + link

			self.db_obj.create_table(link)

			if path != None:
				path = path.replace(
					"&amp;", '&').replace("&lt;", '<').replace(
					"&gt;", '>').replace("&quot;", '"').replace(
					"&#39;", '\'').replace("//", '/')

			else:
				path = '/'

			# if the path isn't in the table
			if not self.db_obj.path_crawled(link, path):
				self.db_obj.add_path(link, path)

	# TODO: merge with get_links()
	def add_referer(self, referer):
		self.popoulate_db(self.ext_regex, referer)

	def get_links(self, text, url):
		referer = self.clean_url(url)

		self.populate_db(self.int_regex, text, referer)
		self.populate_db(self.ext_regex, text)
		self.db_obj.close_db()

	def clean_url(self, url):
		m = self.url_regex.search(url)
		url_clean = m.group()

		return url_clean


def crawl(url):
	pass


obj = Utils()
url = "http://zqktlwi4fecvo6ri.onion/wiki/index.php/Main_Page"
debug_print("url = " + repr(url))
#url = "http://bbbburnsnx2za2tp.onion/"
#url = "http://skunksworkedp2cg.onion/"
#url = "http://7sfwrqmjhne57tgn.onion/"
req = urllib.request.urlopen(url)

# oflline mode debug
#with open("/data/Desktop/link") as f:
#	text = f.read()

#print("text/" in req.getheader("Content-Type"), '\n') # must check b4 going deeper
debug_print("Started download")
text = req.read().decode("ascii", "ignore")
req.close()
debug_print("Downloaded, calling get_links(" + repr(url) + ")\n")
obj.get_links(text, url)
