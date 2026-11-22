from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/client/login/<key>', methods=['POST', 'GET'])
@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def catch_all(key=None, path=None):
    return jsonify({
        "success": True,
        "message": "success",
        "keyType": "premium",
        "expiresIn": 999999999,
        "totalDays": 999,
        "remainingDays": 999
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
