import os
import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("TIDB_HOST"),
        user=os.environ.get("TIDB_USER"),
        password=os.environ.get("TIDB_PASSWORD"),
        database=os.environ.get("TIDB_DATABASE", "test"),
        port=int(os.environ.get("TIDB_PORT", 4000)),
        ssl_verify_cert=True,
        ssl_ca=os.environ.get("TIDB_SSL_CA", "/etc/ssl/certs/ca-certificates.crt")
    )

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "Aishwarya Residency API"}), 200

@app.route('/api/flats', methods=['GET'])
def get_flats():
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM flats ORDER BY flat_number ASC")
        flats = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(flats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        query = """
        SELECT 
            id, 
            amount, 
            category, 
            payment_mode AS paymentMode, 
            DATE_FORMAT(payment_date, '%Y-%m-%d') AS date, 
            notes, 
            'income' AS type, 
            flat_id,
            (SELECT flat_number FROM flats WHERE flats.id = income_records.flat_id) AS flatNumber,
            (SELECT owner_name FROM flats WHERE flats.id = income_records.flat_id) AS residentName
        FROM income_records
        UNION ALL
        SELECT 
            id, 
            amount, 
            category, 
            payment_mode AS paymentMode, 
            DATE_FORMAT(payment_date, '%Y-%m-%d') AS date, 
            notes, 
            'expense' AS type, 
            NULL AS flat_id,
            '-' AS flatNumber,
            paid_to AS residentName
        FROM expenditure_records
        ORDER BY date DESC, id DESC
        """
        cursor.execute(query)
        records = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/defaulters', methods=['GET'])
def get_defaulters():
    try:
        current_month = datetime.now().strftime('%Y-%m')
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        query = """
        SELECT f.id, f.flat_number, f.owner_name, f.contact_number 
        FROM flats f
        WHERE f.id NOT IN (
            SELECT DISTINCT flat_id 
            FROM income_records 
            WHERE DATE_FORMAT(payment_date, '%Y-%m') = %s
            AND category = 'Monthly Maintenance'
        )
        ORDER BY f.flat_number ASC
        """
        cursor.execute(query, (current_month,))
        defaulters = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(defaulters), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/income', methods=['POST'])
def add_income():
    data = request.get_json()
    try:
        flat_id = data.get('flat_id')
        category = data.get('category')
        amount = data.get('amount')
        payment_mode = data.get('payment_mode')
        payment_date = data.get('payment_date')
        notes = data.get('notes', '')

        db = get_db_connection()
        cursor = db.cursor()
        query = """
        INSERT INTO income_records (flat_id, category, amount, payment_mode, payment_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (flat_id, category, amount, payment_mode, payment_date, notes))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({"success": True, "message": "Income record saved"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/expense', methods=['POST'])
def add_expense():
    data = request.get_json()
    try:
        category = data.get('category')
        amount = data.get('amount')
        paid_to = data.get('paid_to')
        payment_mode = data.get('payment_mode')
        payment_date = data.get('payment_date')
        notes = data.get('notes', '')

        db = get_db_connection()
        cursor = db.cursor()
        query = """
        INSERT INTO expenditure_records (category, amount, paid_to, payment_mode, payment_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (category, amount, paid_to, payment_mode, payment_date, notes))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({"success": True, "message": "Expense record saved"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notice', methods=['GET'])
def get_notice():
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 1")
        notice = cursor.fetchone()
        cursor.close()
        db.close()
        return jsonify(notice or {}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notice', methods=['POST'])
def post_notice():
    data = request.get_json()
    try:
        title = data.get('title')
        description = data.get('description')
        file_url = data.get('file_url')
        file_name = data.get('file_name')

        db = get_db_connection()
        cursor = db.cursor()
        query = "INSERT INTO notices (title, description, file_url, file_name) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (title, description, file_url, file_name))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({"success": True, "message": "Notice updated successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
