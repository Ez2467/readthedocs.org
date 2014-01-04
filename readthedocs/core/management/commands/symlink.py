import logging

from django.core.management.base import BaseCommand
from django.conf import settings

from projects import tasks
from tastyapi import apiv2 as api

import redis

log = logging.getLogger(__name__)

def symlink(slug):
    version_data = api.version().get(project=slug, slug='latest')['results'][0]
    v = tasks.make_api_version(version_data)
    log.info("Symlinking %s" % v)
    tasks.symlink_subprojects(v)
    tasks.symlink_cnames(v)
    tasks.symlink_translations(v)

class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args):
            for slug in args:
                symlink(slug)
        else:
            redis_conn = redis.Redis(**settings.REDIS)
            slugs = redis_conn.keys('rtd_slug:v1:*')
            for slug in slugs:
                log.info("Got slug from redis: %s" % slug)
                symlink(slug)
