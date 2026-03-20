from flask import Flask, request, jsonify, send_from_directory # Add send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='static') # Tell Flask where the files are
CORS(app)

@app.route("/")
def home():
    # This sends your index.html file to the user's browser
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/api/expense", methods=["POST"])
def add_expense():
    data = request.json
    print(data)
    return jsonify({"message": "received", "data": data})

if __name__ == "__main__":
    # Railway provides the PORT variable automatically
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
