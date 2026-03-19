from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "Server running"

@app.route("/api/expense", methods=["POST"])
def add_expense():
    data = request.json
    print(data)
    return jsonify({"message": "received", "data": data})

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))