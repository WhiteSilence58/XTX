from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3, requests, time, json, threading, logging
from datetime import datetime, timezone
from contextlib import contextmanager
import os
import secrets, hashlib
import random
import string as _string
import imaplib
import smtplib
import email as email_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
import base64
import csv, io
import re as _re

from generator import SerialGenerator, estimate_total

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("logicheck")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["*"])

BASE_DIR = os.path.dirname(__file__)
MODULE_DIR = os.path.join(BASE_DIR, "modules")

for _module_name in [
    "auth.py",
    "core.py",
    "serials.py",
    "registration.py",
    "mail.py",
    "management.py",
    "inbox.py",
    "manual_invoice.py",
]:
    _path = os.path.join(MODULE_DIR, _module_name)
    with open(_path, "r", encoding="utf-8") as _f:
        exec(compile(_f.read(), _path, "exec"), globals())

app.mount("/", StaticFiles(directory="/frontend", html=True), name="frontend")
