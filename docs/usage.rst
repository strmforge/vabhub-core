Usage
=====

Starting the Application
------------------------

To start the VabHub Core application:

.. code-block:: bash

   python start.py

This will start the FastAPI server on the configured host and port.

API Endpoints
-------------

Once the server is running, you can access the API documentation at:

- Swagger UI: ``http://localhost:8000/docs``
- ReDoc: ``http://localhost:8000/redoc``

The API provides the following main endpoints:

- ``/api/media`` - Media management
- ``/api/tasks`` - Task scheduling
- ``/api/plugins`` - Plugin management
- ``/api/charts`` - Charts and analytics
- ``/api/cache`` - Cache management

Running Tests
-------------

To run the test suite:

.. code-block:: bash

   python -m pytest

For more verbose output:

.. code-block:: bash

   python -m pytest -v

Running Code Quality Checks
--------------------------

To check code formatting with black:

.. code-block:: bash

   python -m black --check core/ tests/

To run type checking with mypy:

.. code-block:: bash

   python -m mypy --config-file mypy.ini core/

To run linting with pylint:

.. code-block:: bash

   pylint core/

Building Documentation
----------------------

To build the documentation:

.. code-block:: bash

   sphinx-build -b html docs/ docs/_build/html

The built documentation will be available in the ``docs/_build/html`` directory.

Docker Deployment
-----------------

To build and run the application using Docker:

.. code-block:: bash

   docker build -t vabhub-core .
   docker run --env-file .env -p 8081:8081 vabhub-core

For development with live reloading:

.. code-block:: bash

   docker run --env-file .env -p 8081:8081 -v $(pwd):/app vabhub-core