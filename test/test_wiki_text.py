import logging
from db import WikiPage

logging.basicConfig(level=logging.DEBUG)


def test_wiki_fulltext(wiki_db):
    # These will be pretty slow tests: around 2700 wikipedia pages are indexed and added to the DB
    # Could take up to a minute
    assert len(wiki_db[WikiPage]) > 0
