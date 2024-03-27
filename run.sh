
cd src
python ingester_main.py&
uvicorn searcher_main:app --reload
