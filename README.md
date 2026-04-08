# Py-Bash

## Description

This library simplifies the use of Bash/Shell commands in Python.

## How to Run Unit Tests Locally

### Step 1: Setup your virtual environment

*If you already have a virtual environment configured, you can skip this step*

```
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip3 install -r requirements.txt --process-dependency-links
pip3 install pytest pytest-cov coverage2clover
```

### Step 2: Run unit tests

*Navigate to the root of this project*

```
pytest --cov-fail-under=100 --cov=py_bash --cov-report=term-missing --cov-report=html test
```
