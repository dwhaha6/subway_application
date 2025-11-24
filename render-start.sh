#!/bin/bash
cd subway_app
gunicorn --bind 0.0.0.0:$PORT app:app
