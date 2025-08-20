#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import app

if __name__ == '__main__':
    app.run(debug=True, port=5000)