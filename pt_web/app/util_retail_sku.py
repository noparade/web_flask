# import
import random
import numpy as np
import pandas as pd
import requests
from elasticsearch import Elasticsearch
import unidecode

FRACTION = .1

# production snapshot for retail sku data
# es = Elasticsearch('10.116.1.16:9200') 
es = Elasticsearch('10.135.4.4:9200') # 6.1 (production)

def get_sku_info(id, idx='retail_skus'):
    """
    return the sku info from complete retail skus 
    """
    source = es.get(index=idx, id=id)['_source']
    return [{
                'id': source['id'],
                'title': source.get('title', None),
                'brand': source.get('brand', None),
                'group_id': source.get("group_id", None),
                'image_url': source.get('main_image', None).get('x500', None),
                'product_type': source.get('product', None)
            }]










