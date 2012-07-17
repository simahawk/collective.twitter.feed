from zope import interface
from zope import component
from zope.component import getUtility

from zope.globalrequest import getRequest

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.registry.interfaces import IRegistry

from collective.prettydate.interfaces import IPrettyDate
import DateTime

from collective.twitter.feed.interfaces import IFeedUtility
from collective.twitter.feed.interfaces import IFeeder
import twitter

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
        if account_id == 'default':
            accounts = self.get_accounts()
            if accounts:
                try:
                    account_id,account = accounts.items()[0]
                except IndexError:
                    raise Exception("No default account found!")
        self.account_id = account_id
        self.account = self.get_account(account_id)
        self.api = self._get_api()
        self.request = request or getRequest()
        self.context = context or object()

    def _get_api(self):
        if not self.account: 
            return None
        api = twitter.Api(consumer_key=self.account.get('consumer_key'),
                         consumer_secret=self.account.get('consumer_secret'),
                         access_token_key=self.account.get('oauth_token'),
                         access_token_secret=self.account.get('oauth_token_secret'),)
        return api

    @classmethod
    def enabled(self):
        return bool(self.account)

    def get_account(self, account_id):
        accounts =  self.get_accounts()
        if accounts:
            return accounts.get(account_id)
        return {}

    @classmethod
    def get_accounts(cls):
        registry = component.getUtility(IRegistry)
        accounts = registry.get('collective.twitter.accounts', [])
        return accounts

    def get_timeline(self, user=None,
                           count=5,
                           rendered=False,
                           rendering_options={},
                           template=None):
        if not self.api:
            return None
        if user is None:
            user = self.account_id
        timeline = None
        try:
            timeline = self.api.GetUserTimeline(user, count=count)
        except Exception, e:
            msg = "Something went wrong: %s" % str(e)
            print msg
        if rendered:
            templ = template or self.template
            opts = rendering_options.copy()
            opts.update(dict(
                timeline=timeline,
                tool = self,
            ))
            defaults = dict(
                show_avatars = False,
                pretty_date = True,
                show_header = True,
            )
            for k,v in defaults.items():
                opts[k] = opts.get(k, v)
            timeline = templ(self, **opts)
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
            text = ' '.join(split_text),
            url = self.get_tweet_url(tweet),
            reply_url = self.get_reply_url(tweet),
            retweet_url = self.get_retweet_url(tweet),
            fav_url = self.get_fav_url(tweet),
            profile_img_url = self.get_profile_image_url(tweet),
            screen_name = tweet.GetUser().GetScreenName(),
            date = self.get_date(tweet, pretty_date=pretty_date),
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

    
