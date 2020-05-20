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

    def atc_button_gen(self,productIdentifier):
        return {"type": "button","text": "Add to Cart :shopping_trolley:","url": 'http://affil.walmart.com/cart/addToCart?q=1&items='+str(productIdentifier)}

    def retrive_stock(self,productIdentifier,instance):
        product = {}
        requestUrl = "http://affil.walmart.com/cart/addToCart?items="+str(productIdentifier)
        while True:
            try:
                r = requests.get(requestUrl)
                if r.status_code != 200:
                    logging.info("Error: Page could not be retrived, Retrying...")
                    raise Exception
            except Exception:
                continue
            break
        if r.url == "https://www.walmart.com/cart/":
            try:
                soup = BeautifulSoup(r.content)
                productStock = str(soup.find_all('script')[17]).split('availableQuantity":')[1].split(',')[0]
            except Exception:
                productStock = 'Unavailable'
        else:
            productStock = 'Unavailable'
        product['productStock'] = productStock
        return product

    def parse_function(self,productId,instance):
        requestLink = 'https://www.walmart.com/terra-firma/item/'+str(productId)
        while True:
            try:
                r = requests.get(requestLink, proxies= {"https":instance.proxy})
                if r.status_code != 200:
                    logging.info("Error: Page could not be retrived, Retrying...")
                    logging.info(r.content)
                    raise ValueError("Bad Status Code While Parsing Page: "+str(r.status_code))
                rawJson = json.loads(r.content)
                if 'sellers' not in list(rawJson['payload'].keys()):
                    time.sleep(5)
                    raise ValueError("Bad Data Retrived From Page. ")#raise ValueError("Bad Data Retrived From Page: "+str(rawJson))
            except Exception as e:
                logging.info(e)
                instance.rotate_proxy()
                #instance.dojoError.log_error(str(traceback.format_exc()),productId,False)
                continue
            break
        try:
            rawProductContent = rawJson['payload']['products'][rawJson['payload']['primaryProduct']]
        except Exception:
            logging.info("Product Unavailable")
            return  {"productUrl":None,"productTitle":None,"productImage":None,"productPrice":None,"inStock":False,"productId":None}
        productTitle = rawProductContent['productAttributes']['productName']
        productUrl = "https://www.walmart.com/product/"+str(productId)
        try:
            productImgUrl = list(rawJson['payload']['images'].values())[0]['assetSizeUrls']['IMAGE_SIZE_450']
        except Exception:
            productImgUrl = "N/A"
        rawAvailabilityInfo = list(rawJson['payload']['offers'].values())
        sellerInfo = {seller['sellerId']:seller['sellerType'] for seller in list(rawJson['payload']['sellers'].values())}
        walmartListings = [i for i in rawAvailabilityInfo if sellerInfo[i['sellerId']] == "INTERNAL"]
        walmartInStock = [i for i in walmartListings if i['productAvailability']['availabilityStatus'] != "OUT_OF_STOCK"]
        if len(walmartInStock) != 0:
            try:
                productPrice = walmartInStock[0]['pricesInfo']['priceMap']['CURRENT']['price']
            except Exception:
                productPrice = "N/A"
            try:
                productZip = str(walmartInStock[0]['fulfillment']['pickupOptions'][0]['storePostalCode'])
            except Exception:
                productZip = "N/A"
            inStock = True
        else:
            productPrice = "N/A"
            productZip = "N/A"
            inStock = False
        productInfo = {"productUrl":productUrl,"productTitle":productTitle,"productImage":productImgUrl,"productPrice":productPrice,"inStock":inStock,"productId":productId}
        return productInfo

Logic(walmart1()).spe_monitor()
