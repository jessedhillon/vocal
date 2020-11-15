from setuptools import setup, find_packages


with open('./VERSION', 'r') as f:
    version = f.read().strip()

setup(name='vocal',
      version=version,
      description="Self-hosted content publishing and membership management engine.",
      author="Jesse Dhillon",
      author_email="jesse@dhillon.com",
      url="https://vocal.social/",
      test_suite='tests',
      install_requires=[
          'aiohttp[speedups]==3.7.2',
          'aiopg==1.0.0',
          'alembic==1.4.3',
          'click==7.1.2',
          'colorlog==4.6.2',
          'jinja2==2.11.2',
          'PyYAML==5.3.1'
      ],
      entry_points={
          'console_scripts': [
              'vocal=vocal.cli:main'
          ]
      })
