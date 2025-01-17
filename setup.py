from setuptools import setup, find_packages

setup(
    name="veille_db",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "pytest",
        "requests",
        "pymongo",
        "pymysql",
        "python-dotenv",
        "httpx",
    ],
)
