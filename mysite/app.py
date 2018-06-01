import numpy as np
from flask import Flask, Markup, request, render_template
from markdown import markdown
import os
import json
from utils import get_readme
from flask import redirect, url_for
# from flask_appconfig import AppConfig




app = Flask(__name__)

# AppConfig(app, configfile)
def category_data(catalog):
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(parent,catalog,'label_summary_done.json')
    res = json.load(open(filepath))
    for x in res:
        x['label_copy'] = x['label'].replace(' ','_')
    return res

@app.route('/',methods=['POST','GET'])
def welcome():
    if request.method == 'POST':
        catalog=request.form['categoryselection']
        print(catalog)
        data = category_data(catalog)
        return redirect('category/'+catalog)
        # return render_template('index.html', data=data)
    else:
        return render_template('welcome.html')


@app.route('/category/<name>',methods=['POST','GET'])
def category(name):
    res = category_data(name)
    print(name)
    if request.method == 'POST':
        data_images = [x  for x in res if x['label_copy'] == str(request.form['submit'])]
        if len(data_images) > 0:
            return render_template('index.html',examples=data_images[0]['examples'],
                                   label=data_images[0]['label'],category=name)
        else:
            if name=='furniture':
                return render_template('index.html', data=res,category=name,kag=1)
            else:
                return render_template('index.html', data=res, category=name)

        # return render_template('index.html',data_label=res[['label','examples']].to_dict('record'))
    else:
        if name == 'furniture':
            return render_template('index.html',data=res,category=name,kag=1)
        else:
            return render_template('index.html', data=res, category=name)




@app.route('/documentation')
def doc():
    md = markdown(get_readme())
    content = Markup(md)
    return render_template('documentation.html', content=content)


# @app.route('/',methods=['POST','GET'])
# def index():
#     filepath = '/yg/analytics/iptc/src/model/furniture/label_summary_done.json'
#     # filepath = '/Users/jing.zhang/PycharmProjects/IPTC/src/model/furniture/label_summary_done.csv'
#     # res = pd.read_csv(filepath)
#     # res['label_copy'] = res['label'].apply(lambda x:x.replace(' ','_'))
#     res = json.load(open(filepath))
#     if request.method == 'POST':
#         # print(str(request.form['submit']))
#         data_images = res[res.label_copy == str(request.form['submit'])]
#         # print(data_images.shape)
#         image_urls = eval(data_images['examples'].iloc[0])
#         label = data_images.label.iloc[0]
#         print((label,len(image_urls)))
#         if data_images.shape[0] > 0:
#             image_urls = eval(data_images['examples'].iloc[0])
#             for image_url in image_urls:
#                 print(image_url)
#             return render_template('index.html',data_images=image_urls,label=label)
#         else:
#             return render_template('index.html',data=res.to_dict('record'))
#         # return render_template('index.html',data_label=res[['label','examples']].to_dict('record'))
#     else:
#         return render_template('index.html',data=res.to_dict('record'))

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(debug=True, host="10.4.0.5", port=3020)
