import os

def get_readme():
    parent = os.path.dirname(os.path.dirname(__file__))
    with open(os.path.join(parent, 'README.md')) as f:
        content = f.read()
    return content
