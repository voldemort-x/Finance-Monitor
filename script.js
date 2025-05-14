// Define the backend API base URL
// For local testing, use http://localhost:5000
// For Vercel deployment with '/api' route, use '/api'
const API_URL = '/api'; // Use '/api' for Vercel deployment // Or '/api' for Vercel structure

// --- Functions to Fetch Data from Backend ---

async function fetchTransactions() {
    try {
        const response = await fetch(`${API_URL}/transactions`);
        if (!response.ok) {
            console.error(`HTTP error fetching transactions: status ${response.status}`);
            const errorText = await response.text();
            console.error('Backend error details:', errorText);
            throw new Error(`Failed to fetch transactions: ${response.status} - ${errorText}`);
        }
        const transactions = await response.json();
        displayTransactions(transactions);
    } catch (error) {
        console.error('Error fetching transactions:', error);
        document.getElementById('transactions-table').getElementsByTagName('tbody')[0].innerHTML = '<tr><td colspan="4">Error loading transactions.</td></tr>';
    }
}

async function fetchPerformanceAnalysis() {
    try {
        const response = await fetch(`${API_URL}/performance_analysis`);
        if (!response.ok) {
             console.error(`HTTP error fetching summary analysis: status ${response.status}`);
             const errorText = await response.text();
             console.error('Backend error details:', errorText);
             throw new Error(`Failed to fetch summary analysis: ${response.status} - ${errorText}`);
        }
        const report = await response.json();
        displayPerformanceReport(report);
    } catch (error) {
        console.error('Error fetching performance analysis:', error);
         document.getElementById('report-content').innerHTML = '<p style="color: red;">Error loading summary analysis. Check backend console for details.</p>';
    }
}

 async function fetchDetailedAnalysis() {
     const reviewButton = document.getElementById('review-button');
     const detailedReportDiv = document.getElementById('detailed-report-content');

     detailedReportDiv.innerHTML = '<p>Loading detailed analysis...</p>'; // Loading message
     reviewButton.disabled = true; // Disable button during fetch

     try {
         const response = await fetch(`${API_URL}/detailed_analysis`);
         if (!response.ok) {
             console.error(`HTTP error fetching detailed analysis: status ${response.status}`);
             const errorText = await response.text();
             console.error('Backend error details:', errorText);
             throw new Error(`Failed to fetch detailed analysis: ${response.status} - ${errorText}`);
         }
         const report = await response.json();
         // Assuming the backend returns {'detailed_report': 'AI text'}
         // Use textContent to prevent potential XSS if LLM output wasn't strictly text
         // But given white-space: pre-wrap, innerHTML might be preferred to render line breaks
         detailedReportDiv.innerHTML = `<p>${report.detailed_report}</p>`;

     } catch (error) {
         console.error('Error fetching detailed analysis:', error);
         detailedReportDiv.innerHTML = '<p style="color: red;">Error loading detailed analysis. Check backend console for details.</p>';
     } finally {
         reviewButton.disabled = false; // Re-enable button
     }
 }


// --- Functions to Display Data in Frontend ---

function displayTransactions(transactions) {
    const tbody = document.getElementById('transactions-table').getElementsByTagName('tbody')[0];
    tbody.innerHTML = ''; // Clear current transactions

    if (!transactions || transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4">No transactions found.</td></tr>';
        return;
    }

    transactions.forEach(tx => {
        const row = tbody.insertRow();
        const amountClass = tx.type === 'income' ? 'income' : 'expense';
        const amountSign = tx.type === 'expense' ? '-' : ''; // Add sign for expense

        row.insertCell(0).textContent = tx.date; // Display date
        row.insertCell(1).textContent = tx.description;
        row.insertCell(2).textContent = tx.type;
        const amountCell = row.insertCell(3);
        amountCell.textContent = `${amountSign}$${tx.amount.toFixed(2)}`; // Format amount with sign and $
        amountCell.classList.add(amountClass); // Add class for styling
    });
}

function displayPerformanceReport(report) {
    const reportContentDiv = document.getElementById('report-content');
     // Clear previous error/loading message
    reportContentDiv.innerHTML = '';

    if (!report) {
         reportContentDiv.innerHTML = '<p style="color: red;">Summary analysis data unavailable.</p>';
         return;
    }

    reportContentDiv.innerHTML = `
        <p><strong>Total Income:</strong> $${report.total_income.toFixed(2)}</p>
        <p><strong>Total Expense:</strong> $${report.total_expense.toFixed(2)}</p>
        <p><strong>Net Profit:</strong> $${report.net_profit.toFixed(2)}</p>
        <p><strong>Analysis:</strong> ${report.performance_summary}</p>
    `;
     // Add color based on net profit
    const netProfitElement = reportContentDiv.querySelector('p:nth-child(3)'); // Select the Net Profit paragraph
    if (report.net_profit > 0) {
        netProfitElement.style.color = 'green';
    } else if (report.net_profit < 0) {
        netProfitElement.style.color = 'red';
    } else {
         netProfitElement.style.color = 'inherit'; // Default color
    }
}

// --- Function to Handle Form Submission ---

async function handleAddTransaction(event) {
    event.preventDefault(); // Prevent page reload

    const form = event.target;
    const description = form.elements['description'].value;
    const type = form.elements['type'].value;
    const amount = parseFloat(form.elements['amount'].value);
    const date = form.elements['date'].value;

    // Basic client-side validation (backend also validates)
    if (!description || !type || isNaN(amount) || amount <= 0 || !date) {
        alert('Please fill in all fields correctly (Amount must be positive).');
        return;
    }

    const newTransaction = {
        description: description,
        type: type,
        amount: amount,
        date: date // Send date in YYYY-MM-DD format
    };

    try {
        const response = await fetch(`${API_URL}/add_transaction`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(newTransaction),
        });

        const result = await response.json(); // Attempt to parse JSON even on error

        if (response.ok) {
            console.log('Transaction added:', result);
            alert('Transaction added successfully!');
            form.reset(); // Clear the form

            // Refresh the lists after adding
            fetchTransactions();
            fetchPerformanceAnalysis();
            // Do NOT automatically fetch detailed analysis on add - it's on button click now
            // fetchDetailedAnalysis(); // Removed this line
        } else {
             console.error('Error adding transaction:', result);
             // Display backend error message if available, otherwise use status text
             alert(`Failed to add transaction: ${result.error || response.statusText}`);
        }

    } catch (error) {
        console.error('Error adding transaction:', error);
        alert('An unexpected error occurred while adding the transaction.');
    }
}

// --- Initialize the App ---

// Add event listener to the transaction form
document.getElementById('transaction-form').addEventListener('submit', handleAddTransaction);

// Add event listener to the Review button
document.getElementById('review-button').addEventListener('click', fetchDetailedAnalysis);


// Fetch initial data when the page loads
document.addEventListener('DOMContentLoaded', () => {
    fetchTransactions();
    fetchPerformanceAnalysis();
    // Initial detailed analysis is triggered by button click, not page load
    // fetchDetailedAnalysis(); // Removed this line
});