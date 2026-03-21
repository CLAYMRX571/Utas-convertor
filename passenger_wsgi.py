import sys
import os

BASE_DIR = "/home/claymrx1/e.utas.uz"
VENV_PATH = "/home/claymrx1/virtualenv/e.utas.uz/3.13"

sys.path.insert(0, VENV_PATH + "/lib/python3.13/site-packages")

os.environ["PATH"] = VENV_PATH + "/bin:" + os.environ["PATH"]
os.environ["VIRTUAL_ENV"] = VENV_PATH

sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from webhook import app as application