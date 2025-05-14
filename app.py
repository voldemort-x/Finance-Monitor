# finance-monitor-vercel/app.py - Core Flask application logic

import sqlite3
import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
# import os # Already imported above

# --- Configuration ---
# Define the path for the SQLite database file
# NOTE: When deployed on Vercel, this path will be inside the ephemeral /tmp directory.
# Data stored here will NOT persist between function invocations.
# For local development, we'll still use the local path relative to the script.

# Determine the base directory of the app.py file
BASE_DIR = os.path.dirname(__file__)

# Database path depends on the environment
# On Vercel, use /tmp. Otherwise, use the local path.
# The VERCEL environment variable is set automatically by Vercel.
if "VERCEL" in os.environ:
     DATABASE_PATH = os.path.join('/tmp', 'finance.db')
     print(f"Running on Vercel. Using temporary database path: {DATABASE_PATH}")
else:
     DATABASE_PATH = os.path.join(BASE_DIR, 'finance.db')
     print(f"Running locally. Using database path: {DATABASE_PATH}")


# --- Google AI Configuration ---
# This key will be read from Vercel Environment Variables (or local env)
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

use_llm = False # Flag to track if LLM is successfully configured

if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY environment variable not set.")
    print("LLM analysis features (summary and detailed) will use fallback rule-based logic.")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # Attempt a basic call to list models to verify the key and connection
        # This can add a small delay on cold starts.
        print("Attempting to configure Google Generative AI...")
        # We don't need the result, just testing the connection/auth
        # Using next() ensures we only fetch one item, slightly faster
        next(genai.list_models())
        print("Google Generative AI configured successfully.")
        use_llm = True
    except Exception as e:
        print(f"Error configuring Google Generative AI: {e}")
        print("LLM analysis features (summary and detailed) will use fallback rule-based logic.")
        # Ensure use_llm remains False


# --- Database Functions ---

def get_db_connection():
    """Creates and returns a database connection."""
    # This function now correctly uses DATABASE_PATH which is set based on environment
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def init_db():
    """Initializes the database and creates the transactions table."""
    # This function will run when the Vercel function starts up.
    # It handles creating the table and adding sample data if the DB is empty.
    # Since the DB is created in /tmp on Vercel, it will be empty on every cold start.
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

    # Check if table is empty BEFORE adding sample data
    # This prevents adding duplicates if the function instance is reused (warm start)
    cursor.execute('SELECT COUNT(*) FROM transactions')
    count = cursor.fetchone()[0]

    if count == 0:
        print("Database is empty. Adding sample transactions.")
        sample_transactions = [
            ('Initial Investment', 'income', 50000.00, '2023-01-01'),
            ('Office Rent', 'expense', 2000.00, '2023-01-15'),
            ('Consulting Fee (Client A)', 'income', 10000.00, '2023-02-10'),
            ('Software Subscription', 'expense', 150.00, '2023-02-12'),
            ('Salaries', 'expense', 8000.00, '2023-02-28'),
            ('Consulting Fee (Client B)', 'income', 15000.00, '2023-03-05'),
        ]
        cursor.executemany('''
            INSERT INTO transactions (description, type, amount, date) VALUES (?, ?, ?, ?)
        ''', sample_transactions)
        conn.commit() # Commit only if new data was added

    conn.close()
    print("Database initialization complete.")


# --- Analysis Logic (Using LLM if configured, with fallbacks) ---
# Keep these functions exactly the same as in the previous updated app.py

def analyze_performance_summary(total_income, total_expense, net_profit):
    """
    Generates a brief performance summary, using LLM if configured,
    otherwise using simple rules.
    """
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
    """
    Generates a detailed performance analysis with improvement suggestions,
    using LLM if configured, otherwise using basic suggestions.
    """
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

app = Flask(__name__)
CORS(app)

# Initialize DB when the module is loaded (i.e., when the serverless function starts)
# This is crucial for Vercel as the /tmp filesystem is ephemeral.
# This ensures the table and sample data are ready for each new function instance.
init_db()

# --- API Endpoints ---

# The root route '/' won't be hit by the vercel.json config below,
# which routes '/' to static/index.html
@app.route('/')
def index():
    """Root endpoint - just a status check (unlikely to be hit by frontend)."""
    return "Finance Monitor Backend is running!"

@app.route('/transactions', methods=['GET'])
def get_transactions():
    """Fetches all transactions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC")
    transactions = cursor.fetchall()
    conn.close()
    transactions_list = [dict(row) for row in transactions]
    return jsonify(transactions_list)

@app.route('/add_transaction', methods=['POST'])
def add_new_transaction():
    """Adds a new transaction from POST request data."""
    new_transaction = request.json
    if not new_transaction:
        return jsonify({'error': 'Invalid input: No JSON data received'}), 400

    description = new_transaction.get('description')
    type = new_transaction.get('type')
    amount = new_transaction.get('amount')
    date = new_transaction.get('date')

    if not all([description, type, amount, date]):
        return jsonify({'error': 'Missing required fields: description, type, amount, date'}), 400

    if type not in ['income', 'expense']:
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
        ''', (description, type, amount, date))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({'message': 'Transaction added successfully', 'id': new_id}), 201
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Database error adding transaction: {e}")
        return jsonify({'error': f'Database error: {e}'}), 500

@app.route('/performance_analysis', methods=['GET'])
def get_performance_analysis_route():
    """Route for the brief summary analysis."""
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


@app.route('/detailed_analysis', methods=['GET'])
def get_detailed_analysis_route():
    """New route for the detailed analysis and suggestions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type, SUM(amount) FROM transactions GROUP BY type")
    totals = dict(cursor.fetchall())
    conn.close()

    total_income = totals.get('income', 0.0)
    total_expense = totals.get('expense', 0.0)
    net_profit = total_income - total_expense

    detailed_report_text = analyze_performance_detailed(total_income, total_expense, net_profit)

    return jsonify({
        'detailed_report': detailed_report_text
    })

# Remove the __main__ block as Vercel handles execution
# if __name__ == '__main__':
#     # init_db() # This call is moved up for Vercel
#     app.run(debug=True)