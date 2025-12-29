from flask import Flask
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['GET', 'POST'])
def home():
    print("REQUEST RECEIVED", flush=True)
    return "OK"

if __name__ == '__main__':
    print("Starting Minimal App on 5003 (No Debug, No Threaded)...")
    app.run(port=5003, debug=False, threaded=False)
