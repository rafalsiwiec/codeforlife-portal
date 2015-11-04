# -*- coding: utf-8 -*-
from setuptools import find_packages, setup
import versioneer

setup(name='codeforlife-portal',
      cmdclass=versioneer.get_cmdclass(),
      version=versioneer.get_version(),
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
          'django==1.7',
          'django-appconf==0.6',
          'django-casper==0.0.2',
          'django-countries==3.3',
          'djangorestframework==2.3.9',
          'unittest2==0.5.1',
          'pyyaml==3.11',
          'six==1.6.1',
          'docutils==0.11',
          'django-recaptcha-field==1.0b2',
          'django-jquery==1.9.1',
          'postcodes==0.1',
          'django-two-factor-auth==1.0.0-beta3',
          'selenium==2.42.1',
          'urllib3==1.9',
          'reportlab==3.1.44',
          'requests==2.7.0',
          'responses==0.3.0'
      ],
      )
