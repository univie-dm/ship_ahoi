<template>
  <AppLayout :showSidebar="false" :showNavbar="true">
    <template #default>
      <div class="index-page explanation-page">
        <!-- Hero Section -->
        <header class="hero-gradient">
            <div class="container hero-container">
                <div class="hero-content">
                    <h1 class="hero-title">SHIP.AHOI Explanations</h1>
                    <p class="hero-subtitle-lead">Understanding the Algorithms</p>
                    <p class="hero-subtitle-main">
                        Learn about the internal workings of the SHIP framework, from how similarity trees are built to how we evaluate the final clustering quality.
                    </p>
                </div>
            </div>
        </header>

        <main class="container main-content">
            <!-- The SHIP Framework Section -->
            <section id="framework">
                <h2 class="section-title">The Core Components</h2>
                <div class="framework-grid">
                    
                    <!-- Card 1: Tree Types -->
                    <div class="framework-card active">
                        <div class="framework-card-header">
                            <div>
                                <div class="framework-icon">🌲</div>
                                <h3 class="framework-title">Tree Types (Similarity)</h3>
                                <p class="framework-description">
                                    Models data relationships into a hierarchy.
                                </p>
                            </div>
                        </div>
                        <div class="details-content" style="max-height: fit-content; opacity: 1;">
                            <div class="details-inner">
                                <p class="details-text">We translate pairwise distances into a hierarchical tree (an Ultrametric). Different tree types capture different aspects of the data.</p>
                                
                                <!-- Interactive Tree Type Visualization -->
                                <div class="interactive-demo">
                                    <h4 class="demo-heading">Tree Types determine the "Map"</h4>
                                    <p class="demo-description">Select a tree type to see how it connects data points:</p>
                                    
                                    <div class="tree-selector">
                                        <button class="tree-btn active" data-tree="dctree">DCTree</button>
                                        <button class="tree-btn" data-tree="covertree">CoverTree</button>
                                        <button class="tree-btn" data-tree="balltree">BallTree</button>
                                        <button class="tree-btn" data-tree="kdtree">KDTree</button>
                                        <button class="tree-btn" data-tree="rtree">RTree</button>
                                    </div>
                                    
                                    <div class="demo-canvas-container">
                                        <canvas id="tree-demo-canvas" width="400" height="250"></canvas>
                                        <div class="demo-caption" id="tree-demo-caption">DCTree: Builds density-based connections, great for complex shapes.</div>
                                    </div>
                                </div>
                                <h4 class="details-heading">Details</h4>
                                <ul class="details-list">
                                    <li><strong>DCTree</strong>: Explores density connectivity (like DBSCAN). Connects points in dense regions.</li>
                                    <li><strong>CoverTree / BallTree</strong>: Good for finding spatial proximity and spherical distributions.</li>
                                    <li><strong>KDTree / RTree</strong>: Axis-aligned and bounding box spatial partitioning.</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <!-- Card 2: Power Parameter -->
                    <div class="framework-card active">
                         <div class="framework-card-header">
                            <div>
                                <div class="framework-icon">⚡</div>
                                <h3 class="framework-title">Power Parameter</h3>
                                <p class="framework-description">
                                    The objective function penalty.
                                </p>
                            </div>
                        </div>
                        <div class="details-content" style="max-height: fit-content; opacity: 1;">
                            <div class="details-inner">
                                <p class="details-text">The Power Parameter controls how we penalize distances. Low values prioritize connectivity, while high values enforce strict compactness.</p>
                                
                                <!-- Interactive Power Parameter Visualization -->
                                <div class="interactive-demo">
                                    <h4 class="demo-heading">Power Parameter controls Compactness</h4>
                                    
                                    <div class="power-controls">
                                        <label for="power-slider">Power Parameter: <span id="power-value">2</span></label>
                                        <input type="range" id="power-slider" min="0" max="10" step="1" value="2" class="power-slider">
                                        <div class="power-labels">
                                            <span>0 (Connected)</span>
                                            <span>2 (Balanced)</span>
                                            <span>10 (Ultra-Tight)</span>
                                        </div>
                                    </div>
                                    
                                    <div class="demo-canvas-container">
                                        <canvas id="power-demo-canvas" width="400" height="250"></canvas>
                                        <div class="demo-caption" id="power-demo-caption">Power = 2: Standard k-Means objective. Balanced compactness.</div>
                                    </div>
                                </div>
                                <h4 class="details-heading">Details</h4>
                                <ul class="details-list">
                                    <li><strong>Power ≈ 0 (k-Center)</strong>: Minimizes max distance. Finds connected components.</li>
                                    <li><strong>Power = 1 (k-Median)</strong>: Minimizes sum of distances. Robust to outliers.</li>
                                    <li><strong>Power = 2 (k-Means)</strong>: Standard squared distance penalty. Promotes spherical clusters.</li>
                                    <li><strong>Power > 2</strong>: Forces clusters to be exceedingly compact and regular.</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <!-- Card 3: Partition Methods -->
                    <div class="framework-card active">
                         <div class="framework-card-header">
                            <div>
                                <div class="framework-icon">✂️</div>
                                <h3 class="framework-title">K-Finding (Partition)</h3>
                                <p class="framework-description">
                                    How the final clusters are extracted.
                                </p>
                            </div>
                        </div>
                        <div class="details-content" style="max-height: fit-content; opacity: 1;">
                             <div class="details-inner">
                                <p class="details-text">A hierarchy contains possible clusterings from 1 to N clusters. The partition step cuts this tree to find the optimal 'K'.</p>
                                
                                <!-- Interactive Partition Method Visualization -->
                                <div class="interactive-demo">
                                    <h4 class="demo-heading">Smart Partitioning</h4>
                                    
                                    <div class="partition-selector">
                                        <button class="partition-btn active" data-method="k">K (Manual)</button>
                                        <button class="partition-btn" data-method="elbow">Elbow</button>
                                        <button class="partition-btn" data-method="stability">Stability</button>
                                        <button class="partition-btn" data-method="qcoverage">QCoverage</button>
                                        <button class="partition-btn" data-method="silhouette">Silhouette</button>
                                    </div>
                                    
                                    <div class="demo-canvas-container">
                                        <canvas id="partition-demo-canvas" width="400" height="250"></canvas>
                                        <div class="demo-caption" id="partition-demo-caption">K Method: You specify exactly 3 clusters.</div>
                                    </div>
                                </div>
                                <h4 class="details-heading">Details</h4>
                                <ul class="details-list">
                                    <li><strong>Elbow</strong>: Automatically finds the "knee" in the cost curve points of diminishing returns.</li>
                                    <li><strong>Stability</strong>: Finds clusters that persist over a wide range of parameter scales (resembles HDBSCAN).</li>
                                    <li><strong>QCoverage</strong>: Optimizes trade-off between coverage and separation.</li>
                                    <li><strong>Silhouette</strong>: Maximizes the Silhouette distance mathematically to partition.</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <!-- Card 4: Metrics Summary -->
                    <div class="framework-card active">
                        <div class="framework-card-header">
                            <div>
                                <div class="framework-icon">📊</div>
                                <h3 class="framework-title">Metrics & Scores</h3>
                                <p class="framework-description">
                                    How cluster quality is evaluated.
                                </p>
                            </div>
                        </div>
                        <div class="details-content" style="max-height: fit-content; opacity: 1;">
                            <div class="details-inner metric-grid">
                                <div class="metric-block">
                                    <h4>Silhouette Score</h4>
                                    <p>Measures how similar an object is to its own cluster compared to other clusters. Ranges from -1 to 1.</p>
                                    <div class="metric-scale">
                                        <span class="scale-bad">-1</span>
                                        <div class="scale-bar silhouette-bar"></div>
                                        <span class="scale-good">+1</span>
                                    </div>
                                    <small><strong>High value:</strong> Dense & well-separated clusters.</small>
                                </div>
                                <div class="metric-block">
                                    <h4>Davies-Bouldin Index</h4>
                                    <p>Computes ratio of within-cluster distances to between-cluster distances.</p>
                                    <div class="metric-scale">
                                        <span class="scale-good">0</span>
                                        <div class="scale-bar db-bar"></div>
                                        <span class="scale-bad">Higher</span>
                                    </div>
                                    <small><strong>Low value:</strong> Better clustering (closer to 0 is better).</small>
                                </div>
                                <div class="metric-block">
                                    <h4>Calinski-Harabasz Score</h4>
                                    <p>Variance Ratio Criterion. Ratio of dispersion between clusters vs dispersion within clusters.</p>
                                    <div class="metric-scale">
                                        <span class="scale-bad">0</span>
                                        <div class="scale-bar ch-bar"></div>
                                        <span class="scale-good">Higher</span>
                                    </div>
                                    <small><strong>High value:</strong> Dense & well-separated clusters.</small>
                                </div>
                                <div class="metric-block">
                                    <h4>Adjusted Rand Index (ARI)</h4>
                                    <p>Compares predicted clusters with Ground Truth labels, correcting for chance.</p>
                                    <div class="metric-scale">
                                        <span class="scale-bad">0</span>
                                        <div class="scale-bar ari-bar"></div>
                                        <span class="scale-good">1</span>
                                    </div>
                                    <small><strong>Value 1.0:</strong> Perfect match with ground truth.</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </main>
      </div>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';

onMounted(() => {
    initializeInteractiveDemos();
});

function initializeInteractiveDemos() {
    initTreeTypeDemo();
    initPowerParameterDemo();
    initPartitionMethodDemo();
}

// Tree Type Demo
function initTreeTypeDemo() {
    const canvas = document.getElementById('tree-demo-canvas') as HTMLCanvasElement;
    const caption = document.getElementById('tree-demo-caption');
    const buttons = document.querySelectorAll('.tree-btn');
    if (!canvas || !caption) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Generate sample data points
    const points = [
        {x: 100, y: 80, cluster: 0}, {x: 120, y: 90, cluster: 0}, {x: 110, y: 100, cluster: 0},
        {x: 280, y: 70, cluster: 1}, {x: 300, y: 85, cluster: 1}, {x: 290, y: 95, cluster: 1},
        {x: 200, y: 180, cluster: 2}, {x: 220, y: 190, cluster: 2}, {x: 210, y: 200, cluster: 2}
    ];
    const colors = ['#3b82f6', '#10b981', '#f97316'];
    
    function drawTreeDemo(treeType: string) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        points.forEach(point => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
            ctx.fillStyle = colors[point.cluster];
            ctx.fill();
            ctx.strokeStyle = '#1f2937';
            ctx.lineWidth = 1;
            ctx.stroke();
        });
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 2;
        
        if (treeType === 'dctree') {
            for (let i = 0; i < points.length; i++) {
                for (let j = i + 1; j < points.length; j++) {
                    const dist = Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y);
                    if (dist < 50) {
                        ctx.beginPath(); ctx.moveTo(points[i].x, points[i].y); ctx.lineTo(points[j].x, points[j].y); ctx.stroke();
                    }
                }
            }
            caption.textContent = 'DCTree: Builds density-based connections between nearby points.';
        } else if (treeType === 'covertree') {
            ctx.strokeStyle = '#10b981'; ctx.setLineDash([5, 5]); ctx.lineWidth = 2;
            [[150, 120, 80], [250, 150, 70]].forEach(([x, y, r]) => { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke(); });
            ctx.strokeStyle = '#059669';
            [[110, 90, 35], [290, 80, 25], [210, 190, 30]].forEach(([x, y, r]) => { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke(); });
            ctx.setLineDash([]);
            caption.textContent = 'CoverTree: Uses hierarchical nested spheres that adapt to metric spaces.';
        } else if (treeType === 'balltree') {
            ctx.strokeStyle = '#f97316'; ctx.setLineDash([3, 3]); ctx.lineWidth = 2;
            [[110, 90, 35], [290, 80, 25], [210, 190, 30]].forEach(([x, y, r]) => { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke(); });
            ctx.setLineDash([]);
            caption.textContent = 'BallTree: Recursively partitions space into intersecting hyperspheres.';
        } else if (treeType === 'kdtree') {
            ctx.strokeStyle = '#8b5cf6'; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(200, 50); ctx.lineTo(200, 200); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(50, 140); ctx.lineTo(200, 140); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(200, 120); ctx.lineTo(350, 120); ctx.stroke();
            caption.textContent = 'KDTree: Axis-aligned splits. Efficient in lower dimensional spaces.';
        } else if (treeType === 'rtree') {
            ctx.strokeStyle = '#ec4899'; ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
            ctx.strokeRect(80, 70, 60, 60); ctx.strokeRect(270, 60, 60, 60); ctx.strokeRect(180, 160, 60, 60);
            ctx.strokeStyle = '#be185d';
            ctx.strokeRect(85, 75, 25, 25); ctx.strokeRect(275, 65, 25, 25); ctx.strokeRect(185, 165, 25, 25);
            ctx.setLineDash([]);
            caption.textContent = 'RTree: Organizes data by minimum bounding rectangles.';
        }
    }
    
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            button.classList.add('active');
            drawTreeDemo(button.getAttribute('data-tree') || 'dctree');
        });
    });
    drawTreeDemo('dctree');
}

// Power Parameter Demo
function initPowerParameterDemo() {
    const canvas = document.getElementById('power-demo-canvas') as HTMLCanvasElement;
    const caption = document.getElementById('power-demo-caption');
    const slider = document.getElementById('power-slider') as HTMLInputElement;
    const valueSpan = document.getElementById('power-value');
    if (!canvas || !caption || !slider || !valueSpan) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const points = [
        {x: 85, y: 105, id: 'blue1'}, {x: 95, y: 115, id: 'blue2'}, {x: 80, y: 120, id: 'blue3'},
        {x: 315, y: 95, id: 'green1'}, {x: 305, y: 105, id: 'green2'}, {x: 320, y: 110, id: 'green3'},
        {x: 130, y: 120, id: 'demo'}, {x: 200, y: 110, id: 'demo'}, {x: 270, y: 120, id: 'demo'},
        {x: 150, y: 140, id: 'border'}, {x: 250, y: 130, id: 'border'},
        {x: 200, y: 160, id: 'far'}, {x: 180, y: 80, id: 'far'}
    ];
    
    function drawPowerDemo(power: number) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const centers = [
            {x: 90, y: 110, color: '#3b82f6', label: 'Center A'},
            {x: 310, y: 100, color: '#10b981', label: 'Center B'}
        ];
        
        const threshold = power === 0 ? 100 : Math.max(20, 60 - power * 4);
        const assignments = points.map(p => {
            const d0 = Math.hypot(p.x - centers[0].x, p.y - centers[0].y);
            const d1 = Math.hypot(p.x - centers[1].x, p.y - centers[1].y);
            let closest = d0 < d1 ? 0 : 1;
            let d = d0 < d1 ? d0 : d1;
            return d > threshold ? -1 : closest;
        });
        
        centers.forEach(center => {
            ctx.beginPath();
            ctx.arc(center.x, center.y, threshold, 0, Math.PI * 2);
            ctx.strokeStyle = center.color;
            ctx.setLineDash([8, 8]);
            ctx.lineWidth = 2;
            ctx.globalAlpha = 0.3;
            ctx.stroke();
            ctx.globalAlpha = 1;
            ctx.setLineDash([]);
        });
        
        points.forEach((p, i) => {
            if (assignments[i] >= 0) {
                ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(centers[assignments[i]].x, centers[assignments[i]].y);
                ctx.strokeStyle = centers[assignments[i]].color; ctx.globalAlpha = 0.4; ctx.stroke(); ctx.globalAlpha = 1;
            }
        });
        
        points.forEach((p, i) => {
            const c = assignments[i] === -1 ? '#ef4444' : centers[assignments[i]].color;
            ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, Math.PI * 2); ctx.fillStyle = c; ctx.fill();
            ctx.strokeStyle = '#1f2937'; ctx.lineWidth = 1; ctx.stroke();
        });
        
        centers.forEach(center => {
            ctx.beginPath(); ctx.arc(center.x, center.y, 8, 0, Math.PI * 2); ctx.fillStyle = center.color; ctx.fill();
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
        });
        
        if(power === 0) caption.textContent = `Power = ${power}: Very loose restrictions. Long chains possible.`;
        else if(power <= 2) caption.textContent = `Power = ${power}: Standard k-Means penalty. Balanced.`;
        else caption.textContent = `Power = ${power}: High penalty. Outliers emerge as threshold tightens.`;
    }
    
    slider.addEventListener('input', () => {
        const p = parseInt(slider.value);
        valueSpan.textContent = p.toString();
        drawPowerDemo(p);
    });
    drawPowerDemo(2);
}

// Partition Demo
function initPartitionMethodDemo() {
    const canvas = document.getElementById('partition-demo-canvas') as HTMLCanvasElement;
    const caption = document.getElementById('partition-demo-caption');
    const buttons = document.querySelectorAll('.partition-btn');
    if (!canvas || !caption) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    function drawPartitionDemo(method: string) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (method === 'k') {
            ctx.fillStyle = '#1f2937'; ctx.font = '16px Inter, sans-serif'; ctx.textAlign = 'center';
            ctx.fillText('Manual K Selection', 200, 120);
            caption.textContent = 'K Method: Hard-code the exact amount of clusters.';
        } else if (method === 'elbow') {
            const data = [{x: 80, y: 70}, {x: 120, y: 90}, {x: 160, y: 110}, {x: 200, y: 120}, {x: 240, y: 125}, {x: 280, y: 128}];
            ctx.beginPath(); ctx.moveTo(50, 180); ctx.lineTo(350, 180); ctx.moveTo(50, 50); ctx.lineTo(50, 180); ctx.stroke();
            ctx.beginPath(); data.forEach((p,i)=> i===0?ctx.moveTo(p.x,p.y):ctx.lineTo(p.x,p.y)); ctx.strokeStyle='#3b82f6'; ctx.stroke();
            data.forEach((p,i)=>{ ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, Math.PI*2); ctx.fillStyle=i===2?'#ef4444':'#3b82f6'; ctx.fill(); });
            caption.textContent = 'Elbow: Finds the "knee" point in variance reduction.';
        } else if (method === 'stability') {
            ctx.beginPath(); ctx.moveTo(50, 180); ctx.lineTo(350, 180); ctx.moveTo(50, 50); ctx.lineTo(50, 180); ctx.stroke();
            const data = [{x: 80, y: 160}, {x: 120, y: 140}, {x: 160, y: 120}, {x: 200, y: 110}, {x: 240, y: 115}, {x: 280, y: 125}];
            ctx.beginPath(); data.forEach((p,i)=> i===0?ctx.moveTo(p.x,p.y):ctx.lineTo(p.x,p.y)); ctx.strokeStyle='#10b981'; ctx.lineWidth=3; ctx.stroke();
            caption.textContent = 'Stability: Searches for the longest-lasting branches over thresholds.';
        } else if (method === 'qcoverage') {
            ctx.fillStyle = '#1f2937'; ctx.font = '16px Inter, sans-serif'; ctx.textAlign = 'center';
            ctx.fillText('Optimizes quality over distance parameters', 200, 120);
            caption.textContent = 'QCoverage: Optimally maximizes within-cluster quality.';
        } else if (method === 'silhouette') {
            ctx.fillStyle = '#1f2937'; ctx.font = '16px Inter, sans-serif'; ctx.textAlign = 'center';
            ctx.fillText('Maximizes generalized Silhouette Index', 200, 120);
            caption.textContent = 'Silhouette: Selects K that maximizes cluster density & separation.';
        }
    }
    
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            button.classList.add('active');
            drawPartitionDemo(button.getAttribute('data-method') || 'k');
        });
    });
    drawPartitionDemo('k');
}
</script>

<style scoped>
.explanation-page {
    background: #f8fafc;
    min-height: 100vh;
}
.hero-gradient {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    color: white;
    padding: 3rem 1rem;
    text-align: center;
}
.hero-title { font-size: 2.5rem; font-weight: 800; margin-bottom: 1rem; }
.hero-subtitle-lead { font-size: 1.25rem; color: #38bdf8; font-weight: 600; }
.hero-subtitle-main { max-width: 600px; margin: 1rem auto; color: #cbd5e1; }

.main-content {
    max-width: 1000px;
    margin: 3rem auto;
    padding: 0 1rem;
}
.section-title { font-size: 1.8rem; margin-bottom: 2rem; color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }

.framework-grid {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}
.framework-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0;
    overflow: hidden;
}
.framework-card-header {
    background: #f1f5f9;
    padding: 1.5rem;
    border-bottom: 1px solid #e2e8f0;
}
.framework-icon { font-size: 2rem; margin-bottom: 0.5rem; }
.framework-title { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin: 0; }
.framework-description { color: #64748b; margin-top: 0.25rem; font-size: 0.95rem; }

.details-content { padding: 1.5rem; }
.details-text { color: #334155; margin-bottom: 1.5rem; line-height: 1.6; }

.interactive-demo {
    background: #f8fafc;
    padding: 1.5rem;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    margin-bottom: 1.5rem;
}
.demo-heading { font-weight: 600; color: #1e293b; margin-bottom: 0.5rem; margin-top:0;}
.demo-description { color: #64748b; font-size: 0.9rem; margin-bottom: 1rem; }

.tree-selector, .partition-selector { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
.tree-btn, .partition-btn {
    padding: 0.4rem 0.8rem; border-radius: 4px; border: 1px solid #cbd5e1; background: white;
    cursor: pointer; font-size: 0.85rem; font-weight: 500; color: #475569; transition: all 0.2s;
}
.tree-btn:hover, .partition-btn:hover { background: #f1f5f9; }
.tree-btn.active, .partition-btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }

.demo-canvas-container {
    background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.demo-caption { margin-top: 1rem; font-size: 0.85rem; color: #64748b; text-align: center; }

.power-controls { margin-bottom: 1.5rem; }
.power-controls label { font-weight: 600; color: #1e293b; display: block; margin-bottom: 0.5rem; }
.power-slider { width: 100%; margin: 1rem 0; }
.power-labels { display: flex; justify-content: space-between; font-size: 0.75rem; color: #64748b; }

.details-heading { font-size: 1.1rem; color: #1e293b; margin: 1.5rem 0 0.75rem 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.25rem; }
.details-list { padding-left: 1.5rem; color: #334155; line-height: 1.6; }
.details-list li { margin-bottom: 0.5rem; }

/* Metrics */
.metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; }
.metric-block { background: #f8fafc; border: 1px solid #e2e8f0; padding: 1.25rem; border-radius: 8px; }
.metric-block h4 { margin-top: 0; color: #0f172a; margin-bottom: 0.5rem; }
.metric-block p { font-size: 0.9rem; color: #475569; margin-bottom: 1rem; line-height: 1.4; }
.metric-scale { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.scale-bar { flex: 1; height: 8px; border-radius: 4px; }
.silhouette-bar { background: linear-gradient(to right, #ef4444, #eab308, #22c55e); }
.db-bar { background: linear-gradient(to right, #22c55e, #eab308, #ef4444); }
.ch-bar { background: linear-gradient(to right, #ef4444, #eab308, #22c55e); }
.ari-bar { background: linear-gradient(to right, #ef4444, #eab308, #22c55e); }
.scale-good { color: #16a34a; font-size: 0.75rem; font-weight: bold; }
.scale-bad { color: #dc2626; font-size: 0.75rem; font-weight: bold; }
.metric-block small { display: block; margin-top: 0.5rem; color: #64748b; }

</style>
