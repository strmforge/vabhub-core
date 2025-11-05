Usage
=====

Starting the Application
------------------------

To start the VabHub Core application::

   python start.py

This will start the FastAPI server on the configured host and port.

API Endpoints
-------------

Once the server is running, you can access the API documentation at:

- Swagger UI: ``http://localhost:8000/docs``
- ReDoc: ``http://localhost:8000/redoc``

Running Tests
-------------

To run the test suite::

   python -m pytest

For more verbose output::

   python -m pytest -v

Running Code Quality Checks
--------------------------

To check code formatting with black::

   python -m black --check core/ tests/

To run type checking with mypy::

   python -m mypy --config-file mypy.ini core/

To run linting with pylint::

   pylint core/

Building Documentation
----------------------

To build the documentation::

   sphinx-build -b html docs/ docs/_build/html

The built documentation will be available in the ``docs/_build/html`` directory.