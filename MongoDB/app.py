from flask import Flask, request, jsonify
from pymongo import MongoClient
import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  

MONGO_URI = "mongodb+srv://StarlithMonitoring:Starlith136@monitoringesp32starlith.bmcwx.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["sensor_db"]
collection = db["sensor_data"]

@app.route('/sensor', methods=['POST'])
def receive_data():
    try:
        data = request.json
        
        data["timestamp"] = datetime.datetime.utcnow().isoformat()

        insert_result = collection.insert_one(data)

        data["_id"] = str(insert_result.inserted_id)

        return jsonify({"message": "Data berhasil disimpan ke MongoDB", "data": data}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sensor', methods=['GET'])
def get_data():
    try:
        data = list(collection.find({}, {
            "_id": 1, 
            "ldr": 1, 
            "temperature": 1, 
            "humidity": 1, 
            "motion": 1, 
            "distance": 1,  # **Tambahkan field distance**
            "timestamp": 1
        }))

        for item in data:
            item["_id"] = str(item["_id"])

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
