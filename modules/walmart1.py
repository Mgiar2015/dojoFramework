import os
import sys
import time
import json
import logging
import requests
import random
import cfscrape
import traceback
import cfscrape
from bs4 import BeautifulSoup

if str(os.path.dirname(os.path.abspath(__file__))).count("/") > str(os.path.dirname(os.path.abspath(__file__))).count("\\"):
    splitChar = "/"
else:
    splitChar = "\\"
folder_dir = str(os.path.dirname(os.path.abspath(__file__))).split(str(os.path.dirname(os.path.abspath(__file__))).split(splitChar)[-1])[0][:-1]
print(folder_dir)
sys.path.append(folder_dir+splitChar+"framework")

from logic import Logic

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(threadName)-5s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S',
                    )
logging.getLogger("requests").setLevel(logging.WARNING)
class walmart1():

    def __init__(self):
        self.monitor_id = "walmart1"
        self.parse_add_function = self.retrive_stock

    def atc_button_gen(self,product_identifier):
        return {"type": "button","text": "Add to Cart :shopping_trolley:","url": 'http://affil.walmart.com/cart/addToCart?q=1&items='+str(product_identifier)}

    def retrive_stock(self,product_identifier,instance):
        product = {}
        request_url = "http://affil.walmart.com/cart/addToCart?items="+str(product_identifier)
        while True:
            try:
                r = requests.get(request_url)
                if r.status_code != 200:
                    logging.info("Error: Page could not be retrived, Retrying...")
                    raise Exception
            except Exception:
                continue
            break
        if r.url == "https://www.walmart.com/cart/":
            try:
                soup = BeautifulSoup(r.content)
                product_stock = str(soup.find_all('script')[17]).split('availableQuantity":')[1].split(',')[0]
            except Exception:
                product_stock = 'Unavailable'
        else:
            product_stock = 'Unavailable'
        product['productStock'] = product_stock
        return product

    def parse_function(self,product_id,instance):
        request_link = 'https://www.walmart.com/terra-firma/item/'+str(product_id)
        while True:
            try:
                r = requests.get(request_link, proxies= {"https":instance.proxy})
                if r.status_code != 200:
                    logging.info("Error: Page could not be retrived, Retrying...")
                    logging.info(r.content)
                    raise ValueError("Bad Status Code While Parsing Page: "+str(r.status_code))
                raw_json = json.loads(r.content)
                if 'sellers' not in list(raw_json['payload'].keys()):
                    time.sleep(5)
                    raise ValueError("Bad Data Retrived From Page. ")#raise ValueError("Bad Data Retrived From Page: "+str(raw_json))
            except Exception as e:
                logging.info(e)
                instance.rotate_proxy()
                continue
            break
        try:
            raw_product_content = raw_json['payload']['products'][raw_json['payload']['primaryProduct']]
        except Exception:
            logging.info("Product Unavailable")
            return  {"productUrl":None,"productTitle":None,"productImage":None,"productPrice":None,"inStock":False,"productId":None}
        product_title = raw_product_content['productAttributes']['productName']
        product_url = "https://www.walmart.com/product/"+str(product_id)
        try:
            product_img_url = list(raw_json['payload']['images'].values())[0]['assetSizeUrls']['IMAGE_SIZE_450']
        except Exception:
            product_img_url = "N/A"
        raw_availability_info = list(raw_json['payload']['offers'].values())
        seller_info = {seller['sellerId']:seller['sellerType'] for seller in list(raw_json['payload']['sellers'].values())}
        walmart_listings = [i for i in raw_availability_info if seller_info[i['sellerId']] == "INTERNAL"]
        walmart_in_stock = [i for i in walmart_listings if i['productAvailability']['availabilityStatus'] != "OUT_OF_STOCK"]
        if len(walmart_in_stock) != 0:
            try:
                product_price = walmart_in_stock[0]['pricesInfo']['priceMap']['CURRENT']['price']
            except Exception:
                product_price = "N/A"
            try:
                product_zip = str(walmart_in_stock[0]['fulfillment']['pickupOptions'][0]['storePostalCode'])
            except Exception:
                product_zip = "N/A"
            in_stock = True
        else:
            product_price = "N/A"
            product_zip = "N/A"
            in_stock = False
        product_info = {"productUrl":product_url,"productTitle":product_title,"productImage":product_img_url,"productPrice":product_price,"inStock":in_stock,"productId":product_id}
        return product_info

Logic(walmart1()).spe_monitor()
