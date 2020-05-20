import os
import sys
import time
import logging
import warnings
import datetime
import requests
import traceback
import threading

from database import ProductAccess, StoreAccess
from slack_post import SlackPost
from error_post import ErrorPost

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(filename)s] [%(threadName)-5s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S',
                    )
logging.getLogger("requests").setLevel(logging.WARNING)

class Logic():

    def __init__(self,monitor_class):
        ## initiate Logic class, create instances of supporting classes
        self.monitor_id = monitor_class.monitor_id
        self.store_access = StoreAccess(self.monitor_id)
        self.product_access = ProductAccess(self.monitor_id)
        self.monitor_settings = self.update_store_settings() 
        self.slack_post = SlackPost(self.monitor_settings,self.product_access,monitor_class.atc_button_gen)
        self.error_post = ErrorPost(self.monitor_settings,self.store_access)
        self.parse_add_function = monitor_class.parse_add_function
        self.parse_function = monitor_class.parse_function

    def update_store_settings(self):
        ## update monitor settings for specific monitor module
        monitor_settings = self.store_access.retrive_store_settings()
        if monitor_settings['proxiesEnabled']:
            if monitor_settings['proxySettings']['resiEnabled']:
                proxy_list = "proxies2.txt"
            else:
                proxy_list = "proxies1.txt"
            self.proxy_list = self.retrive_proxy_list(proxy_list)
            self.proxy = self.proxy_list[0]
            self.rotate_on_parse = monitor_settings['proxySettings']['rotateOnParse']
        else:
            self.proxy_list = None
            self.rotate_on_parse = False
            self.proxy = None
        self.delay_in = monitor_settings['delay']['in']
        self.delay_out = monitor_settings['delay']['out']
        self.default_identifier = monitor_settings['defaultIdentifier']
        self.sf_enabled = monitor_settings['sfEnabled']
        self.enabled = monitor_settings['enabled']
        if self.enabled == False:
            logging.info("Monitor Disabled, quitting thread...")
            sys.exit()
        return monitor_settings

    def retrive_proxy_list(self,proxy_list):
        ## retrive proxt list
        if str(os.path.dirname(os.path.abspath(__file__))).count("/") > str(os.path.dirname(os.path.abspath(__file__))).count("\\"):
            split_char = "/"
        else:
            split_char = "\\"
        folder_dir = str(os.path.dirname(os.path.abspath(__file__)))+split_char+"proxies"
        raw_proxies = [i.replace('\n','') for i in list(open(folder_dir+split_char+proxy_list).readlines())]
        proxies = []
        for i in raw_proxies:
            parts = i.split(':')
            proxy = "http://" + parts[2]+':'+parts[3]+'@'+parts[0]+':'+parts[1]
            proxies.append(proxy)
        return proxies

    def rotate_proxy(self):
        ## change the proxy that is set to the self.proxy variable
        if self.proxy == self.proxy_list[-1]:
            self.proxy = self.proxy_list[0]
        else:
            self.proxy = self.proxy_list[self.proxy_list.index(self.proxy)+1]

    def smart_post_filter(self,product_identifier):
        ### check wether a post for this same product has been made in the last 60 seconds, if it has, do not post the product 
        out_of_stock_time = 60
        product = self.product_access.retrive_product(product_identifier)
        if False not in [i['inStock'] for i in product['stockLog']]:
            post_message = True
        if product['stockLog'][-1]['inStock'] == False:
            ts = time.time()
            if (int(ts) -product['stockLog'][-1]['time']) > out_of_stock_time:
                post_message = True
            else:
                post_message = False
        else:
            post_message = True
        if product['enabled'] == False:
            post_message = False
        return post_message

    def single_product_endpoint(self,product_identifier):
        ## monitor a single product endpoint
        logging.info("Initiated Single Product Id Logic")
        while True:
            product = self.parse_function(product_identifier,self)
            while product['inStock']:
                self.update_store_settings()
                product = self.parse_function(product_identifier,self)
                time.sleep(self.delayIn)
                if self.rotate_on_parse: self.rotate_proxy()
                logging.info("[In Stock]Checking Product...")

            if len(self.product_access.retrive_product(product_identifier)['postLog']) > 0:
                product_log =  self.product_access.retrive_product(product_identifier)['postLog'][-1] # double check that this should not be postLog
                current_time = time.time()
                self.slack_post.post_product(product)

            self.product_access.log_product_status(product_identifier,product['inStock'])

            while product['inStock'] == False:
                self.update_store_settings()
                product = self.parse_function(product_identifier,self)
                time.sleep(self.delayOut)
                if self.rotate_on_parse: self.rotate_proxy()
                logging.info("[Out of Stock]Checking Product...")
            if self.sf_enabled:
                post_message = self.smart_post_filter(product_identifier)
            else:
                post_message = True
            if post_message:
                if self.parse_add_function:
                    add_info = self.parse_add_function(product[self.default_identifier],self)
                    product = {**product,**add_info}
                self.slack_post.post_product(product)
            else:
                self.error_post.log_error("Product Message Not Posted, Detected by Smart Filter",product_identifier)
            self.product_access.log_product_status(product_identifier,product['inStock'])

    def w_single_product_endpoint(self,product_identifier):
        ## wrapper function for single product endpoint
        while True:
            try:
                self.single_product_endpoint(product_identifier,)
            except Exception as e:
                self.error_post.log_error(str(traceback.format_exc()),product_identifier)

    def spe_monitor(self):
        ## initiate spe monitor for each product specified in product database
        c = 0
        product_list = self.product_access.retrive_products()
        print(product_list)
        product_list = [i for i in product_list if i['manuallyAdded'] == True]
        for product in product_list:
            c+= 1
            t = threading.Thread(name=(self.monitor_id+" #"+str(c)),target= self.w_single_product_endpoint, args=(product[self.default_identifier],))
            t.start()
        t.join()

    def new_product_endpoint(self):
        ## monitor a page for new products to pop up
        logging.info("Initiated New Page Logic")
        init_products = self.parse_function(self)
        self.product_access.import_new_products(init_products)
        while True:
            updated_products = []
            while len(updated_products) == 0:
                self.update_store_settings()
                logging.info("Monitoring Site for Changes")
                if self.rotate_on_parse: self.rotate_proxy()
                products = self.parse_function(self)
                changed_products = [i for i in products if i[self.default_identifier] not in [a[self.default_identifier] for a in init_products] or i['inStock'] != next(item for item in init_products if item[self.default_identifier] == i[self.default_identifier])['inStock'] ]
                removed_products = [{**i,"inStock":False} for i in init_products if i[self.default_identifier] not in [a[self.default_identifier] for a in products]]
                updated_products = changed_products + removed_products
                time.sleep(self.delay_out)
            logging.info('Product Change Detecteds')
            self.product_access.import_new_products(updated_products)
            for updated_product in updated_products:
                if self.sf_enabled:
                    post_message = self.smart_post_filter(updated_product[self.default_identifier])
                else:
                    post_message = True
                if post_message:
                    if self.parse_add_function != None:
                        add_info = {}
                        add_info = self.parse_add_function(updated_product[self.default_identifier],self)
                        updated_product = {**updated_product,**add_info}
                    self.slack_post.post_product(updated_product)
                else:
                    self.error_post.log_error("Product Message Not Posted, Detected by Smart Filter",updated_product[self.default_identifier])
                self.product_access.log_product_status(updated_product[self.default_identifier],updated_product['inStock'])
                logging.info("Product Posted")
            init_products = products

    def npe_monitor(self):
        ## wrapper function for new product endpoint
        while True:
            try:
                self.new_product_endpoint()
            except Exception as e:
                self.error_post.log_error(str(traceback.format_exc()))


    def multi_product_endpoint(self,product_identifiers):
        ## monitor multiple passed in product ids with a single endpoint
        logging.info("Initiated Multi Id Page Logic")
        init_products = self.parse_function(product_identifiers,self)
        self.product_access.import_new_products(init_products)
        while True:
            updated_products = []
            while len(updated_products) == 0:
                self.update_store_settings()
                logging.info("Monitoring Site fors Changes")
                if self.rotate_on_parse: self.rotate_proxy()
                products = self.parse_function(product_identifiers,self)
                changed_products = [i for i in products if i[self.default_identifier] not in [a[self.default_identifier] for a in init_products] or i['inStock'] != next(item for item in init_products if item[self.default_identifier] == i[self.default_identifier])['inStock'] ]
                removed_products = [{**i,"inStock":False} for i in init_products if i[self.default_identifier] not in [a[self.default_identifier] for a in products]]
                updated_products = changed_products + removed_products
                time.sleep(self.delay_out)
            logging.info('Product Change Detecteds')
            self.product_access.import_new_products(updated_products)
            for updated_product in updated_products:
                if self.sf_enabled:
                    post_message = self.smart_post_filter(updated_product[self.default_identifier])
                else:
                    post_message = True
                if post_message:
                    if self.parse_add_function:
                        add_info = {}
                        add_info = self.parse_add_function(updated_product[self.default_identifier],self)
                        updated_product = {**updated_product,**add_info}
                    self.slack_post.post_product(updated_product)
                else:
                    self.error_post.log_error("Product Message Not Posted, Detected by Smart Filter",updated_product[self.default_identifier])
                self.product_access.log_product_status(updated_product[self.default_identifier],updated_product['inStock'])
                logging.info("Product Posted")
            init_products = products

    def w_multi_product_endpoint(self,product_identifiers):
        ## wrapper function for multi product endpoint
        while True:
            try:
                self.multi_product_endpoint(product_identifiers,)
            except Exception as e:
                self.error_post.log_error(str(traceback.format_exc()))

    def mpe_monitor(self,max_page=10000000000):
        ## run needed amount of threads to accomidate for all products in database using the multi product endpoint monitor method
        product_list = self.product_access.retrive_products()
        product_identifiers = [i[self.default_identifier] for i in product_list if i['manuallyAdded'] == True]
        self.product_identifiers = product_identifiers
        n = max_page
        c = 0
        identifer_lists = [product_identifiers[i * n:(i + 1) * n] for i in range((len(product_identifiers) + n - 1) // n )] # split list of products into sublist of products based on the max_page value that was passed in
        for id_list in identifer_lists:
            c+= 1
            t = threading.Thread(name=(self.monitor_id+" #"+str(c)),target= self.w_multi_product_endpoint, args=(id_list,))
            t.start()
        t.join()
