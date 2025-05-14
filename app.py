# finance-monitor-vercel/app.py - Core Flask application logic for Vercel with PostgreSQL

import os
import psycopg2 # For PostgreSQL
from psycopg2 import sql # For safe SQL identifiers, if needed
from psycopg2.extras import RealDictCursor # To get results as dictionaries
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# --- Database Configuration (PostgreSQL for Vercel/Neon) ---
# Vercel, when integrated with Neon, will provide this environment variable.
DATABASE_URL = os.getenv('POSTGRES_URL')

if not DATABASE_URL:
    print("CRITICAL: POSTGRES_URL environment variable not set. Database will not connect.")
    # In a real app, you might want to raise an exception or exit if the DB is essential.

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

# --- Database Functions (PostgreSQL) ---

def get_db_connection():
    """Creates and returns a PostgreSQL database connection."""
    if not DATABASE_URL:
        raise ConnectionError("DATABASE_URL not configured.")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        raise # Re-raise the exception to be caught by the caller

def init_db():
    """Initializes the PostgreSQL database and creates the transactions table if it doesn't exist."""
    print("Initializing PostgreSQL database schema...")
    conn = None
    try:
        conn = get_db_connection()
        # Using RealDictCursor makes fetchall() return a list of dicts directly
        with conn.cursor() as cur: # Using 'with' ensures the cursor is closed
            cur.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    description TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                    amount REAL NOT NULL,
                    date DATE NOT NULL 
                )
            ''')

            cur.execute('SELECT COUNT(*) FROM transactions')
            count_result = cur.fetchone()
             # fetchone() on an empty table with COUNT(*) should return (0,), not None
            count = count_result[0] if count_result else 0


            if count == 0:
                print("PostgreSQL transactions table is empty. Adding sample transactions.")
                sample_transactions = [
                    ('Initial Cloud Investment', 'income', 50000.00, '2023-01-01'),
                    ('Cloud Server Hosting', 'expense', 200.00, '2023-01-15'),
                    ('Consulting Services (Client X)', 'income', 12000.00, '2023-02-10'),
                    ('Software Licensing', 'expense', 180.00, '2023-02-12'),
                    ('Employee Salaries', 'expense', 8500.00, '2023-02-28'),
                    ('Project Fee (Client Y)', 'income', 18000.00, '2023-03-05'),
                ]
                # For executemany with psycopg2, the query placeholders are %s
                cur.executemany('''
                    INSERT INTO transactions (description, type, amount, date) VALUES (%s, %s, %s, %s)
                ''', sample_transactions)
            
            conn.commit() # Commit changes
    except (Exception, psycopg2.Error) as error:
        print(f"Error while initializing PostgreSQL database: {error}")
        if conn:
            conn.rollback() # Rollback in case of error during init
    finally:
        if conn:
            conn.close()
    print("PostgreSQL database initialization attempt complete.")

# --- Analysis Logic (remains the same as your SQLite version) ---
def analyze_performance_summary(total_income, total_expense, net_profit):
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

# Initialize DB when the Flask app module is loaded by Vercel.
# This is crucial for serverless environments.
init_db()

# --- API Endpoints (Adapted for PostgreSQL) ---

@app.route('/')
def index():
    """Root endpoint - just a status check."""
    return "Finance Monitor Backend (PostgreSQL) is running!"

@app.route('/transactions', methods=['GET'])
def get_transactions():
    """Fetches all transactions."""
    conn = None
    try:
        conn = get_db_connection()
        # Using RealDictCursor to get results as dictionaries directly
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, description, type, amount, date FROM transactions ORDER BY date DESC, id DESC")
            transactions_list = cur.fetchall() # Now a list of dicts
        return jsonify(transactions_list)
    except (Exception, psycopg2.Error) as error:
        print(f"Error fetching transactions: {error}")
        return jsonify({'error': f'Database error fetching transactions: {error}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/add_transaction', methods=['POST'])
def add_new_transaction():
    """Adds a new transaction from POST request data."""
    new_transaction_data = request.json
    if not new_transaction_data:
        return jsonify({'error': 'Invalid input: No JSON data received'}), 400

    description = new_transaction_data.get('description')
    # Renamed 'type' to 'type_' to avoid conflict with Python's built-in type
    type_ = new_transaction_data.get('type') 
    amount_str = new_transaction_data.get('amount') # Amount might come as string
    date_str = new_transaction_data.get('date') # Date string from JSON

    if not all([description, type_, amount_str, date_str]):
        return jsonify({'error': 'Missing required fields: description, type, amount, date'}), 400

    if type_ not in ['income', 'expense']:
         return jsonify({'error': 'Invalid type. Must be "income" or "expense"'}), 400

    try:
        amount = float(amount_str) # Convert amount to float
        if amount < 0:
             return jsonify({'error': 'Amount must be positive'}), 400
    except ValueError:
        return jsonify({'error': 'Amount must be a number'}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Use %s for placeholders in psycopg2
            # RETURNING id will give back the id of the newly inserted row
            cur.execute('''
                INSERT INTO transactions (description, type, amount, date) VALUES (%s, %s, %s, %s)
                RETURNING id; 
            ''', (description, type_, amount, date_str)) # Ensure date_str is in 'YYYY-MM-DD' format
            new_id_tuple = cur.fetchone() # fetchone() returns a tuple, e.g., (new_id_value,)
            if new_id_tuple is None:
                raise Exception("Failed to insert transaction or retrieve new ID.")
            new_id = new_id_tuple[0]
            conn.commit()
        return jsonify({'message': 'Transaction added successfully', 'id': new_id}), 201
    except (Exception, psycopg2.Error) as error:
        print(f"Database error adding transaction: {error}")
        if conn:
            conn.rollback() # Rollback on error
        return jsonify({'error': f'Database error adding transaction: {error}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/performance_analysis', methods=['GET'])
def get_performance_analysis_route():
    """Route for the brief summary analysis."""
    conn = None
    total_income = 0.0
    total_expense = 0.0
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur: # Use RealDictCursor
            cur.execute("SELECT type, SUM(amount) AS total FROM transactions GROUP BY type")
            totals_rows = cur.fetchall() # List of dicts, e.g., [{'type': 'income', 'total': 500.0}]
        
        for row in totals_rows:
            if row['type'] == 'income':
                total_income = row['total'] if row['total'] is not None else 0.0
            elif row['type'] == 'expense':
                total_expense = row['total'] if row['total'] is not None else 0.0
        
    except (Exception, psycopg2.Error) as error:
        print(f"Error calculating performance analysis: {error}")
        return jsonify({'error': f'Database error in performance analysis: {error}'}), 500
    finally:
        if conn:
            conn.close()

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
    conn = None
    total_income = 0.0
    total_expense = 0.0
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur: # Use RealDictCursor
            cur.execute("SELECT type, SUM(amount) AS total FROM transactions GROUP BY type")
            totals_rows = cur.fetchall()

        for row in totals_rows:
            if row['type'] == 'income':
                total_income = row['total'] if row['total'] is not None else 0.0
            elif row['type'] == 'expense':
                total_expense = row['total'] if row['total'] is not None else 0.0
        
    except (Exception, psycopg2.Error) as error:
        print(f"Error calculating detailed analysis totals: {error}")
        return jsonify({'error': f'Database error in detailed analysis: {error}'}), 500
    finally:
        if conn:
            conn.close()
            
    net_profit = total_income - total_expense
    detailed_report_text = analyze_performance_detailed(total_income, total_expense, net_profit)

    return jsonify({
        'detailed_report': detailed_report_text
    })

# Vercel handles the WSGI server (like Gunicorn) and execution,
# so the if __name__ == '__main__': block is not needed for Vercel deployment.
# You can keep it for local testing if you set DATABASE_URL locally and run 'python app.py'.
# if __name__ == '__main__':
#     # For local testing against a PostgreSQL DB (e.g., local or cloud like Neon)
#     # ensure DATABASE_URL is set in your environment.
#     # init_db() # Already called when the app module is loaded
#     app.run(debug=True, port=5001) # Example port for local testing
