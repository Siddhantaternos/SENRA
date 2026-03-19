async function sendExpense() {
    const response = await fetch('https://senra-production.up.railway.app', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item: 'test-item', amount: 10 })
    });
    const data = await response.json();
    console.log("Response from server:", data);
}
