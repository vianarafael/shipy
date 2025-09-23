import os, sys, datetime

DEBUG = os.getenv("SHIPY_DEBUG") == "1"

def log(*args):
    """Print only when SHIPY_DEBUG=1 is set"""
    if not DEBUG:
        return
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[shipy {ts}]", *args, file=sys.stderr, flush=True)
