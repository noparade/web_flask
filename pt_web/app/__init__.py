import numpy as np
from flask import Flask, Markup, request, render_template
from flask_appconfig import AppConfig
from markdown import markdown
from .utils import get_readme
# from .search import text_search, image_search, cb_sku_recommend
from .util_pt import knn_for_product_type_web, knn_for_product_type_image_url_web



def create_app(configfile='config.py'):
    app = Flask(__name__)

    AppConfig(app, configfile)

    @app.route('/', methods=['GET', 'POST'])
    def jet():
        if request.method == 'POST':
            term = (request.form['term']).strip()
            iw = request.form['iw']
            same_l0 = request.form['kind']
            weight = {'title': 1-np.float(iw), 'image': np.float(iw), 'brand': 0}
            if same_l0 == 'same':
                sku, hits = knn_for_product_type_web(id = term , weight=weight, same_l0=True)
            else:
                sku, hits = knn_for_product_type_web(id = term , weight=weight, same_l0=False)
            if sku is None:
                return render_template(
                     'index.html', term=term, iw=iw, kind=same_l0, no_sku = '1')
            else: 
                if hits == []:
                    return render_template(
                            'index.html', term=term, iw=iw, sku=sku, kind=same_l0, no_hits = '1')
                else:
                    return render_template(
                            'index.html', term=term, iw=iw, sku=sku, hits=hits, kind=same_l0)
        else:
            return render_template('index.html', kind='same')    
    
    @app.route('/walmart', methods=['GET', 'POST'])
    def walmart():
        if request.method == 'POST':
            image_url = (request.form['image_url']).strip()
            sku, hits = knn_for_product_type_image_url_web(image_url=image_url)

            if hits == []:
                return render_template(
                        'walmart.html', image_url=image_url, sku=sku, no_hits = '1')
            else:
                return render_template(
                        'walmart.html', image_url=image_url, sku=sku, hits=hits)
        else:
            return render_template('walmart.html')    

    @app.route('/documentation')
    def doc():
        md = markdown(get_readme())
        content = Markup(md)
        return render_template('documentation.html', content=content)

    return app



    # def index():
    #     if request.method == 'POST':
    #         term = request.form['term']
    #         if term.startswith('http'):
    #             hits = image_search(term)
    #             return render_template(
    #                 'index.html', term=term, img=term, hits=hits)
    #         elif (len(term) == 32) and (' ' not in term):
    #             skus, hits = cb_sku_recommend(term)
    #             sku = skus[0]
    #             return render_template(
    #                 'index.html', term=term, sku=sku, hits=hits)
    #         else:
    #             hits = text_search(term)
    #             return render_template('index.html', term=term, hits=hits)
    #         return render_template('index.html', term=term)
    #     else:
    #         return render_template('index.html')