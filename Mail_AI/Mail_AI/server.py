from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route('/main', methods=['POST'])
def run_mail_ai():
    try:
        subprocess.run(["python", "main.py"], check=True)
        return jsonify({"status": "success", "message": "Mail processing completed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5001)
