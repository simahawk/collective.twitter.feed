import json

import requests

from zope import component

from collective.twitter.feed.interfaces import IFeedUtility


def get_timeline(account_id, rendered=False, context=None, request=None):
	Feeder = component.getUtility(IFeedUtility, name="timeline")
	feeder = Feeder(account_id, context=context, request=request)
	return feeder.get_timeline()


# class SmartDict(dict):

# 	def __getattr__(self, k):
# 		return self[k]

# 	def __setattr__(self, k, v):
# 		setattr(self, k, v)


# URL = "https://api.twitter.com/1/statuses/user_timeline.json"
# from zope.globalrequest import getRequest
# from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

# class DummyRenderer(object):
# 	def __init__(self):
# 		self.request = getRequest()
# 		self.context = object()

# def get_timeline(account_id, rendered=False):
# 	data = dict(
# 		screen_name = "simahawk",
# 		count=5,
# 	)
# 	rr = requests.get(URL,params=data)
# 	result = json.loads(rr.text)
# 	if rendered:
# 		template = ViewPageTemplateFile("feed.pt")
# 		dr = DummyRenderer()
# 		result = template(dr,**dict(timeline=result))
# 	return result