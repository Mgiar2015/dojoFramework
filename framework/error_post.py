import time
import logging
import warnings
from pymongo import MongoClient
from slackclient import SlackClient

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(filename)s] [%(threadName)-5s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S',
                    )
logging.getLogger("requests").setLevel(logging.WARNING)

class ErrorPost():

    def __init__(self,monitor_settings,store_access):
        self.store_access = store_access
        self.monitor_settings = monitor_settings
        self.channel_id = "" #insert channel id to feed errors into
        slack_token = "" #insert slack api key here 
        self.sc = SlackClient(slack_token)

    def log_error(self,error_string,product_identifier = "None",send_message = True):
        product_identifier = str(product_identifier)
        if send_message:
            self.send_message(error_string,product_identifier)
        logging.info("Error Successfully Logged")

    def send_message(self,error_string,product_identifier):
        dropnotif =  [
                {
                    "color": "#000000",
                    "title": "Error: "+self.monitor_settings['monitorId']+" Product ID: "+ str(product_identifier),
                    "text":"`"+error_string+"`",
                    "author_name": "Funko Dojo",
                }
        ]
        response = self.sc.api_call(
          "chat.postMessage",
          channel= self.channel_id,
          attachments = dropnotif
        )
        try:
            return response['ts']
        except Exception:
            print(response)
