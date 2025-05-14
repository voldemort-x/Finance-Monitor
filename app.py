# finance-monitor/app.py - For Render Deployment

import sqlite3
import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from whitenoise import WhiteNoise # For serving static files

# --- Configuration ---
# Determine the base directory of the app.py file
BASE_DIR = os.path.dirname(__file__)

# Database path: Use /tmp for ephemeral storage on Render, or local for development
# Render also provides a /var/data persistent disk on paid plans if needed later.
# For now, ephemeral /tmp is fine for SQLite.
if os.getenv('RENDER_INSTANCE_ID'): # RENDER_INSTANCE_ID is set by Render
     DATABASE_PATH = os.path.join('/tmp', 'finance.db')
     print(f"Running on Render. Using temporary database path: {DATABASE_PATH}")
else:
     DATABASE_PATH = os.path.join(BASE_DIR, 'finance.db')
     print(f"Running locally. Using database path: {DATABASE_PATH}")

# --- Google AI Configuration ---
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
use_llm = False
if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY environment variable not set.")
    print("LLM analysis features will use fallback rule-based logic.")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        print("Attempting to configure Google Generative AI...")
        next(genai.list_models())
        print("Google Generative AI configured successfully.")
        use_llm = True
    except Exception as e:
        print(f"Error configuring Google Generative AI: {e}")
        print("LLM analysis features will use fallback rule-based logic.")
        use_llm = False

# --- Database Functions (SQLite) ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    print("Initializing database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            amount REAL NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM transactions')
    count = cursor.fetchone()[0]
    if count == 0:
        print("Database is empty. Adding sample transactions.")
        sample_transactions = [
            ('Initial Investment (Render)', 'income', 55000.00, '2023-01-01'),
            ('Office Rent (Render)', 'expense', 2200.00, '2023-01-15'),
            # ... add more sample data ...
        ]
        cursor.executemany('''
            INSERT INTO transactions (description, type, amount, date) VALUES (?, ?, ?, ?)
        ''', sample_transactions)
        conn.commit()
    conn.close()
    print("Database initialization complete.")

# --- Analysis Logic (remains the same) ---
def analyze_performance_summary(total_income, total_expense, net_profit):
    # ... (your existing logic) ...
    performance_message = ""
    if use_llm:
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            Based on the following financial data for a finance company:
            Total Income: ${total_income:.2f}
            Total Expense: ${total_expense:.2f}
            Net Profit: ${net_profit:.2f}
            Provide a very brief summary (1-2 sentences) of the overall financial performance. Do not include numerical values in the summary.
            """
            response = model.generate_content(prompt)
            performance_message = response.text.strip()
        except Exception as e:
            print(f"Error calling Google AI API for summary: {e}")
            if net_profit > 5000:
                performance_message = "Excellent performance! (LLM error fallback)"
            elif net_profit > 0:
                performance_message = "Good performance. (LLM error fallback)"
            elif net_profit == 0:
                performance_message = "Breaking even. (LLM error fallback)"
            else:
                performance_message = "Low performance. (LLM error fallback)"
    else:
        if net_profit > 5000:
            performance_message = "Excellent performance! The company shows strong profitability."
        elif net_profit > 0:
            performance_message = "Good performance. The company is profitable."
        elif net_profit == 0:
            performance_message = "The company is currently breaking even."
        else:
            performance_message = "Performance is low. The company is currently experiencing a net loss. Review expenses."
    return performance_message

def analyze_performance_detailed(total_income, total_expense, net_profit):
    # ... (your existing logic) ...
    detailed_message = ""
    if use_llm:
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            Analyze the financial performance of a finance company based on the following aggregate data:
            Total Income: ${total_income:.2f}
            Total Expense: ${total_expense:.2f}
            Net Profit: ${net_profit:.2f}

            Provide an in-depth analysis of the company's financial state.
            Based on these figures, suggest actionable strategies or methods for improving the company's financial health and efficiency.
            Consider both increasing income and decreasing expenses.
            Format the response clearly, perhaps using bullet points for suggestions.
            """
            print("Sending detailed prompt to LLM...")
            response = model.generate_content(prompt)
            print("Received detailed response from LLM.")
            detailed_message = response.text.strip()
        except Exception as e:
            print(f"Error calling Google AI API for detailed analysis: {e}")
            detailed_message = "Error generating detailed analysis from AI. "
            if net_profit < 0:
                detailed_message += "The company is currently running at a loss. Focus on reducing expenses and identifying new revenue streams."
            elif net_profit > 0 and total_expense > total_income * 0.5:
                 detailed_message += "The company is profitable, but expenses seem relatively high compared to income. Look for cost-saving opportunities."
            elif total_income == 0:
                 detailed_message += "No income recorded. Strategies should focus on generating revenue."
            else:
                 detailed_message += "Financial health seems stable. Consider strategies for growth such as expanding services or client acquisition."
            detailed_message += "\n\n(Fallback analysis due to LLM error or configuration issue.)"
    else:
        detailed_message = "LLM analysis is not configured or available. Here are some basic suggestions based on the numbers:\n\n"
        if net_profit < 0:
            detailed_message += "- Urgent: Analyze all expense categories to find areas for reduction.\n"
            detailed_message += "- Identify potential bottlenecks in income generation.\n"
            detailed_message += "- Review pricing models or seek higher-value clients.\n"
        elif net_profit > 0:
            detailed_message += "- Continue monitoring income and expenses.\n"
            detailed_message += "- Investigate opportunities to increase income (e.g., new services, marketing).\n"
            detailed_message += "- Explore ways to optimize operational costs without impacting service quality.\n"
        else:
            detailed_message += "- Analyze whether the current income streams are sustainable.\n"
            detailed_message += "- Look for small cost savings to push into profitability.\n"
            detailed_message += "- Develop strategies to increase client base or service volume.\n"
        detailed_message += "\n(This is a basic fallback analysis, not from an LLM.)"
    return detailed_message

# --- Flask App Setup ---
app = Flask(__name__) # Create the Flask app instance

# Initialize WhiteNoise.
# It will serve files from the root directory where app.py is located.
# For this to work, index.html, script.js, style.css must be in the same directory.
# WhiteNoise will automatically serve index.html for the '/' route.
app.wsgi_app = WhiteNoise(app.wsgi_app, root='.')
app.wsgi_app.add_files('.', prefix='/') # Ensure all files in root are servable

CORS(app, resources={r"/api/*": {"origins": "*"}}) # Apply CORS specifically to /api routes

init_db() # Initialize DB when app starts

# --- API Endpoints (prefixed with /api) ---
# IMPORTANT: For Render with WhiteNoise serving the root, 
# it's cleaner if API routes have a distinct prefix like '/api'.
# If WhiteNoise serves index.html at '/', your Flask @app.route('/') won't be hit.

@app.route('/api/') # Example: a simple API root
def api_index():
    return "Finance Monitor API is running!"

@app.route('/api/transactions', methods=['GET'])
def get_transactions_api(): # Renamed to avoid confusion
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC")
    transactions = cursor.fetchall()
    conn.close()
    transactions_list = [dict(row) for row in transactions]
    return jsonify(transactions_list)

@app.route('/api/add_transaction', methods=['POST'])
def add_new_transaction_api(): # Renamed
    new_transaction = request.json
    if not new_transaction:
        return jsonify({'error': 'Invalid input: No JSON data received'}), 400
    description = new_transaction.get('description')
    type_ = new_transaction.get('type') # Renamed variable
    amount = new_transaction.get('amount')
    date = new_transaction.get('date')

    if not all([description, type_, amount, date]):
        return jsonify({'error': 'Missing required fields: description, type, amount, date'}), 400
    if type_ not in ['income', 'expense']:
         return jsonify({'error': 'Invalid type. Must be "income" or "expense"'}), 400
    try:
        amount = float(amount)
        if amount < 0:
             return jsonify({'error': 'Amount must be positive'}), 400
    except ValueError:
        return jsonify({'error': 'Amount must be a number'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO transactions (description, type, amount, date) VALUES (?, ?, ?, ?)
        ''', (description, type_, amount, date))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({'message': 'Transaction added successfully', 'id': new_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        if conn: conn.close()
        print(f"Database error adding transaction: {e}")
        return jsonify({'error': f'Database error: {e}'}), 500

@app.route('/api/performance_analysis', methods=['GET'])
def get_performance_analysis_api(): # Renamed
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type, SUM(amount) FROM transactions GROUP BY type")
    totals = dict(cursor.fetchall())
    conn.close()
    total_income = totals.get('income', 0.0)
    total_expense = totals.get('expense', 0.0)
    net_profit = total_income - total_expense
    performance_summary_text = analyze_performance_summary(total_income, total_expense, net_profit)
    return jsonify({
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'performance_summary': performance_summary_text
    })

@app.route('/api/detailed_analysis', methods=['GET'])
def get_detailed_analysis_api(): # Renamed
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type, SUM(amount) FROM transactions GROUP BY type")
    totals = dict(cursor.fetchall())
    conn.close()
    total_income = totals.get('income', 0.0)
    total_expense = totals.get('expense', 0.0)
    net_profit = total_income - total_expense
    detailed_report_text = analyze_performance_detailed(total_income, total_expense, net_profit)
    return jsonify({'detailed_report': detailed_report_text})

# This block is for local development only (python app.py)
if __name__ == '__main__':
    # init_db() # Already called when app module loads
    # When running locally with WhiteNoise, Flask's dev server will also serve static files.
    # Gunicorn will be used on Render.
    app.run(debug=True, port=5000, host='0.0.0.0')
