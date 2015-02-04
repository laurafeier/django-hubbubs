import os
from setuptools import setup, find_packages


README = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')


DEPENDENCIES = [
    'django>=1.4,<=1.7',
    'requests',
]

setup(
    name='django-hubbubs',
    version='0.1',
    description='PubSubHubbub subscriber app for Django projects.',
    long_description = open(README, 'r').read(),
    author='Laura Feier',
    author_email='feierlaura10@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=DEPENDENCIES,
    setup_requires=[],
    classifiers=[]
)
