# import
import random
import numpy as np
import pandas as pd
import requests
from elasticsearch import Elasticsearch
import unidecode

URL_DOC2VEC = 'http://profx-doc2vec.nomad.eastus2.dev.jet.network/'
URL_IMG2VEC = "http://profx-iu-im2vec.nomad.eastus2.dev.jet.network/"
FRACTION = .1

es = Elasticsearch('10.135.4.4:9200') # 6.1

# embedding related
def get_text_vector(text):
    """
    get text vector for the text entered
    """
    text = unidecode.unidecode(text)
    if text is None or len(text) < 1:
        return None
    data = {
        'words': [
            text
        ]
    }
    try: # to be defensive
        vector = requests.post(URL_DOC2VEC, json=data).json()[text]
        return [round(xx, 4) for xx in vector]
    except:
        return None

def get_image_vector(image_url):
    """
    get CNN descriptor (a vector) from image url
    """
    response = requests.post(
        url=URL_IMG2VEC,
        json={
            "image_urls": [
                image_url
            ]
        }
    )
    try:
        fl = response.json()['message']['image_urls_fetch_failed'].__len__()
    except:
        return None

    if fl > 0:
        return None
    else:
        try:
            vector = response.json()['data']['prelogits'][0]
            return  [round(xx, 4) for xx in vector]
        except:
            return None          

# hashing methods
def sign(x):
    if x > 0:
        return '+'
    elif x < 0:
        return '-'
    else:
        return '0'


def tokenize(vector):
    if vector is None:
        return vector
    n = int(len(vector) *FRACTION)
    tokens = []
    for i in np.argpartition(np.abs(vector), -n)[-n:]:
        tokens.append('{pos}{sign}'.format(pos=i, sign=sign(vector[i])))
    return tokens 


def get_sku_info(id, idx='retail_skus'):
    """
    return the sku info from complete retail skus 
    """
    try:
        source = Elasticsearch('10.116.1.16:9200').get(idx, id)['_source']
    except:
        return None
    return {
                'id': source['id'],
                'title': source.get('title', None),
                'brand': source.get('brand', None),
                'group_id': source.get("group_id", None),
                'image_url': source.get('main_image', None).get('x500', None),
                'product_type': source.get('product', None),
                'L0': source.get('category_level_0', None)
            }

def get_random_id(idx='lstm_training_data'):
    """
    get a random id from the current index
    """
    body = {
                "size": 1,
                "_source": [
                    "id"
                ],
                "query": {
                    "function_score": {
                    "functions": [
                        {
                        "random_score": {}
                        }
                    ]
                    }
                }
            }
    try:
        hits = es.search(idx, body=body)
    except:
        return None
    return hits['hits']['hits'][0]['_source']['id']

# main utility function
def knn_for_product_type(id, idx='lstm_training_data', weight = {'title': 0, 'image': 1, 'brand': 0}, es_size=1000, k=24, same_l0=True): 
    """
    find knn based on title and image vectors
    """

    if  weight['title'] < 0 or weight['image'] <0 or weight['brand'] < 0 or \
        weight['title'] + weight['image'] + weight['brand'] != 1:
            raise ValueError("weight must be non-negative and sum to 1.")

    sku_info = get_sku_info(id, idx='retail_skus')

    if sku_info is None:
        return None, []

    # find embeddings 
    if weight['title'] > 0:
        anchor_sku_title_vector = get_text_vector(sku_info['title'])
        title_tokens = tokenize(anchor_sku_title_vector)
        t_len = len(title_tokens)
    else:
        anchor_sku_title_vector = None

    if weight['image'] > 0:
        anchor_sku_image_vector = get_image_vector(sku_info['image_url'])
        image_tokens = tokenize(anchor_sku_image_vector)
        i_len = len(image_tokens)
    else:
        anchor_sku_image_vector = None
    
    all_fun = []     # boost filtered subset
    all_dist = []    # rescore 
    all_filter = []  # filter

    all_filter += [{"term": {"category_level_0": sku_info['L0']}}] if same_l0 else []
    # title length and image length
    
    # title
    if weight['title'] > 0 and anchor_sku_title_vector is not None: 
        # source_title_vector = [float(x) for x in source['title_vector'].split()]
        all_dist += \
            [{
            "script_score": {
                "script": {
                    "source": "euclidean_distance",
                    "lang": "profx-scripts",
                    "params": {
                        "field": "title_vector",
                        "values": anchor_sku_title_vector
                    }
                }
            },
            "weight": -weight['title']
            }]
        # title tokens
        all_fun += [{'filter':{'term': {'title_tokens': xx}}, 'weight': weight['title']/t_len} for xx in title_tokens]

    # image
    if weight['image'] > 0 and anchor_sku_image_vector is not None: 
        # source_image_vector = [float(x) for x in source['image_vector'].split()]
        all_dist += \
        [{
          "script_score": {
            "script": {
                "source": "euclidean_distance",
                "lang": "profx-scripts",
                "params": {
                        "field": "image_vector",
                        "values": anchor_sku_image_vector
                }
            }
          },
          "weight": -weight['image']
        }]
        # image tokens
        all_fun += [{'filter':{'term': {'image_tokens': xx}}, 'weight': weight['image']/i_len} for xx in image_tokens]
    
    # brand
    if weight['brand'] > 0 and sku_info['brand'] is not None: 
        all_fun += [{'filter': {'term':{'brand': sku_info['brand']}}, 'weight': weight['brand']}]
        all_dist += \
            [{
                "filter":{
                    "bool": {
                        "must_not": {
                            "term": {"brand": sku_info['brand']}
                        }
                    }
                },
                "weight": -weight['brand']
            }]

    # query
    body = \
    {
        "size": 100,
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "must": all_filter
                    }
                },
                "functions": all_fun,
                "score_mode": "sum"
            }
        }, 
        "rescore": {
            "window_size": es_size,
            "query": {
                "rescore_query": {
                    "function_score": {
                        "query": {
                            "match_all": {}
                        },
                        "functions": all_dist,
                        "score_mode": "sum",
                        "boost_mode": "replace"
                    }
                },
                "query_weight": 0,
                "rescore_query_weight": 1
            }
        }
    }

    # fetch data
    try:    
        hits = es.search(idx, body=body)
    except:
        return sku_info, []

    # import json
    # with open('example.txt', 'w') as outfile:
    #     json.dump(body, outfile)

    # post-precess rslt
    rslt = []
    for hit in hits['hits']['hits']:
        rslt+=[{
                'id': hit['_source']['id'],
                'title': hit['_source']['title'],
                'brand': hit['_source']['brand'],
                'group_id': hit['_source']['group_id'],
                'image_url': hit['_source']['image_url'],
                'dist': -hit['_score'],
                'product_type': hit['_source']['product_type'],
                'L0': hit['_source']['category_level_0']
                }]

    return sku_info, sorted(rslt, key=lambda k: k['dist'])[0:k]

def knn_for_product_type_web(id, idx='lstm_training_data', weight = {'title': 0, 'image': 1, 'brand': 0}, es_size=1000, k=24, same_l0=True): 

    sku, hits = knn_for_product_type(id, idx=idx, weight =weight, es_size=es_size, k=k, same_l0=same_l0)

    if sku is not None:
        sku['product_type'] = ' | '.join(sku['product_type']) if sku['product_type'] is not None else None

    if hits == []:
        return sku, hits

    rslt = []
    for hit in hits:
        rslt+=[{
                'id': hit['id'],
                'title': hit['title'],
                'brand': hit['brand'],
                'group_id': hit['group_id'],
                'image_url': hit['image_url'],
                'dist': hit['dist'],
                'product_type': ' | '.join(hit['product_type']) if hit['product_type'] is not None else None
                }]

    return sku, rslt

def knn_for_product_type_image_url(image_url, idx='wmt_training_data', es_size=1000, k=24):

    anchor_sku_image_vector = get_image_vector(image_url)

    if anchor_sku_image_vector is None:
        return []

    image_tokens = tokenize(anchor_sku_image_vector)

    all_fun = []     # boost filtered subset
    all_dist = []    # rescore 

    all_dist += \
    [{
        "script_score": {
        "script": {
            "source": "euclidean_distance",
            "lang": "profx-scripts",
            "params": {
                    "field": "image_vector",
                    "values": anchor_sku_image_vector
            }
        }
        },
        "weight": -1
    }]
        
    # image tokens
    all_fun += [{'filter':{'term': {'image_tokens': xx}}, 'weight': 1} for xx in image_tokens]

    # query
    body = \
    {
        "size": k,
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        # "must": [{
                        #             "term": {"category_level_0": sku_info['L0']}
                        # }]
                    }
                },
                "functions": all_fun,
                "score_mode": "sum"
            }
        }, 
        "rescore": {
            "window_size": 1000,
            "query": {
                "rescore_query": {
                    "function_score": {
                        "query": {
                            "match_all": {}
                        },
                        "functions": all_dist,
                        "score_mode": "sum",
                        "boost_mode": "replace"
                    }
                },
                "query_weight": 0,
                "rescore_query_weight": 1
            }
        }
    }

    # fetch data
    try:    
        hits = es.search(idx, body=body)
    except:
        return []

    # import json
    # with open('example.txt', 'w') as outfile:
    #     json.dump(body, outfile)

    # post-precess rslt
    rslt = []
    for hit in hits['hits']['hits']:
        rslt+=[{
                'id': hit['_source']['id'],
                'title': hit['_source']['title'],
                'brand': hit['_source']['brand'],
                'group_id': hit['_source']['group_id'],
                'image_url': hit['_source']['image_url'],
                'dist': -hit['_score'],
                'product_type': hit['_source']['product_type'],
                'L0': hit['_source']['category_level_0']
                }]

    return sorted(rslt, key=lambda k: k['dist'])[0:k]


def knn_for_product_type_image_url_web(image_url, idx='wmt_training_data', es_size=1000, k=24): 

    hits = knn_for_product_type_image_url(image_url=image_url, idx=idx, es_size=1000, k=24)

    # sku, hits = knn_for_product_type(id, idx=idx, weight =weight, es_size=es_size, k=k, same_l0=same_l0)

    
    if hits == []:
        return None, hits

    sku = {'L0': None,
           'brand': None,
           'group_id': None,
           'id': None,
           'image_url': image_url,
           'product_type': None,
           'title': None}

    rslt = []
    for hit in hits:
        rslt+=[{
                'id': hit['id'],
                'title': hit['title'],
                'brand': hit['brand'],
                'group_id': hit['group_id'],
                'image_url': hit['image_url'],
                'dist': hit['dist'],
                'product_type': hit['product_type'] #' | '.join(hit['product_type']) if hit['product_type'] is not None else None
                }]

    return sku, rslt
    

# # e.g.
# image_url = "https://images.jet.com/md5/5b5dca3f763b6414c22325708fba0420.500"
# yy = knn_for_product_type_url(image_url=image_url)
# # xx, yy = knn_for_product_type_web(id = '7c29feb18f78417e95bff97a52a57feb', same_l0=False)
# xx, yy = knn_for_product_type_image_url_web(image_url = "https://images.jet.com/md5/5b5dca3f763b6414c22325708fba0420.500")