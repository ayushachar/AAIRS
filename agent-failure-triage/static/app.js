document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('accuracyChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Baseline (No Reflection)', 'LangGraph Reflection Pipeline'],
            datasets: [{
                label: 'Diagnostic & Grounding Accuracy (%)',
                data: [32, 100],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.6)',
                    'rgba(14, 165, 233, 0.6)'
                ],
                borderColor: [
                    'rgba(239, 68, 68, 1)',
                    'rgba(14, 165, 233, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });

    document.getElementById('triage-btn').addEventListener('click', async () => {
        const trace = document.getElementById('raw-trace').value;
        if (!trace) return alert('Enter a trace first.');

        document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
        document.getElementById('step-triage').classList.add('active');

        try {
            const sessionId = "sess_" + Math.random().toString(36).substring(7);
            const response = await fetch('/v1/triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, raw_trace: trace })
            });
            const data = await response.json();
            
            setTimeout(() => {
                document.getElementById('step-triage').classList.remove('active');
                document.getElementById('step-verifier').classList.add('active');
                
                setTimeout(() => {
                    document.getElementById('step-verifier').classList.remove('active');
                    if (data.retries_used > 0) {
                        document.getElementById('step-reflection').classList.add('active');
                    }
                    setTimeout(() => {
                        document.getElementById('step-reflection').classList.remove('active');
                        document.getElementById('step-resolved').classList.add('active');
                        
                        const diagRes = document.getElementById('diagnosis-results');
                        if (data.diagnosis) {
                            diagRes.innerHTML = `
                                <h3>Classification: <span class="success">${data.diagnosis.layer}</span></h3>
                                <p><strong>Root Cause:</strong> ${data.diagnosis.root_cause_summary}</p>
                                <p><strong>Remediation:</strong> ${data.diagnosis.suggested_remediation}</p>
                                <h4>Grounding Evidence (${data.is_verified ? 'Verified' : 'Unverified'}):</h4>
                                <ul>${data.diagnosis.cited_evidence.map(e => `<li>${e}</li>`).join('')}</ul>
                            `;
                        } else {
                            diagRes.innerHTML = `<p class="warning">Failed to extract diagnosis.</p>`;
                        }
                        
                    }, data.retries_used > 0 ? 1000 : 0);
                }, 1000);
            }, 1000);
            
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to connect to triage API.');
        }
    });
});
