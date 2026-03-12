# Are We There Yet? :car:
Sequential hypothesis testing without peeking bias.



## Working Locally (After Setup - See Below)

### 1. Virtual Environment

```bash
# Activate the virtual environment
source .venv/bin/activate
```

### 2. Run the Dashboard

```bash
streamlit run app.py
```


### Setup

### 1. Create and Activate Virtual Environment

```bash
# Create virtual environment (using Python 3.10)
python3.10 -m venv .venv
```


### 2. Install Dependencies

```bash
pip install -r requirements.txt
```


## Testing

Tests live in the `tests/` directory and use [pytest](https://docs.pytest.org/).

### Install pytest (one-time)

```bash
source .venv/bin/activate
pip install pytest
```
Test by doing `which pytest`. If not in the correct locaiton
do `source .venv/bin/activate` again.

### Run all tests

```bash
pytest tests/ -v
```