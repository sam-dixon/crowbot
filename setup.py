from setuptools import setup

setup(name='crowbot',
      version='0.1',
      description='A Slack chatbot for observing',
      url='http://github.com/sam-dixon/crowbot',
      author='Sam Dixon',
      author_email='sam.dixon@berkeley.edu',
      license='MIT',
      packages=['crowbot'],
      install_requires=['slackclient',
                        'sqlalchemy',
                        'pyyaml',
                        'astropy',
                        'ephem',
                        'requests',
                        'twilio'],
      include_package_data=True)