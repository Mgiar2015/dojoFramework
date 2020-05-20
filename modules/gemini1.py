import os
import sys
import time
import json
import logging
import cfscrape
import requests
from bs4 import BeautifulSoup

if str(os.path.dirname(os.path.abspath(__file__))).count("/") > str(os.path.dirname(os.path.abspath(__file__))).count("\\"):
    splitChar = "/"
else:
    splitChar = "\\"
folder_dir = str(os.path.dirname(os.path.abspath(__file__))).split(str(os.path.dirname(os.path.abspath(__file__))).split(splitChar)[-1])[0][:-1]
sys.path.append(folder_dir+splitChar+"framework")
from logic import Logic

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(threadName)-5s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S',
                    )
logging.getLogger("requests").setLevel(logging.WARNING)

class gemini1():
    def __init__(self):
        self.monitor_id = "gemini1"
        self.parse_add_function = None
        self.atc_button_gen = None

    def parse_function(self,instance):
        page_num = 1
        cat_products,num_pages = self.parsePage(page_num)
        while page_num != num_pages:
            page_num += 1
            products,num_pages = self.parsePage(page_num)
            cat_products.extend(y for y in products if y not in cat_products)
        logging.info("Category Size: "+str(len(cat_products)))
        return cat_products

    def parsePage(self,page_num):
        products = []
        request_url = 'https://www.geminicollectibles.net/2020-wondercon/?page=' +str(page_num)
        while True:
            try:
                r = cfscrape.create_scraper().get(request_url)
                if r.status_code != 200:
                    if r.status_code == 403:
                        logging.info("403 Encountered")
                        return [],1
                    logging.info("Status Code: "+str(r.status_code))
                    raise Exception
            except Exception as e:
                logging.info("Error Loading Page, Retrying...")
                self.s = cfscrape.create_scraper()
                continue
            break
        soup = BeautifulSoup(r.content, "html.parser")
        try:
            num_pages = int(soup.find("ul",{'class':'PagingList'}).find_all('li')[-1].text)
        except Exception:
            num_pages = 1
        product_forms = soup.find('ul',{'class':'ProductList'}).find_all('li')
        for product_form in product_forms:
            product_url = product_form.find('a')['href']
            product_title = product_form.find('img')['alt']
            product_image = product_form.find("img")['src']
            product_id =product_form.find("img")['src'].split("products/")[1].split('/')[0]
            if product_form.find("em") == None:
                product_price = product_form.find('em',{'class':'p-price'}).text
            else:
                product_price = product_form.find('em').text
            stock_identifier = product_form.find('a',{'title':'Out of stock'})
            if stock_identifier == None:
                in_stock = True
            else:
                in_stock = False
            product = {'productUrl':product_url,'productTitle':product_title,'productImage':product_image,'productPrice':product_price,'productId':product_id,"inStock":in_stock}
            products.append(product)
        return products,num_pages


Logic(gemini1()).npe_monitor()
