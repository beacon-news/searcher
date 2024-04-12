
# cd src
# python ingester_main.py&
# uvicorn searcher_main:app --reload

# 'searcher' python package must be installed
uvicorn searcher.searcher_main:app
