#!/bin/bash

python bot.py &
uvicorn server:app --host 0.0.0.0 --port $PORT