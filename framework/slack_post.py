import time
import logging
import warnings
from slackclient import SlackClient


logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(filename)s] [%(threadName)-5s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S',
                    )
logging.getLogger("requests").setLevel(logging.WARNING)

class SlackPost():

    def __init__(self,monitor_settings,product_access,atc_button_gen):
        self.product_access = product_access
        self.monitor_settings = monitor_settings
        self.message_settings = self.monitor_settings['slackSettings']
        self.message_field_dic = {'productPrice':{"title": "Price:",'value': None,"short": True},'productStock':{"title": "Initial Stock:",'value': None,"short": True}}
        self.atc_button_gen = atc_button_gen
        slack_token = "" #insert slack api token here
        self.sc = SlackClient(slack_token)

    def post_product(self,product):
        ## determine wether to post new message or update old message to mark product as out of stock
        message = self.format_message(product)
        if product['inStock'] == True:
            message[0]['fields'][-1]['value'] = ":white_check_mark:In Stock"
            ts = self.post_message(message)
            self.product_access.log_product_post(product[self.monitor_settings['defaultIdentifier']],ts)

        else:
            try:
                timestamp = self.product_access.retrive_product(product[self.monitor_settings['defaultIdentifier']])['postLog'][-1]
                message[0]['fields'][-1]['value'] = ":octagonal_sign:Sold Out\n in `"+str(round(float(time.time())-float(timestamp),2))+" sec`"
                self.update_message(message,timestamp)
            except Exception:
                logging.info("In Stock Message Not Available to Correct")

    def format_message(self,product):
        ## format a slack message for the passed in product
        base_message = [
                {
                    "thumb_url": product['productImage'],
                    "color": self.message_settings['color'],
                    "short": 'true',
                    "title": product['productTitle'],
                    "title_link": product['productUrl'],
                    "fields": [],
                    "author_name": self.message_settings['displayName'],
                    "author_icon": self.message_settings['icon'],
                    "footer": "funko dojo.",
                    "footer_icon": "https://i.imgur.com/11NqQxN.png",
                    "actions": []
                }
        ]
        for i in list(product.keys()):
            if i in list(self.message_field_dic.keys()):
                field = self.message_field_dic[i]
                field['value'] = product[i]
                base_message[0]['fields'].append(field)
        base_message[0]['fields'].append({"title": "Status:",'value': None,"short": True})
        if self.atc_button_gen: base_message[0]['actions'].append(self.atc_button_gen(product['productId'])) ## if atc button specified in module, add to message
        return base_message

    def update_message(self,message,timestamp):
        response = self.sc.api_call(
          "chat.update",
          channel= self.message_settings['channelId'],
          ts= timestamp,
          attachments = message
        )
        try:
            return response['ts']
        except Exception:
            print(response) ## if error, print response

    def post_message(self,message,):
        response = self.sc.api_call(
          "chat.postMessage",
          channel= self.message_settings['channelId'],
          attachments = message
        )
        try:
            return response['ts']
        except Exception:
            print(response) ## if error, print response
