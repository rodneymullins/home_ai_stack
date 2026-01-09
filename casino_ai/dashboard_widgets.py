"""
Casino AI Dashboard Widget

Add this to your dashboard template for AI-enhanced machine display.
"""

# HTML/Jinja2 Template Component
AI_MACHINE_WIDGET = """
<!-- AI Analysis Widget -->
<div class="card mb-3" id="ai-analysis-card">
    <div class="card-header bg-primary text-white">
        <h5 class="mb-0">
            🤖 AI Analysis
            <span class="badge bg-light text-dark float-end" id="ai-confidence-badge">
                Loading...
            </span>
        </h5>
    </div>
    <div class="card-body">
        <div class="row">
            <!-- Hot Score -->
            <div class="col-md-3 text-center">
                <h6 class="text-muted">Hot Score</h6>
                <div class="display-4" id="ai-hot-score">--</div>
                <small class="text-muted">out of 100</small>
            </div>
            
            <!-- Predicted Timing -->
            <div class="col-md-3 text-center">
                <h6 class="text-muted">Next Jackpot</h6>
                <div class="display-4" id="ml-predicted-time">--</div>
                <small class="text-muted">minutes</small>
            </div>
            
            <!-- Classification -->
            <div class="col-md-3 text-center">
                <h6 class="text-muted">Status</h6>
                <span class="badge fs-4" id="ml-classification-badge">
                    ANALYZING
                </span>
            </div>
            
            <!-- Recommendation -->
            <div class="col-md-3 text-center">
                <h6 class="text-muted">Action</h6>
                <div class="fs-5 fw-bold" id="ai-recommendation">
                    --
                </div>
            </div>
        </div>
        
        <hr>
        
        <!-- AI Reasoning -->
        <div class="row mt-3">
            <div class="col-md-12">
                <h6>💡 AI Insights:</h6>
                <p class="mb-0" id="ai-reasoning">
                    Loading AI analysis...
                </p>
            </div>
        </div>
        
        <!-- Pattern Detection -->
        <div class="row mt-2" id="pattern-section" style="display: none;">
            <div class="col-md-12">
                <div class="alert alert-info mb-0">
                    <strong>Pattern Detected:</strong> 
                    <span id="pattern-description">--</span>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Fetch AI analysis for current machine
async function loadAIAnalysis(machineId) {
    try {
        const response = await fetch(`http://192.168.1.176:8080/ai/machine/${machineId}`);
        const data = await response.json();
        
        // Update hot score
        const hotScore = Math.round(data.ai_hot_score * 100);
        document.getElementById('ai-hot-score').textContent = hotScore;
        
        // Update predicted time
        document.getElementById('ml-predicted-time').textContent = 
            data.ml_predicted_minutes || '--';
        
        // Update classification badge
        const classificationBadge = document.getElementById('ml-classification-badge');
        classificationBadge.textContent = data.ml_classification;
        classificationBadge.className = 'badge fs-4 ';
        
        if (data.ml_classification === 'HOT') {
            classificationBadge.classList.add('bg-danger');
        } else if (data.ml_classification === 'WARM') {
            classificationBadge.classList.add('bg-warning', 'text-dark');
        } else {
            classificationBadge.classList.add('bg-info');
        }
        
        // Update recommendation
        document.getElementById('ai-recommendation').innerHTML = 
            data.final_recommendation;
        
        // Update reasoning
        document.getElementById('ai-reasoning').textContent = 
            data.ai_reasoning || 'AI analysis complete';
        
        // Update confidence badge
        const confidence = Math.round(data.ai_confidence * 100);
        document.getElementById('ai-confidence-badge').textContent = 
            `${confidence}% Confidence`;
        
        // Show pattern if detected
        if (data.pattern_detected) {
            document.getElementById('pattern-section').style.display = 'block';
            document.getElementById('pattern-description').textContent = 
                data.pattern_type || 'Consistent jackpot pattern';
        }
        
    } catch (error) {
        console.error('Error loading AI analysis:', error);
        document.getElementById('ai-hot-score').textContent = 'ERR';
        document.getElementById('ai-reasoning').textContent = 
            'AI analysis unavailable. System may be training.';
    }
}

// Load on page load
document.addEventListener('DOMContentLoaded', function() {
    const machineId = "{{ machine_id }}";  // From template context
    loadAIAnalysis(machineId);
    
    // Refresh every 5 minutes
    setInterval(() => loadAIAnalysis(machineId), 300000);
});
</script>
"""

# Hot Machines Alert Widget
HOT_MACHINES_WIDGET = """
<!-- Hot Machines Alert Widget -->
<div class="card mb-3">
    <div class="card-header bg-danger text-white">
        <h5 class="mb-0">
            🔥 Hot Machines Right Now
            <button class="btn btn-sm btn-light float-end" onclick="refreshHotMachines()">
                <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
        </h5>
    </div>
    <div class="card-body p-0">
        <div class="list-group list-group-flush" id="hot-machines-list">
            <div class="list-group-item text-center text-muted">
                Loading hot machines...
            </div>
        </div>
    </div>
</div>

<script>
async function refreshHotMachines() {
    try {
        const response = await fetch('http://192.168.1.176:8080/ai/hot-machines?top_n=10&min_score=0.7');
        const data = await response.json();
        
        const listEl = document.getElementById('hot-machines-list');
        listEl.innerHTML = '';
        
        if (data.machines.length === 0) {
            listEl.innerHTML = `
                <div class="list-group-item text-center text-muted">
                    No hot machines detected right now
                </div>
            `;
            return;
        }
        
        data.machines.forEach((machine, index) => {
            const score = Math.round(machine.combined_score * 100);
            const item = document.createElement('a');
            item.href = `/machine/${machine.machine_id}`;
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${machine.machine_id}</strong>
                        <br>
                        <small class="text-muted">${machine.final_recommendation}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-danger fs-6">${score}</span>
                        <br>
                        <small class="text-muted">Score</small>
                    </div>
                </div>
            `;
            listEl.appendChild(item);
        });
        
    } catch (error) {
        console.error('Error loading hot machines:', error);
        document.getElementById('hot-machines-list').innerHTML = `
            <div class="list-group-item text-center text-danger">
                Error loading hot machines
            </div>
        `;
    }
}

// Load on page load
document.addEventListener('DOMContentLoaded', refreshHotMachines);

// Refresh every 2 minutes
setInterval(refreshHotMachines, 120000);
</script>
"""

# Save as file
if __name__ == "__main__":
    with open('casino_ai_widget.html', 'w') as f:
        f.write(AI_MACHINE_WIDGET)
        f.write('\n\n')
        f.write(HOT_MACHINES_WIDGET)
    
    print("✅ Dashboard widgets saved to casino_ai_widget.html")
