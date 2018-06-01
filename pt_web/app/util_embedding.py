# import
import random
import numpy as np
import pandas as pd
import requests
from elasticsearch import Elasticsearch
import unidecode

FRACTION = .1
URL_DOC2VEC = 'http://profx-doc2vec.nomad.eastus2.dev.jet.network/'
URL_IMG2VEC = "http://profx-iu-im2vec.nomad.eastus2.dev.jet.network/"



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
        





