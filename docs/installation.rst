Installation
============

Requirements
------------

VabHub Core requires Python 3.8 or higher.

Installation Steps
------------------

1. Clone the repository::

   git clone https://github.com/strmforge/vabhub-Core.git
   cd vabhub-Core

2. Create a virtual environment::

   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install the required packages::

   pip install -r requirements.txt

4. For development, also install dev dependencies::

   pip install -r requirements-dev.txt

Configuration
-------------

Before running the application, you need to set up the configuration file. Copy the example file and modify it according to your needs::

   cp .env.example .env