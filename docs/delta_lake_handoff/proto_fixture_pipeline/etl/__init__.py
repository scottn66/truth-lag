"""TruthLag lake prototype: Bronze and Silver Delta tables written with delta-rs.

The rules stay in the old pandas pipeline (ec-hw2/config.py and ec-hw2/ingest/*.py).
This package only moves the data through Delta tables and calls the old functions.

Environment variables
    TRUTHLAG_HW2_DIR    the ec-hw2 folder (holds config.py and ingest/)
    TRUTHLAG_LAKE_DIR   the lake root; tables live at <lake>/<layer>/<table>/
"""
