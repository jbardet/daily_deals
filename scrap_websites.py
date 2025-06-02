import asyncio
from asyncio import as_completed, run
from datetime import date, datetime, time, timedelta
from pathlib import Path
import re
import numpy as np

from bs4 import BeautifulSoup
from config import EMAIL_SENDER, EMAIL_RECIPIENTS, EMAIL_PASSWORD
from aiohttp import ClientSession
# from jsondatetime import jsondatetime as json
import json
import time
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# import scrapy
# from scrapy.crawler import CrawlerProcess
# from scrapy.spiders import Spider
from deep_translator import GoogleTranslator
import requests
from create_email import main as create_email

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
# from PIL import Image
import urllib.request
import ssl
from email.utils import make_msgid
from email.headerregistry import Address
import html
import mimetypes
import json
from pathlib import Path
from email.message import EmailMessage
from urllib.request import Request, urlopen
import re
from pathlib import Path

path = Path(__file__).with_name("todays_ids.json")
path.touch()

config_path = Path(__file__).with_name("config.json")
CONFIG: dict = json.loads(config_path.read_text())

try:
    TODAYS_IDS: dict = json.loads(path.read_text().strip() or "{}")
except UnicodeDecodeError:
    with open(path, encoding = "ISO-8859-1") as file:
        TODAYS_IDS: dict = json.loads(file.read().strip())
        print(TODAYS_IDS)

async def digitec(session: ClientSession):
    url = "https://www.digitec.ch/api/graphql/get-daily-deal-previews"

    payload = json.dumps(
        [
            {
                "operationName": "GET_DAILY_DEAL_PREVIEWS",
                "variables": {"portalIds": [25, 22]},
                "query": (
                    "query GET_DAILY_DEAL_PREVIEWS($portalIds: [Int!]) {\n  dailyDeal {\n    previews(portalIds:"
                    " $portalIds) {\n      portalId\n      product {\n        ...ProductWithOffer\n      }\n    }\n "
                    " }\n}\n\nfragment ProductWithOffer on ProductWithOffer {\n  product {\n   "
                    " ...ProductMandatorIndependent\n  }\n  offer {\n    ...ProductOffer\n  }\n}\n\nfragment"
                    " ProductMandatorIndependent on ProductV2 {\n  id\n  productId\n  name\n  nameProperties\n "
                    " productTypeName\n  brandId\n  brandName\n  averageRating\n  totalRatings\n  images {\n    url\n  "
                    "  height\n    width\n  }\n}\n\nfragment ProductOffer on OfferV2 {\n  id\n  productId\n  price {\n "
                    "   amountInclusive\n    currency\n  }\n  volumeDiscountPrices {\n    price {\n      amountInclusive\n     "
                    " currency\n    }\n  }\n  salesInformation {\n    numberOfItems\n    numberOfItemsSold\n   "
                    " isEndingSoon\n    validFrom\n  }\n  insteadOfPrice {\n    price {\n      amountInclusive\n     "
                    " currency\n    }\n  }\n}"
                ),
            }
        ]
    )

    headers = {
        "Host": "www.digitec.ch",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.120"
            " Safari/537.36"
        ),
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://www.digitec.ch",
        "Accept-Encoding": "gzip, deflate",
    }

    async with session.post(url, headers=headers, data=payload) as response:
        return digitec_data(await response.json())


async def digitec_data(data):
    product_wrappers = data[0]["data"]["dailyDeal"]["previews"]
    for wrapper in product_wrappers:
        product = wrapper["product"]["product"]
        offer = wrapper["product"]["offer"]
        portal = "digitec" if wrapper["portalId"] == 25 else "galaxus"

        info = {
            "id": product["productId"],
            "name": GoogleTranslator(source='auto', target='en').translate(product["name"]),
            "brand": product["brandName"],
            "rating": product["averageRating"],
            "rating_top": 5,
            "description": GoogleTranslator(source='auto', target='en').translate(f"{product['productTypeName']}, {product['nameProperties']}".strip(" ,")),
            "image": product["images"][0]["url"],
            "price_before": offer["insteadOfPrice"]["price"]["amountInclusive"] if offer["insteadOfPrice"] else None,
            "price_after": offer["price"]["amountInclusive"],
            "quantity_total": offer["salesInformation"]["numberOfItems"],
            "quantity_sold": offer["salesInformation"]["numberOfItemsSold"],
            "url": f"https://www.{portal}.ch/product/{product['productId']}",
            "portal": portal.title() + " Tagesangebot",
            "currency": "CHF",
            "next_sale_at": datetime.combine(date.today(), datetime.min.time()) + timedelta(days=1),
            "current_sale_since": date.today(),
        }

        info["percent_available"] = (1 - info["quantity_sold"] / info["quantity_total"]) * 100

        yield info


async def brack(session, type = None):
    url = "https://daydeal.ch/fr/"
    if type is not None:
        url+="category/"+type
    async with session.get(url) as response:
        return brack_data(await response.text(), type, url)


async def brack_data(raw, type, url):
    html = BeautifulSoup(raw, "html.parser")

    today = datetime.combine(date.today(), datetime.min.time())
    now = datetime.now()
    if type is None:
        portal = "Brack / daydeal.ch Tagesangebot"
        next_sale_at = today + timedelta(hours=9)
        next_sale_at = next_sale_at if now.hour < 9 else (next_sale_at + timedelta(days=1))
        current_sale_since = next_sale_at - timedelta(days=1)
        current_id = current_sale_since.strftime("%d%m%Y")
        class_ = "ProductMain-Title"
        i=0
    else:
        portal = "Brack / daydeal.ch "+type
        next_sale_at = today + timedelta(days=7 - today.weekday(), hours=9)
        next_sale_at = next_sale_at - timedelta(days=7) if today.weekday() == 0 and now.hour < 9 else next_sale_at
        current_sale_since = next_sale_at - timedelta(days=7)
        current_id = current_sale_since.strftime("%d%m%Y")
        class_ = "ProductMain-Title"
        if type == "it-multimedia":
            i=1
        elif type == "maison-habitat":
            i=2
        elif type == "supermarche-droguerie":
            i=3
        elif type == "famille-bebe":
            i=4
        elif type == "bricolage-hobby":
            i=5
        elif type == "sport-loisirs":
            i=6

    try:
        percent_available =  int(re.sub(r"\D", "", html.find(class_="ProgressBar-TextValue").text))
    except AttributeError:
        percent_available = 0

    info = {
        "name": GoogleTranslator(source='auto', target='en').translate(html.find(class_=class_).text),
        "brand": "",
        "id": current_id,
        "rating": -1,
        "rating_top": -1,
        "description": GoogleTranslator(source='auto', target='en').translate(html.find(class_="ProductMain-Subtitle").text),
        "image": html.find(class_="ProductMain-Image").attrs["src"],
        "price_before": float(re.search(r"\d+(\.\d+)?", html.find_all(class_="Price-OldPriceValue")[i].text).group()),
        "price_after": float(re.search(r"\d+(\.\d+)?", html.find_all(class_="Price-Price")[i].text).group()),
        "quantity_total": -1,
        "quantity_sold": -1,
        "percent_available": percent_available,
        "portal": portal,
        "url": url,
        "currency": "CHF",
        "next_sale_at": next_sale_at,
        "current_sale_since": current_sale_since,
    }

    yield info

async def twenty_min(session, day=True):
    # path = 'https://myshop.20min.ch/fr'
    url = "https://api.myshop.20min.ch/api/v2/shop/deals"
    if not day:
        # path += "/category/offre-hebdomadaire"
        url += "?wochenangebot"
    # driver = webdriver.Edge()
    # driver.get(path)
    # spider = MySpider()
    # process = CrawlerProcess()
    # process.crawl(MySpider)
    # process.start()
    # res = scrapy.Request(url=path)
    # time.sleep(5)
    # async with driver.get(path) as response:
    #     return twenty_min_data(await response.text(), day)
    # return twenty_min_data(driver, day)
    return twenty_min_data(requests.get(url), day, url)


async def twenty_min_data(response, day=True, url=None):
    today = datetime.combine(date.today(), datetime.min.time())
    if day:
        portal = "20min Tagesangebot"
        next_sale_at = today + timedelta(days=1)
        current_id = today.strftime("%d%m%Y")
        current_sale_since = today
    else:
        portal = "20min Wochenangebot"
        next_sale_at = today + timedelta(days=7 - today.weekday())
        current_sale_since = next_sale_at - timedelta(days=7)
        current_id = current_sale_since.strftime("%d%m%Y")

    # 20 Minutes does not work with BeautifulSoup but with Selenium
    # html = BeautifulSoup(raw, "html.parser")
    print(response.json())
    try:
        res = response.json()['hydra:member'][0]
    except IndexError:
        return
    # There are more than one deal so will show them all
    infos = []
    for i, res in enumerate(response.json()['hydra:member']):
        info = {
            "name": GoogleTranslator(source='auto', target='en').translate(res['title']),
            "brand": res['mutualBrand']['name'],
            "id": current_id,
            "rating": -1,
            "rating_top": -1,
            "description": GoogleTranslator(source='auto', target='en').translate(res['homeDescription']),
            "image": res['coverPhotoPath'],
            "price_before": res['originalPrice']/100,
            "price_after": res['price']/100,
            "quantity_total": res['productsAmount'],
            "percent_available": res['remainingStockPercent'],
            "portal" : portal+str(i),
            "url": 'https://myshop.20min.ch/en/products/'+res['forthLink'].split("/")[-1],
            "currency": "CHF",
            "next_sale_at": next_sale_at,
            "current_sale_since": current_sale_since
        }
        info["quantity_sold"] = info["quantity_total"] * (info["percent_available"] / 100)
        infos.append(info)
    yield infos


def clean_money(money):
    """Unify money representation

    None   => None
    i10    => "10"
    f22.00 => "22"
    f22.90 => "22.90"
    """
    if money is None:
        return
    if isinstance(money, float) and int(money) == money:
        money = int(money)
    if isinstance(money, float):
        return f"{money:.2f}"
    return str(money)

def create_htm_from_deals(data: dict, msgRoot: EmailMessage):
    """
    Creates the text and images to add to the email so that we haev all needed
    information in one place.

    :param data: the scrapped informations from the websites
    :type data: dict
    """

    cids = [make_msgid()[1:-1] for _ in range(len(data))]
    txt = ""
    for i, offer_dict in enumerate(data):
        offer_portal = offer_dict["portal"]

        price_before = clean_money(offer_dict["price_before"])
        price_after = clean_money(offer_dict["price_after"])

        if not price_before:
            price = f"{price_after} {offer_dict['currency']}"
        else:
            price = f"<s>{price_before} {offer_dict['currency']}</s> {price_after} {offer_dict['currency']}"

        current_sale_since = offer_dict["current_sale_since"].strftime("%d.%m.%Y")
        if isinstance(offer_dict["current_sale_since"], datetime):
            current_sale_since = offer_dict["current_sale_since"].strftime("%d.%m.%Y %H:%M")

        msgRoot.set_content('[image: {title}]'.format(title=offer_portal))
        txt+=f"<h1>{offer_dict['name']}</h1>"
        txt+=f"<h2>{price}, availability: {round(offer_dict['percent_available'])}%</h2>"
        txt+='<img src="cid:{cid}" alt="{alt}" width="400" height="200"/>'.format(cid=cids[i], alt=html.escape(offer_portal, quote=True))
        if len(offer_dict['description']) > 0:
            txt+=f"<p>{offer_dict['description']}</p>"
        txt+=f"<p><a href='{offer_dict['url']}'> Link </a></p>"
        txt+=f"<p>From: {current_sale_since}, until: {offer_dict['next_sale_at']}</p>"
        if offer_dict['rating']>0:
            txt+=f"<p>Rating: {offer_dict['rating']}/{offer_dict['rating_top']}</p>"
        if offer_dict['toppreise'][0] is not None:
            txt+=f"<p><a href='{offer_dict['toppreise'][-1]}'>Toppreise</a>: {offer_dict['toppreise'][0]}: {offer_dict['toppreise'][1]} <b>{offer_dict['toppreise'][2]}</b></p>"
        else:
            txt+=f"<p><a href='https://www.toppreise.ch/fr'>Toppreise </a>: No data. Look by yourself</p>"
    msgRoot.add_alternative(txt, subtype='html')

    for i, offer_dict in enumerate(data):
        offer_portal = offer_dict['portal']
        # load img
        offer_portal = re.sub("/", " ", offer_portal)
        URL = offer_dict['image']
        path = Path(f'/home/jbardet/airflow/daily_deals/{offer_portal}.jpg')
        req = Request(
            url=URL,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        webimg = urlopen(req).read()
        with open(path, 'wb') as f:
            f.write(webimg)
        # with urllib.request.urlopen(URL, headers={'User-Agent': 'Mozilla/5.0'}) as url:
        #     with open(path, 'wb') as f:
        #         f.write(url.read())
        # add img
        maintype, subtype = mimetypes.guess_type(str(path))[0].split('/', 1)
        msgRoot.get_payload()[1].add_related(  # image/png
            path.read_bytes(), maintype, subtype, cid="<{cid}>".format(cid=cids[i]))

    return msgRoot


def update_ids(offer):
    TODAYS_IDS.setdefault(offer["portal"], {})
    TODAYS_IDS[offer["portal"]] = {
        "id": offer["id"],
        "name": offer["name"],
        "brand": offer["brand"],
        "rating": offer["rating"],
        "rating_top": offer["rating_top"],
        "description": offer["description"],
        "image": offer["image"],
        "price_before": offer["price_before"],
        "price_after": offer["price_after"],
        "quantity_total": offer["quantity_total"],
        "quantity_sold": offer["quantity_sold"],
        "url": offer["url"],
        "currency": offer["currency"],
        'next_sale_at': offer["next_sale_at"].strftime("%m/%d/%Y, %H:%M:%S"),
        'current_sale_since': offer["current_sale_since"].strftime("%m/%d/%Y, %H:%M:%S"),
        'percent_available': offer['percent_available']
    }

def send_email(subject, body, sender, recipients, password):
    # # body['Subject'] = subject
    # # body['From'] = sender
    # # body['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
    # with smtplib.SMTP('smtp.gmail.com', 465, timeout=60) as smtp_server:
        # smtp_server.starttls(context=ssl.create_default_context())
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, recipients, body.as_string())
        # smtp_server.send_message(body)
    # # smtp = smtplib.SMTP()
    # # smtp.connect('smtp.gmail.com')
    # # smtp.login(sender, password)
    # # smtp.sendmail(sender, sender, body.as_string())
    # # smtp.quit()
    # s = smtplib.SMTP('smtp.gmail.com', 465) # 587)
    # s.ehlo()
    # s.login(sender, password)
    # s.sendmail(msgRoot['From'], recipients[0], msgRoot.as_string())
    # s.quit()
    print("Message sent!")

async def is_new(offer):
    old_data = TODAYS_IDS.get(offer["portal"])
    # brack weekly deals have same ids
    is_new = old_data and (old_data.get("id") != offer["id"] or old_data.get("name") != offer["name"])
    update_ids(offer)
    return is_new

async def scrap(website: str):
    async with ClientSession() as session:
        if website == "20min":
            tasks = [
                twenty_min(session)
            ]
        elif website == "brack":
            tasks = [
                brack(session),
                brack(session, type='it-multimedia'),
                brack(session, type='maison-habitat'),
                brack(session, type='supermarche-droguerie'),
                brack(session, type='famille-bebe'),
                brack(session, type='bricolage-hobby'),
                brack(session, type='sport-loisirs')
            ]
        elif website == "galaxus":
            tasks = [
                digitec(session)
            ]
        # tasks = [
        #     digitec(session),
        #     brack(session),
        #     brack(session, type='it-multimedia'),  # Wochenangebot ->it-multimedia, maison-habitat, supermarche-droguerie, famille-bebe, bricolage-hobby, sport-loisirs
        #     brack(session, type='maison-habitat'),
        #     brack(session, type='supermarche-droguerie'),
        #     brack(session, type='famille-bebe'),
        #     brack(session, type='bricolage-hobby'),
        #     brack(session, type='sport-loisirs'),
        #     twenty_min(session)
        #     # twenty_min(session, day=False),  # Wochenangebot
        # ]

        senders = []

        for result in as_completed(tasks):
            result = await result
            async for offer in result:
                # if offer is list
                if isinstance(offer, list):
                    for o in offer:
                        if await is_new(o):
                            senders.append(o)
                else:
                    if await is_new(offer):
                        senders.append(offer)
                # senders.append(prepare_and_send_to_telegram(session, offer))

        # [await result for result in as_completed(senders)]
        # print("senders ", senders)
        return senders

def build_url(product):
    return f'https://www.toppreise.ch/chercher?q={re.sub(" ", "+", product)}&cid='

async def toppreise_data(raw):
    html = BeautifulSoup(raw, "html.parser")
    # html.find_all(class_='bold col-12 col-xxl-auto my-2 my-md-0') -> gives only products with 1 price
    try:
        name = html.find_all(class_='col-12 f_item')[0].text.split("Évaluer le produit")[0].strip()
        description = html.find_all(class_='col-12 my-1 product-features')[0].text
        price = html.find_all(class_="Plugin_Price")[0].text.strip()
        url = 'https://www.toppreise.ch' + html.find_all(class_='col-12 f_item')[0].find('a').get('href')
    except IndexError:
        try:
            name = html.find_all(class_='bold col-12 col-xxl-auto my-2 my-md-0')[0].text.strip()
            description = html.find_all(class_='product-features')[0].text
            price = html.find_all(class_="Plugin_Price")[0].text.strip()
            url = 'https://www.toppreise.ch' + html.find_all(class_='bold col-12 col-xxl-auto my-2 my-md-0')[0].get('href')
        except IndexError:
            name = None
            description = None
            price = None
            url = None
    print(name, price)
    yield name, description, price, url

async def toppreise(session, url):
    print(url)
    async with session.get(url) as response:
        return toppreise_data(await response.text())

async def scrap_toppreise(data):
    senders = []
    async with ClientSession() as session:
        tasks = ['' for _ in range(4*len(data))]
        for i, d in enumerate(data):
            tasks[i*4] = toppreise(session, build_url(d['brand'] + " " + d['name'] + " " + d['description']))
            tasks[i*4+1] = toppreise(session, build_url(d['brand'] + " " + d['name']))
            tasks[i*4+2] = toppreise(session, build_url(d['name'] + " " + d['description']))
            tasks[i*4+3] = toppreise(session, build_url(d['brand'] + " " + d['description']))
        results = await asyncio.gather(*tasks)
        for result in results:
            async for offer in result:
                senders.append(offer)
        results = [[None, None, None, None] for _ in range(len(senders)//4)]
        for i in range(len(senders)//4):
            result = [None, None, None, None]
            for j in range(i*4, i*4+4):
                # take only first correct
                if senders[j][0] is not None:
                    if results[i] == [None, None, None, None]:
                        results[i] = [senders[j][i] for i in range(len(senders[j]))]
                    else:
                        if np.allclose(data[j//4]['price_before'], float(re.sub("'", "", results[i][2])), atol=0.4):
                            continue
                        else:
                            results[i] = [senders[j][i] for i in range(len(senders[j]))]
                # result[j-i*4] = senders[j]
            # results[i] = [senders[j] for j in range(i*4, i*4+4) if senders[j][0] is not None]

        return results


def main(website: str):

    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    data = run(scrap(website))
    data_complete = run(scrap_toppreise(data))
    for i in range(len(data_complete)):
        data[i]['toppreise'] = data_complete[i]
    if len(data)==0: return

    msgRoot = EmailMessage()
    sender = EMAIL_SENDER
    recipients = EMAIL_RECIPIENTS
    password = EMAIL_PASSWORD

    # msgRoot = MIMEMultipart('alternative') # related
    msgRoot['From'] = sender
    msgRoot['Subject'] = "Deals"
    msgRoot['To'] = recipients
    # msgRoot.preamble = 'This is a multi-part message in MIME format.'

    msgRoot = create_htm_from_deals(data, msgRoot)

    # save to disk a local copy of the message
    # Path('outgoing.msg').write_bytes(bytes(msgRoot))

    send_email("", msgRoot, sender, recipients, password)

    path.write_text(json.dumps(TODAYS_IDS, ensure_ascii=False, indent=4, sort_keys=True))

if __name__ == "__main__":
    # main('galaxus')
    # main('20min')
    main('brack')
