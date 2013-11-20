from time import time
import logging

from zope.component import getUtility
from zope import schema
from zope.interface import Interface

from plone.tiles import PersistentTile
from plone.memoize import ram

from collective.twitter.feed.interfaces import IFeedUtility
from collective.twitter.feed import _

logger = logging.getLogger('[twitter.feed]')


class ITwitterFeedTile(Interface):
    """ base schema for our tiles
    """

    tile_title = schema.TextLine(
        title=u'Feed title',
        required=False,
        default=u'',
    )
    tw_account = schema.Choice(
        title=_(u'Twitter account'),
        description=_(u"Which twitter account to use."),
        required=True,
        vocabulary='twitter.accounts'
    )

    tw_user = schema.TextLine(
        title=_(u'Twitter user'),
        description=_(u"The Twitter user you wish to get feed from "
                      u"(you can include or omit the initial @)."),
        required=False
    )

    search = schema.TextLine(
        title=_(u'Search terms'),
        description=_(u"Search terms, can be also hashtags."
                      u"If you provide 'Twitter user' the search will be"
                      u"filtered on tweets from that user"),
        required=False
    )

    show_avatars = schema.Bool(
        title=_(u'Show avatars'),
        description=_(u"Show people's avatars."),
        required=False
    )

    max_results = schema.Int(
        title=_(u'Maximum results'),
        description=_(u"The maximum results number."),
        required=True,
        default=5
    )

    pretty_date = schema.Bool(
        title=_(u'Pretty dates'),
        description=_(u"Show dates in a pretty format (ie. '4 hours ago')."),
        default=True,
        required=False
    )


def cache_key_simple(func, var):
    #let's memoize for 10 minutes or if any value of the portlet is modified
    timeout = time() // (60 * 10)
    return (timeout,
            var.data['tw_account'],
            var.data['tw_user'],
            var.data['max_results'])


class TwitterFeedTile(PersistentTile):
    # implements(ITwitterFeedTile)

    @property
    def tile_title(self):
        return self.data['tile_title']

    @ram.cache(cache_key_simple)
    def results(self):
        results = ''
        tw_user = self.data['tw_user']
        search = self.data['search']
        if not tw_user and not search:
            logger.info('No twitter account set up.')
            return results

        logger.info("Getting tweets.")

        max_results = self.data['max_results']
        rendering_options = {
            'show_header': not self.tile_title,
        }

        try:
            if search:
                results = self.feed_tool.get_search(
                    search,
                    user=tw_user,
                    count=max_results,
                    rendered=1,
                    rendering_options=rendering_options
                )
            else:
                results = self.feed_tool.get_timeline(
                    tw_user,
                    count=max_results,
                    rendered=1,
                    rendering_options=rendering_options
                )
            logger.info("%s results obtained. Limited to %s." % (len(results),
                                                                 max_results))
        except Exception, e:
            logger.info("Something went wrong: %s." % e)
            results = ''
        return results

    @property
    def feed_tool(self):
        util = getUtility(IFeedUtility, name="timeline")
        return util(self.data['tw_account'],
                    request=self.request,
                    context=self.context)
