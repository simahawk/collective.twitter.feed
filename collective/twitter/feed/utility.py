#-*- coding: utf-8 -*-
import urllib
import DateTime
import twitter
import logging

from zope import interface
from zope import component
from zope.component import getUtility
from zope.globalrequest import getRequest

from plone.registry.interfaces import IRegistry

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.prettydate.interfaces import IPrettyDate

from collective.twitter.feed.interfaces import IFeedUtility
from collective.twitter.feed.interfaces import IFeeder


logger = logging.getLogger(__file__)

# We need to make URLs, hastags and users clickable.
URL_TEMPLATE = """
<a href="%s" target="blank_">%s</a>
"""
HASHTAG_TEMPLATE = """
<a href="http://twitter.com/#!/search?q=%s" target="blank_">%s</a>
"""
USER_TEMPLATE = """
<a href="http://twitter.com/#!/%s" target="blank_">%s</a>
"""


class AttrDict(dict):

    def __getattr__(self, k):
        return self[k]

    def __setattr__(self, k, v):
        self[k] = v


class Feeder(object):
    interface.classProvides(IFeedUtility)
    interface.implements(IFeeder)

    account_id = ''
    account = {}
    api = None
    context = None
    request = None
    template = ViewPageTemplateFile("feed.pt")

    def __init__(self, account_id, context=None, request=None):
        assert account_id
        self.account_id, self.account = self.get_account(account_id)
        self.api = self._get_api()
        self.request = request or getRequest()
        self.context = context or object()

    def _get_api(self):
        if not self.account:
            return None
        api = twitter.Api(
            consumer_key=self.account.get('consumer_key'),
            consumer_secret=self.account.get('consumer_secret'),
            access_token_key=self.account.get('oauth_token'),
            access_token_secret=self.account.get('oauth_token_secret')
        )
        return api

    def enabled(self):
        return bool(self.account)

    def get_account(self, account_id):
        account = {}
        accounts = self.get_accounts() or {}
        if account_id == 'default' and accounts:
            try:
                account_id, account = accounts.items()[0]
            except IndexError:
                raise Exception("No default account found!")
        else:
            account = accounts.get(account_id)
        return account_id, account

    @classmethod
    def get_accounts(cls):
        registry = component.getUtility(IRegistry)
        accounts = registry.get('collective.twitter.accounts', [])
        return accounts

    def _get_timeline(self, user, count=5):
        timeline = None
        try:
            timeline = self.api.GetUserTimeline(user, count=count)
        except Exception, e:
            msg = "Something went wrong: %s" % str(e)
            logger.error(msg)
        return timeline

    def _get_search(self, term, count=5):
        timeline = None
        try:
            timeline = self.api.GetSearch(term,
                                          count=count,
                                          include_entities=True)
        except Exception, e:
            msg = "Something went wrong: %s" % str(e)
            logger.error(msg)
        return timeline

    def _render(self, timeline, template, **rendering_options):
        templ = template or self.template
        opts = rendering_options.copy()
        opts.update(dict(
            timeline=timeline,
            tool=self,
        ))
        defaults = dict(
            show_avatars=False,
            pretty_date=True,
            show_header=True,
        )
        for k, v in defaults.iteritems():
            opts[k] = opts.get(k, v)
        timeline = templ(self, **opts)
        return timeline

    def get_timeline(self,
                     user=None,
                     count=5,
                     rendered=False,
                     rendering_options={},
                     template=None):

        if not self.enabled():
            return None

        if user is None:
            # if no user is given use the default one
            user = self.account_id

        timeline = self._get_timeline(user, count=count)

        if rendered:
            timeline = self._render(timeline, template, **rendering_options)
        return timeline

    def get_search(self,
                   search_term,
                   user=None,
                   count=5,
                   rendered=False,
                   rendering_options={},
                   template=None):

        if not self.enabled():
            return None

        if user:
            search_term += '+FROM:%s' % user

        search_term = urllib.quote(search_term)

        timeline = self._get_search(search_term, count=count)

        if rendered:
            timeline = self._render(timeline, template, **rendering_options)
        return timeline

    def get_tweet_data(self, tweet, pretty_date=True):
        full_text = tweet.GetText()
        split_text = full_text.split(' ')

        # Now, lets fix links, hashtags and users
        for index, word in enumerate(split_text):
            if word.startswith('@'):
                # This is a user
                split_text[index] = USER_TEMPLATE % (word[1:], word)
            elif word.startswith('#'):
                # This is a hashtag
                split_text[index] = HASHTAG_TEMPLATE % ("%23" + word[1:], word)
            elif word.startswith('http'):
                # This is a hashtag
                split_text[index] = URL_TEMPLATE % (word, word)

        result = AttrDict(
            text=' '.join(split_text),
            url=self.get_tweet_url(tweet),
            reply_url=self.get_reply_url(tweet),
            retweet_url=self.get_retweet_url(tweet),
            fav_url=self.get_fav_url(tweet),
            profile_img_url=self.get_profile_image_url(tweet),
            screen_name=tweet.GetUser().GetScreenName(),
            date=self.get_date(tweet, pretty_date=pretty_date),
        )
        return result

    def get_tweet_url(self, tweet):
        return "https://twitter.com/%s/status/%s" % \
            (tweet.user.screen_name, tweet.id)

    def get_reply_url(self, tweet):
        return "https://twitter.com/intent/tweet?in_reply_to=%s" % tweet.id

    def get_retweet_url(self, tweet):
        return "https://twitter.com/intent/retweet?tweet_id=%s" % tweet.id

    def get_fav_url(self, tweet):
        return "https://twitter.com/intent/favorite?tweet_id=%s" % tweet.id

    def get_date(self, tweet, pretty_date=True):
        if pretty_date:
            # Returns human readable date for the tweet
            date_utility = getUtility(IPrettyDate)
            date = date_utility.date(tweet.GetCreatedAt())
        else:
            date = DateTime.DateTime(tweet.GetCreatedAt())

        return date

    def get_profile_image_url(self, tweet):
        return tweet.GetUser().GetProfileImageUrl()
