# DATABASE_NAME = 'data.sqlite'

import os
# os.environ['SCRAPERWIKI_DATABASE_NAME'] = DATABASE_NAME

import scraperwiki
import lxml.html
from pprint import pprint
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import re

result_schema = {
        'rank': None,
        'bib': None,
        'fis_code': None,
        'name': None,
        'year_of_birth': None,
        'nation': None,
        'run_1': None,
        'run_2': None,
        'total_time': None,
        'diff': None,
        'fis_points': None,
}

# generator of FIS race links
def race_link_results(url):
    html = scraperwiki.scrape(url)
    root = lxml.html.fromstring(html)
    result_table = root.cssselect("table.fisfootable")[0]
    status_cells = result_table.cssselect("td.status")
    for status_cell in status_cells:
        result_div = status_cell.cssselect("div")[1]
        for element, attribute, link, pos in result_div.iterlinks():
            event_page = scraperwiki.scrape(link)
            event_root = lxml.html.fromstring(event_page)
            event_rows = event_root.cssselect("table.footable tbody tr")
            for event_row in event_rows:
                last_cell = event_row.cssselect("td:last-child")[0]
                for race_links in last_cell.iterlinks():
                    extra = {
                        'date': get_cell_value(event_row.cssselect("td")[1], "span a"),
                        'place': get_cell_value(event_row.cssselect("td")[2], "span a"),
                        'country': get_cell_value(event_row.cssselect("td")[3], "a span"),
                        'codex': get_cell_value(event_row.cssselect("td")[4], "a"),
                        'discipline': get_cell_value(event_row.cssselect("td")[5], "a"),
                    }
                    yield (race_links[2], extra)

def get_cell_value(element, css):
    return element.cssselect(css)[0].text_content()

FIS_URL = "http://data.fis-ski.com/alpine-skiing/results.html"
for link, raceinfo in race_link_results(FIS_URL):
    # html = scraperwiki.scrape(link)
    # root = lxml.html.fromstring(html)
    # result_table = root.cssselect("table.fisfootable")[0]
    print(link)
    print(raceinfo['date'])
    print("oe")

# # Write out to the sqlite database using scraperwiki library
# data = {"name": "susan", "occupation": "software developer"}
# scraperwiki.sqlite.save(unique_keys=['name'], data=data, table_name="data")
# 
# An arbitrary query against the database
# pprint(scraperwiki.sql.select("* from data where 'name'='susan'"))