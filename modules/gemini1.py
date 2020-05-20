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
        pageNum = 1
        catProducts,numPages = self.parsePage(pageNum)
        while pageNum != numPages:
            pageNum += 1
            products,numPages = self.parsePage(pageNum)
            catProducts.extend(y for y in products if y not in catProducts)
        logging.info("Category Size: "+str(len(catProducts)))
        return catProducts

    def parsePage(self,pageNum):
        products = []
        requestUrl = 'https://www.geminicollectibles.net/2020-wondercon/?page=' +str(pageNum)
        while True:
            try:
                r = cfscrape.create_scraper().get(requestUrl)
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
            numPages = int(soup.find("ul",{'class':'PagingList'}).find_all('li')[-1].text)
        except Exception:
            numPages = 1
        productForms = soup.find('ul',{'class':'ProductList'}).find_all('li')
        for product_form in productForms:
            productUrl = product_form.find('a')['href']
            productTitle = product_form.find('img')['alt']
            productImage = product_form.find("img")['src']
            productId =product_form.find("img")['src'].split("products/")[1].split('/')[0]
            if product_form.find("em") == None:
                productPrice = product_form.find('em',{'class':'p-price'}).text
            else:
                productPrice = product_form.find('em').text
            stockIdentifier = product_form.find('a',{'title':'Out of stock'})
            if stockIdentifier == None:
                inStock = True
            else:
                inStock = False
            product = {'productTitle':productTitle,'productUrl':productUrl,'productImage':productImage,'productPrice':productPrice,'productId':productId,"inStock":inStock}
            products.append(product)
        return products,numPages


Logic(gemini1()).npe_monitor()
