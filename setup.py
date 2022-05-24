from setuptools import setup, find_packages

VERSION = "0.2.0"
DESCRIPTION = "A simple dependency injector based on type hints"

with open("README.md", "r", encoding="utf-8") as readme:
    LONG_DESCRIPTION = readme.read()


setup(name="HinteDI",
      version=VERSION,
      author="Eetu Asikainen",
      author_email="eetu.asikainen1204@gmail.com",
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      packages=find_packages(),
      keywords=["dependency injection", "DI"],
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent"
      ],
      python_requires='>=3.10')
