import redis
from urlparse import urlparse
from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from scrapy.spider import BaseSpider


class RedisMixin(object):
    """Mixin class to implement reading urls from a redis queue."""
    redis_key = None  # use default '<spider>:start_urls'

    def setup_redis(self):
        """Setup redis connection and idle signal.

        This should be called after the spider has set its crawler object.
        """
        if not self.redis_key:
            self.redis_key = '%s:start_urls' % self.name
        # TODO: use REDIS_URL
        host = self.crawler.settings.get('REDIS_HOST', 'localhost')
        port = self.crawler.settings.get('REDIS_PORT', 6379)
        self.server = redis.Redis(host, port)
        # idle signal is called when the spider has no requests left,
        # that's when we will schedule new requests from redis queue
        self.crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)
        self.log("Reading URLs from redis list '%s' at %s:%s." % (self.redis_key, host, port))

    def next_request(self):
        """Returns a request to be scheduled or none."""
        url = self.server.lpop(self.redis_key)
        print "URL = [%s]" % url
        parsed_url = urlparse(url if url else "")
        print "DOMAIN = [%s]" % parsed_url.netloc
        if url and [True for u in self.allowed_Domains if parsed_url.netloc.endswith(u)]:
            return self.make_requests_from_url(url)

    def spider_idle(self):
        """Schedules a request if available, otherwise waits."""
        req = self.next_request()
        if req:
            self.crawler.engine.crawl(req, spider=self)
        raise DontCloseSpider


class RedisSpider(RedisMixin, BaseSpider):
    """Spider that reads urls from redis queue when idle."""

    def set_crawler(self, crawler):
        super(RedisSpider, self).set_crawler(crawler)
        self.setup_redis()
