// Define the backend API base URL
// For local testing: 'http://localhost:5000/api'
// For Render deployment: '/api' (since it's served from the same domain)
const API_BASE_URL = '/api';

// --- Functions to Fetch Data from Backend ---

async function fetchTransactions() {
    try {
        const response = await fetch(`${API_BASE_URL}/transactions`);
        // ... (rest of the function is the same as your Vercel version) ...
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
        const response = await fetch(`${API_BASE_URL}/performance_analysis`);
        // ... (rest of the function is the same as your Vercel version) ...
        if (!response.ok) {
             console.error(`HTTP error fetching summary analysis: status ${response.status}`);
             const errorText = await response.text();
             console.error('Backend error details:', errorText);
             throw new Error(`Failed to fetch summary analysis: ${response.status} - ${errorText}`);
        }
        const report = await response.json();
        displayPerformanceReport(report);
    } catch (error)
        // ... (rest of the function is the same as your Vercel version) ...
        console.error('Error fetching performance analysis:', error);
        document.getElementById('report-content').innerHTML = '<p style="color: red;">Error loading summary analysis. Check backend console for details.</p>';
    }


 async function fetchDetailedAnalysis() {
     const reviewButton = document.getElementById('review-button');
     const detailedReportDiv = document.getElementById('detailed-report-content');
     detailedReportDiv.innerHTML = '<p>Loading detailed analysis...</p>'; 
     reviewButton.disabled = true; 

     try {
         const response = await fetch(`${API_BASE_URL}/detailed_analysis`);
        // ... (rest of the function is the same as your Vercel version) ...
         if (!response.ok) {
             console.error(`HTTP error fetching detailed analysis: status ${response.status}`);
             const errorText = await response.text();
             console.error('Backend error details:', errorText);
             throw new Error(`Failed to fetch detailed analysis: ${response.status} - ${errorText}`);
         }
         const report = await response.json();
         detailedReportDiv.innerHTML = `<p>${report.detailed_report}</p>`;
     } catch (error) {
        // ... (rest of the function is the same as your Vercel version) ...
         console.error('Error fetching detailed analysis:', error);
         detailedReportDiv.innerHTML = '<p style="color: red;">Error loading detailed analysis. Check backend console for details.</p>';
     } finally {
         reviewButton.disabled = false; 
     }
 }

// ... (displayTransactions, displayPerformanceReport functions remain the same) ...

async function handleAddTransaction(event) {
    event.preventDefault(); 
    // ... (form data extraction is the same) ...
    const form = event.target;
    const description = form.elements['description'].value;
    const type = form.elements['type'].value;
    const amount = parseFloat(form.elements['amount'].value);
    const date = form.elements['date'].value;

    if (!description || !type || isNaN(amount) || amount <= 0 || !date) {
        alert('Please fill in all fields correctly (Amount must be positive).');
        return;
    }
    const newTransaction = { description, type, amount, date };

    try {
        const response = await fetch(`${API_BASE_URL}/add_transaction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', },
            body: JSON.stringify(newTransaction),
        });
        // ... (response handling is the same as your Vercel version) ...
        const result = await response.json(); 
        if (response.ok) {
            console.log('Transaction added:', result);
            alert('Transaction added successfully!');
            form.reset(); 
            fetchTransactions();
            fetchPerformanceAnalysis();
        } else {
             console.error('Error adding transaction:', result);
             alert(`Failed to add transaction: ${result.error || response.statusText}`);
        }
    } catch (error) {
        // ... (error handling is the same as your Vercel version) ...
        console.error('Error adding transaction:', error);
        alert('An unexpected error occurred while adding the transaction.');
    }
}

// --- Initialize the App (remains the same) ---
document.getElementById('transaction-form').addEventListener('submit', handleAddTransaction);
document.getElementById('review-button').addEventListener('click', fetchDetailedAnalysis);
document.addEventListener('DOMContentLoaded', () => {
    fetchTransactions();
    fetchPerformanceAnalysis();
});
