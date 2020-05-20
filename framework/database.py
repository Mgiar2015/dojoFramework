import json
import time
import logging
import datetime
from pymongo import MongoClient


logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(filename)s] [%(threadName)-5s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S',
                    )
logging.getLogger("requests").setLevel(logging.WARNING)

class StoreAccess():

    def __init__(self,monitor_id):
        self.monitor_id = monitor_id
        self.cluster_string = "" #insert connection string here
        self.database_string = "status" #set the collection as a enviorment variable to last throughout the session
        self.collection_string = "monitors"
        self.database_connect(self.collection_string)

    def database_connect(self,collection_string):
        logging.info("MongoDB Connecting...")
        while True:
            try:
                client = MongoClient(self.cluster_string) #connect to the cluster client
                database = client[self.database_string]
                self.collection = database[collection_string]
            except Exception as e:
                logging.info(e)
                logging.info('Error connecting to MongoDB, retrying..')
                time.sleep(10)
                continue
            break
        logging.info("MongoDB Connection Established")

    def retrive_product_collections(self):
        store_docs = list(self.collection.find())
        product_collections = list(dict.fromkeys([i['productCollectionId'] for i in store_docs]))
        return product_collections

    def retrive_store_settings(self):
        return list(self.collection.find({"monitorId":self.monitor_id}))[0]

    def log_error(self,error_information,product_identifier = "None"):
        error_message = [{'error':"",'time':str(datetime.datetime.now()),"productIdentifier":product_identifier}]
        self.collection.update({"monitorId": self.monitor_id}, { '$push':{'errorLog': {'$each':error_message}}})

    def change_monitor_status(self,status):
        self.collection.updateOne({ "monitorId": self.monitor_id },{"$set": { "enabled": status}})

class ProductAccess():
    def __init__(self,monitor_id):
        self.monitor_id = monitor_id
        self.cluster_string = "" #insert connection string here
        self.database_string = "products" #set the collection as a enviorment variable to last throughout the session
        self.store_settings = StoreAccess(monitor_id).retrive_store_settings()
        self.collection_string = self.store_settings['productCollectionId']
        self.database_connect(self.collection_string)

    def database_connect(self,collection_string):
        logging.info("MongoDB Connecting...")
        while True:
            try:
                client = MongoClient(self.cluster_string) #connect to the cluster client
                database = client[self.database_string]
                self.collection = database[collection_string]
            except Exception:
                logging.info('Error connecting to MongoDB, retrying..')
                time.sleep(10)
                continue
            break
        logging.info("MongoDB Connection Established")

    def retrive_product(self,identifier_value):
        ## retrive all enabled products in the previously specificed collecttion ##
        product_list = list(self.collection.find({self.store_settings['defaultIdentifier']: identifier_value}))
        if len(product_list) == 0:
            product = None
        else:
            product = product_list[0]
        return product

    def retrive_products(self):
        ## retrive all enabled products in the previously specificed collecttion ##
        return list(self.collection.find({"enabled":True}))


    def import_new_products(self,products):
        for product in products:
            self.add_product(product)
        logging.info("All New Products Successfully Imported")

    def change_product_status(self,product,status):
        self.collection.updateOne({ self.store_settings['defaultIdentifier']: product[self.store_settings['defaultIdentifier']] },{"$set": { "enabled": status}})

    def add_product(self,product):
        product_temp = {"productTitle":None,"productPrice":None,"productUrl":None,"productId":None,"productImageUrl":None,"stockLog":[],"postLog":[],"enabled":True,"manuallyAdded":False}
        product_doc = {**product_temp,**product}
        in_stock = product_doc.pop('inStock', None)
        if in_stock != None:
            product_doc['stockLog'].append({'inStock':in_stock,'time':time.time()})
        if self.retrive_product(product[self.store_settings['defaultIdentifier']]) == None:
            self.collection.insert_one(product_doc)
            logging.info("Product Successfully Added to Database")
            success = True
        else:
            product_elements = {**product}
            del product_elements['inStock']
            self.collection.update({self.store_settings['defaultIdentifier']:product[self.store_settings['defaultIdentifier']]}, {"$set":product_elements})
            logging.info("Product Log Updated")
            success = False
        return success

    def log_product_details(self,identifier_value, product_details):
        for value_key in list(product_details.keys()):
            try:
                self.collection.update({self.store_settings['defaultIdentifier']: identifier_value},  {"$push": {"log": { value_key : product_details['valueKey'] }}})
            except Exception:
                logging.info("Error Updating Product Value")
        logging.info("Product Details Successfully Updated in Database")

    def log_product_status(self,identifier_value, status):
        ## log product event given its url ##
        product = self.retrive_product(identifier_value)
        if len(product['stockLog']) == 0 or product['stockLog'][-1]['inStock'] != status:
            update_message = [{'inStock':status,'time':time.time(),'monitorId':self.monitor_id}]
            self.collection.update({self.store_settings['defaultIdentifier']: identifier_value}, { '$push':{'stockLog': {'$each':update_message}}})
            logging.info("Restock Logged in MongoDB")
        else:
            logging.info("Product status has not changed since previous log")

    def log_product_post(self,identifier_value,post_ts):
        product = self.retrive_product(identifier_value)
        update_message = [post_ts]
        self.collection.update({self.store_settings['defaultIdentifier']: identifier_value}, { '$push':{'postLog': {'$each':update_message}}})
        logging.info("Post Logged in MongoDB")
