#! python3

"""this is pixiv module for comiccrawler

Ex:
	http://www.pixiv.net/member_illust.php?id=2211832

"""

import re, execjs
from comiccrawler import Episode, extend, grabhtml, LastPageError, SkipEpisodeError
from safeprint import safeprint
from html import unescape

header = {
	"Referer": "http://www.pixiv.net/member_illust.php"
}
domain = ["www.pixiv.net"]
name = "Pixiv"
noepfolder = True

def loadconfig(config):
	if name not in config:
		config[name] = {}
	extend(config[name], {
		"SESSID": "請輸入Cookie中的PHPSESSID"
	})
	header["Cookie"] = "PHPSESSID=" + config[name]["SESSID"]

def gettitle(html, **kw):
	if "pixiv.user.loggedIn = true" not in html:
		raise Exception("you didn't login!")
	user = re.search("class=\"user\">(.+?)</h1>", html).group(1)
	id = re.search(r"pixiv.context.userId = \"(\d+)\"", html).group(1)
	return "{} - {}".format(id, user)
	
def getepisodelist(html, url=""):
	s = []
	root = re.search("https?://[^/]+", url).group()
	base = re.search("https?://[^?]+", url).group()
	while True:
		ms = re.findall(r'<a href="([^"]+)"><h1 class="title" title="([^"]+)">', html)
		# safeprint(ms)
		for m in ms:
			url, title = m
			uid = re.search("id=(\d+)", url).group(1)
			e = Episode()
			e.title = "{} - {}".format(uid, title)
			e.firstpageurl = root + url
			s.append(e)
			
		un = re.search("href=\"([^\"]+)\" rel=\"next\"", html)
		if un is None:
			break
		u = un.group(1).replace("&amp;", "&")
		safeprint(base + u)
		html = grabhtml(base + u, hd=header)
	return s[::-1]

def getimgurls(html, url=""):
	if "pixiv.user.loggedIn = true" not in html:
		raise Exception("you didn't login!")
		
	base = re.search(r"https?://[^/]+", url).group()
	
	# ugoku
	rs = re.search(r"pixiv\.context\.ugokuIllustFullscreenData\s+= ([^;]+)", html)
	if rs:
		from execjs import eval
		json = rs.group(1)
		o = eval(json)
		return [o["src"]]
		
	# new image layout (2014/12/14)
	rs = re.search(r'class="big" data-src="([^"]+)"', html)
	if rs:
		return [rs.group(1)]
		
	rs = re.search(r'data-src="([^"]+)" class="original-image"', html)
	if rs:
		return [rs.group(1)]
		
	# old image layout
	header["Referer"] = url
	url = re.search(r'"works_display"><a (?:class="[^"]*" )?href="([^"]+)"', html).group(1)
	html = grabhtml(base + "/" + url, header)
	
	if "mode=big" in url:
		# single image
		img = re.search(r'src="([^"]+)"', html).group(1)
		return [img]
	
	if "mode=manga" in url:
		# multiple image
		imgs = []
		
		for match in re.finditer(r'a href="(/member_illust\.php\?mode=manga_big[^"]+)"', html):
			url = base + match.group(1)
			html = grabhtml(url, header)
			img = re.search(r'img src="([^"]+)"', html).group(1)
			imgs.append(img)
			
		# New manga reader (2015/3/18)
		# http://www.pixiv.net/member_illust.php?mode=manga&illust_id=19254298
		if not imgs:
			for match in re.finditer(r'originalImages\[\d+\] = ("[^"]+")', html):
				url = match.group(1)
				url = execjs.eval(url)
				imgs.append(url)
			
		return imgs
		
	# restricted
	rs = re.search('<section class="restricted-content">', html)
	if rs:
		raise SkipEpisodeError
	
	# error page
	rs = re.search('class="error"', html)
	if rs:
		raise SkipEpisodeError
		
	# id doesn't exist
	rs = re.search("pixiv.context.illustId", html)
	if not rs:
		raise SkipEpisodeError

class RestrictPageError(Exception):
	pass
		
def errorhandler(er, ep):
	
	# http://i1.pixiv.net/img21/img/raven1109/10841650_big_p0.jpg
	from urllib.error import HTTPError
	if type(er) is HTTPError:
		if er.code == 404 and "imgurls" in dir(ep):
			p = ep.currentpagenumber - 1
			ep.imgurls[p] = ep.imgurls[p].replace("_big_", "_")
			return True
			
		# Private page?
		if er.code == 403:
			raise SkipEpisodeError

def getnextpageurl(pagenumber, html, url=""):
	pass
	