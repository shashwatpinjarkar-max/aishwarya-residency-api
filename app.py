import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)

# TiDB Cloud Configuration (Works both locally and on Render)
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"),
    "user": os.environ.get("DB_USER", "3SgfrJ4hVt3X9Ww.root"),
    "password": os.environ.get("DB_PASSWORD", "xfkvih2rTzUSIebN"),
    "database": os.environ.get("DB_NAME", "test"),
    "port": int(os.environ.get("DB_PORT", 4000)),
    "ssl_verify_cert": False
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# 1. Fetch All Flats
@app.route('/api/flats', methods=['GET'])
def get_flats():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM flats ORDER BY flat_number ASC")
        flats = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(flats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. Fetch Unified Transactions (Income + Expenses)
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT i.id, 'income' AS type, i.category, CAST(i.amount AS FLOAT) AS amount, 
                   i.payment_mode AS paymentMode, DATE_FORMAT(i.payment_date, '%Y-%m-%d') AS date,
                   f.flat_number AS flatNumber, f.owner_name AS residentName
            FROM income_records i
            LEFT JOIN flats f ON i.flat_id = f.id
        """)
        income = cursor.fetchall()

        cursor.execute("""
            SELECT id, 'expense' AS type, category, CAST(amount AS FLOAT) AS amount, 
                   payment_mode AS paymentMode, DATE_FORMAT(payment_date, '%Y-%m-%d') AS date,
                   '-' AS flatNumber, paid_to AS residentName
            FROM expenditure_records
        """)
        expenses = cursor.fetchall()

        cursor.close()
        conn.close()

        all_records = sorted(income + expenses, key=lambda x: x['date'], reverse=True)
        return jsonify(all_records), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. Add Income Entry
@app.route('/api/income', methods=['POST'])
def add_income():
    data = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        query = """
            INSERT INTO income_records (flat_id, category, amount, payment_mode, payment_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data.get('flat_id'),
            data.get('category'),
            data.get('amount'),
            data.get('payment_mode'),
            data.get('payment_date'),
            data.get('notes')
        ))
        conn.commit()
        record_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({"message": "Income saved", "id": record_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. Add Expense Entry
@app.route('/api/expense', methods=['POST'])
def add_expense():
    data = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        query = """
            INSERT INTO expenditure_records (category, amount, paid_to, payment_mode, payment_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data.get('category'),
            data.get('amount'),
            data.get('paid_to'),
            data.get('payment_mode'),
            data.get('payment_date'),
            data.get('notes')
        ))
        conn.commit()
        record_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({"message": "Expense saved", "id": record_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 5. Defaulter Tracking for Current Month
@app.route('/api/defaulters', methods=['GET'])
def get_defaulters():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT f.id, f.flat_number, f.owner_name, f.contact_number
            FROM flats f
            WHERE f.id NOT IN (
                SELECT DISTINCT flat_id 
                FROM income_records 
                WHERE flat_id IS NOT NULL 
                  AND category = 'Monthly Maintenance'
                  AND MONTH(payment_date) = MONTH(CURRENT_DATE())
                  AND YEAR(payment_date) = YEAR(CURRENT_DATE())
            )
            ORDER BY f.flat_number ASC
        """
        cursor.execute(query)
        defaulters = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(defaulters), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)