Installation
============

Requirements
------------

VabHub Core requires:

- Python 3.8 or higher
- A supported database (SQLite, PostgreSQL, MySQL)
- Redis for caching and task queues
- Git (for development)

Installation Steps
------------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/strmforge/vabhub-Core.git
      cd vabhub-Core

2. Create a virtual environment:

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install the required packages:

   .. code-block:: bash

      pip install -r requirements.txt

4. For development, also install dev dependencies:

   .. code-block:: bash

      pip install -r requirements-dev.txt

Configuration
-------------

Before running the application, you need to set up the configuration file. Copy the example file and modify it according to your needs:

.. code-block:: bash

   cp .env.example .env

Edit the ``.env`` file to configure your database, Redis, and other settings.

Database Setup
--------------

To initialize the database, run:

.. code-block:: bash

   python -m core.database.init

This will create the necessary tables and initial data.

Running Tests
-------------

To run the test suite:

.. code-block:: bash

   python -m pytest

For more verbose output:

.. code-block:: bash

   python -m pytest -v