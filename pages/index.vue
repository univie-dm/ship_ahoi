<template>
  <AppLayout :showSidebar="false" :showNavbar="false">
    <template #default>
      <div class="index-page">
        <!-- Hero Section with Interactive Animation -->
        <header class="hero-gradient">
            <div class="container hero-container">
                <div class="hero-content">
                    <h1 class="hero-title">SHIP.AHOI</h1>
                    <p class="hero-subtitle-lead">Interactive Clustering at the Speed of Thought</p>
                    <p class="hero-subtitle-main">
                        SHIP.AHOI transforms clustering from a trial-and-error process into an interactive exploration. 
                        Powered by the <strong>SHIP</strong> (Similarity-Hierarchy-Partition) framework, it separates the heavy lifting of analyzing data structure from the creative process of defining clusters. 
                        Compute the underlying similarity model once, then generate, visualize, and compare thousands of optimal clustering solutions in milliseconds.
                    </p>
                    
                    <!-- Research Paper Link -->
                    <div class="paper-link-container">
                        <a href="https://arxiv.org/abs/2502.14018" target="_blank" rel="noopener noreferrer" class="paper-link">
                            <div class="paper-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                </svg>
                            </div>
                            <div class="paper-content">
                                <span class="paper-title">Read the Research Paper</span>
                                <span class="paper-subtitle">arXiv:2502.14018 - "I Want 'Em All (At Once)"</span>
                            </div>
                            <div class="paper-arrow">&rarr;</div>
                        </a>
                    </div>
                    
                    <!-- Interactive SHIP Framework Visualization -->
                    <div class="animation-container">
                         <canvas id="ship-animation-canvas" width="540" height="300"></canvas>
                         <p id="animation-caption" class="animation-caption">Click to see the SHIP framework in action!</p>
                    </div>
                </div>
            </div>
        </header>

        <main class="container main-content">
            <!-- Benefits Section -->
            <section id="benefits" class="benefits-section">
                <h2 class="section-title">The SHIP Advantage</h2>
                <p class="section-subtitle">
                    Most algorithms run from scratch every time you change a parameter. SHIP is different.
                </p>
                <div class="benefits-grid">
                    <div class="benefit-card">
                        <div class="benefit-icon">⚡</div>
                        <h3 class="benefit-title">Instant Re-Clustering</h3>
                        <p class="benefit-description">Perform the expensive distance calculation only once to build a similarity tree. After that, finding solutions for any number of clusters (k) or changing objective functions is effectively instantaneous.</p>
                    </div>
                    <div class="benefit-card">
                        <div class="benefit-icon">🔭</div>
                        <h3 class="benefit-title">True Exploration</h3>
                        <p class="benefit-description">Don't settle for the first result. Effortlessly switch between different mathematical "lenses"—from density-based connectivity to variance-based compactness—to find the structure that matters.</p>
                    </div>
                    <div class="benefit-card">
                        <div class="benefit-icon">🧩</div>
                        <h3 class="benefit-title">Unifies Algorithms</h3>
                        <p class="benefit-description">SHIP unifies distinct methods. By adjusting the tree type and power parameter, you can replicate the behavior of DBSCAN, k-Means, and Single-Linkage clustering within one consistent framework.</p>
                    </div>
                      <div class="benefit-card">
                        <div class="benefit-icon">📐</div>
                        <h3 class="benefit-title">Guaranteed Optimality</h3>
                        <p class="benefit-description">Within the constructed ultrametric space, SHIP provides provably optimal solutions for center-based objectives. This removes the approximation errors and initialization bias (like k-Means seeds) found in heuristics.</p>
                    </div>
                </div>
            </section>

            <!-- The SHIP Framework Section -->
            <section id="framework">
                <h2 class="section-title">The 3 Steps of SHIP</h2>
                <p class="section-subtitle">
                    A modular pipeline that separates structure from interpretation.
                </p>
                <div class="framework-grid">
                    <!-- Card 1: Similarity -->
                    <div class="framework-card">
                        <div class="framework-card-header">
                            <div>
                                <div class="framework-icon">1</div>
                                <h3 class="framework-title">Similarity (The Map)</h3>
                                <p class="framework-description">
                                    We model the data's intrinsic structure by constructing a <strong>Similarity Tree</strong> (Ultrametric). This acts as a static map of your data's density and geometry.
                                </p>
                            </div>
                            <svg class="chevron-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                        <div class="details-content">
                            <div class="details-inner">
                                <p class="details-text">This is the only computationally expensive step. We translate pairwise distances into a hierarchical tree (an Ultrametric). Different tree types capture different aspects of the data: <strong>DCTree</strong> captures density-connectivity (like DBSCAN), while <strong>CoverTree</strong> or <strong>KDTree</strong> capture spatial proximity.</p>
                                
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
                                
                                <h4 class="details-heading">Key Tree Types</h4>
                                <div class="details-methods">
                                    <div><span class="method-tag">DCTree (Density-Connectivity)</span><p class="method-description">The most powerful option for complex data. It connects points based on local density, unifying concepts from DBSCAN and Spectral Clustering.</p></div>
                                    <div><span class="method-tag">CoverTree / BallTree</span><p class="method-description">Spatial partitioning trees. Good for high-dimensional data and identifying compact, spherical clusters.</p></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <!-- Card 2: Hierarchy -->
                    <div class="framework-card">
                         <div class="framework-card-header">
                            <div>
                                <div class="framework-icon">2</div>
                                <h3 class="framework-title">Hierarchy (The Lens)</h3>
                                <p class="framework-description">
                                    We generate a cluster hierarchy by applying an objective function (the <strong>Power Parameter</strong>). This acts as a lens, determining what constitutes a "good" cluster.
                                </p>
                            </div>
                            <svg class="chevron-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                        <div class="details-content">
                            <div class="details-inner">
                                <p class="details-text">From the single Similarity Tree, we can instantly derive different hierarchies by changing the Power Parameter (z). This parameter controls how we penalize distances. Low values prioritize connectivity (chain-like clusters), while high values prioritize compactness (round clusters).</p>
                                
                                <!-- Interactive Power Parameter Visualization -->
                                <div class="interactive-demo">
                                    <h4 class="demo-heading">Power Parameter controls Compactness</h4>
                                    <p class="demo-description">Adjust the power to change the clustering objective:</p>
                                    
                                    <div class="power-controls">
                                        <label for="power-slider">Power Parameter: <span id="power-value">2</span></label>
                                        <input type="range" id="power-slider" min="2" max="6" step="2" value="2" class="power-slider">
                                        <div class="power-labels">
                                            <span>2 (Balanced)</span>
                                            <span>4 (Tight)</span>
                                            <span>6 (Very Tight)</span>
                                        </div>
                                    </div>
                                    
                                    <div class="demo-canvas-container">
                                        <canvas id="power-demo-canvas" width="400" height="250"></canvas>
                                        <div class="demo-caption" id="power-demo-caption">Power = 2: Standard k-Means objective. Balanced compactness.</div>
                                    </div>
                                </div>
                                
                                <h4 class="details-heading">Objective Functions</h4>
                                <div class="details-methods">
                                    <div><span class="method-tag">Power ≈ 0 (k-Center)</span><p class="method-description">Minimizes the maximum distance. Great for finding connected components and continuous shapes.</p></div>
                                    <div><span class="method-tag">Power = 1 (k-Median)</span><p class="method-description">Minimizes the sum of distances. Robust average, less sensitive to outliers than k-means.</p></div>
                                    <div><span class="method-tag">Power = 2 (k-Means)</span><p class="method-description">Minimizes squared distances. The standard for finding compact, spherical clusters.</p></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <!-- Card 3: Partition -->
                    <div class="framework-card">
                         <div class="framework-card-header">
                            <div>
                                <div class="framework-icon">3</div>
                                <h3 class="framework-title">Partition (The Solution)</h3>
                                <p class="framework-description">
                                    Finally, we <strong>Partition</strong> the hierarchy to extract the final clusters. You can choose specific numbers or let algorithms find the natural structure.
                                </p>
                            </div>
                            <svg class="chevron-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                        <div class="details-content">
                             <div class="details-inner">
                                <p class="details-text">A hierarchy contains every possible clustering from 1 to N clusters. The Partition step "cuts" this hierarchy. You can cut manually (selecting K) or use smart algorithms that analyze the cost curve to find the mathematical "sweet spot" or the most stable structures.</p>
                                
                                <!-- Interactive Partition Method Visualization -->
                                <div class="interactive-demo">
                                    <h4 class="demo-heading">Smart Partitioning</h4>
                                    <p class="demo-description">How do we decide where to cut the tree?</p>
                                    
                                    <div class="partition-selector">
                                        <button class="partition-btn active" data-method="k">K (Manual)</button>
                                        <button class="partition-btn" data-method="elbow">Elbow</button>
                                        <button class="partition-btn" data-method="stability">Stability</button>
                                        <button class="partition-btn" data-method="qcoverage">QCoverage</button>
                                    </div>
                                    
                                    <div class="demo-canvas-container">
                                        <canvas id="partition-demo-canvas" width="400" height="250"></canvas>
                                        <div class="demo-caption" id="partition-demo-caption">K Method: You specify exactly 3 clusters - direct control.</div>
                                    </div>
                                </div>
                                
                                <h4 class="details-heading">Partition Strategies</h4>
                                 <div class="details-methods">
                                    <div><span class="method-tag">Elbow Method</span><p class="method-description">Automatically finds the "knee" in the cost curve—the point of diminishing returns.</p></div>
                                    <div><span class="method-tag">Stability</span><p class="method-description">Finds clusters that persist over a wide range of scales (similar to HDBSCAN). Robust against noise.</p></div>
                                    <div><span class="method-tag">Manual K</span><p class="method-description">Precision control. Because SHIP is fast, you can scroll through K=2 to K=50 in seconds to see how the data breaks down.</p></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Icicle Plot Explanation Section -->
            <section id="icicle-explanation" class="icicle-explanation-section">
                <div class="icicle-collapse" data-collapsible>
                    <button
                      class="icicle-collapse-header"
                      type="button"
                      aria-expanded="false"
                      data-collapsible-trigger
                    >
                        <div class="icicle-header-text">
                            <h2 class="section-title icicle-collapse-title">Visualizing Hierarchies: The Icicle Plot</h2>
                            <p class="section-subtitle icicle-collapse-subtitle">
                                We use Icicle plots to visualize the "DNA" of your clusters—showing how big groups break down into smaller ones.
                            </p>
                        </div>
                        <svg class="icicle-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                    </button>

                    <div class="details-content icicle-collapse-content" data-collapsible-content>
                        <div class="details-inner">
                            <div class="icicle-demo-container">
                                <div class="icicle-explanation-full">
                                    <h3 class="demo-title">How to Read an Icicle Plot</h3>
                                    <div class="explanation-grid">
                                        <div class="explanation-item">
                                            <span class="feature-highlight">Top-Down</span> The top bar is the whole dataset. Lower bars are sub-clusters.
                                        </div>
                                        <div class="explanation-item">
                                            <span class="feature-highlight">Width = Size</span> The wider the bar, the more data points are in that cluster.
                                        </div>
                                        <div class="explanation-item">
                                            <span class="feature-highlight">Color</span> Indicates cluster membership in the current partition.
                                        </div>
                                        <div class="explanation-item">
                                            <span class="feature-highlight">Structure</span> Immediately see if clusters are balanced or if one dominates.
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="icicle-demo">
                                    <h4 class="demo-heading">Icicle Plot vs. Dendrogram</h4>
                                    <p class="demo-description">The Icicle plot is more space-efficient for showing cluster proportions:</p>
                                    
                                    <div class="dual-canvas-container">
                                        <div class="canvas-section">
                                            <h5 class="canvas-title">Icicle Plot</h5>
                                            <canvas id="icicle-canvas" width="450" height="350"></canvas>
                                            <div class="canvas-subtitle">Clear view of cluster proportions</div>
                                        </div>
                                        
                                        <div class="canvas-section">
                                            <h5 class="canvas-title">Dendrogram</h5>
                                            <canvas id="dendrogram-canvas" width="450" height="350"></canvas>
                                            <div class="canvas-subtitle">Classic view of merge distances</div>
                                        </div>
                                    </div>
                                    
                                    <div class="demo-caption" id="comparison-caption">Compare how the same hierarchical data looks in both visualization types</div>
                                </div>
                                
                                <div class="icicle-notice">
                                    <div class="notice-content">
                                        <span class="notice-icon">💡</span>
                                        <div class="notice-text">
                                            <strong>Pro Tip:</strong> Use the Icicle plot to spot <em>imbalanced clustering</em>. If you see one huge bar and many tiny slivers, your algorithm might be chaining noise points instead of finding groups.
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

             <!-- Action Buttons Section -->
            <section class="action-buttons-section">
                 <h2 class="section-title">Ready to Explore?</h2>
                 <p class="section-subtitle">Jump right in. No code required.</p>
                 <div class="action-buttons-container">
                    <button @click="goToDataUpload" class="action-button primary">Upload Data</button>
                    <button @click="startOnboarding" class="action-button">Start Guided Setup</button>
                    <button @click="startQuickDemo" class="action-button">Load Demo Dataset</button>
                 </div>
            </section>
        </main>
        
        <!-- Footer -->
        <footer class="page-footer">
          <div class="container">
            <div class="footer-content">
              <p class="creator-credit">Created by </p>
            </div>
          </div>
        </footer>
      </div>

      <!-- Onboarding Wizard Modal -->
      <OnboardingWizard 
        v-if="showOnboardingWizard"
        @close="closeOnboardingWizard"
      />
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useGlobalState } from '~/composables/useGlobalState';
import { useStudySession } from '~/composables/useStudySession';
import OnboardingWizard from '~/components/onboarding/OnboardingWizard.vue';

const router = useRouter();
const globalState = useGlobalState();
const studySession = useStudySession();

// Onboarding wizard state
const showOnboardingWizard = ref(false);

// Computed properties
const isReturningUser = computed(() => {
  return globalState.currentDataset.value !== null || globalState.recentRuns.value.length > 0;
});

const currentDatasetName = computed(() => {
  if (globalState.currentDataset.value) {
    return globalState.currentDataset.value.name || 'Current Dataset';
  }
  return 'Previous Dataset';
});

// Navigation methods
const continueToAnalysis = () => {
  router.push('/clustering');
};

const startNewAnalysis = () => {
  // Clear current state
  globalState.clearCurrentDataset();
  router.push('/data-upload');
};

const startOnboarding = () => {
  // Start study session
  studySession.startSession();

  // Clear any existing onboarding session storage to ensure fresh start
  sessionStorage.removeItem('onboardingInProgress');
  sessionStorage.removeItem('onboardingStep');
  sessionStorage.removeItem('onboardingExperienceLevel');
  sessionStorage.removeItem('returningFromDataUpload');
  
  // Always use beginner mode - go directly to data upload
  sessionStorage.setItem('onboardingInProgress', 'true');
  sessionStorage.setItem('onboardingStep', 'questions');
  sessionStorage.setItem('onboardingExperienceLevel', 'beginner');
  
  // Navigate directly to data upload page
  router.push('/data-upload?from=onboarding');
};

const goToDataUpload = () => {
  router.push('/data-upload');
};

const startQuickDemo = () => {
  // Set up a default sample dataset and go directly to clustering
  const dimensions = 2;
  const headers = Array.from({ length: dimensions }, (_, i) => `Feature ${i + 1}`);
  
  globalState.setDataset({
    name: 'Blobs',
    type: 'sample',
    sampleName: 'blobs',
    n_samples: 1000,
    headers,
    featureCount: dimensions
  });
  
  // Set reasonable default parameters for demo
  globalState.setClusteringParameters({
    treeType: 'MST',
    partitionMethod: 'SILHOUETTE',
    power: 2,
    k: 5
  });
  
  // Mark onboarding as completed and go to clustering
  globalState.setOnboardingCompleted(true);
  router.push('/clustering');
};

const closeOnboardingWizard = () => {
  showOnboardingWizard.value = false;
};

// Auto-redirect for returning users and handle onboarding returns
onMounted(() => {
  // Check if returning from data upload during onboarding
  const isReturningFromUpload = sessionStorage.getItem('returningFromDataUpload') === 'true';
  const onboardingInProgress = sessionStorage.getItem('onboardingInProgress') === 'true';
  const onboardingStep = sessionStorage.getItem('onboardingStep');
  
  if (isReturningFromUpload && onboardingInProgress) {
    // Clear the return flag but keep onboarding state for the wizard
    sessionStorage.removeItem('returningFromDataUpload');
    
    // Show the onboarding wizard to continue from parameter selection
    showOnboardingWizard.value = true;
    console.log('Returning from data upload - resuming onboarding wizard');
    return;
  }
  
  // Regular returning user logic
  if (isReturningUser.value && globalState.currentDataset.value) {
    // Optional: Auto-redirect after a delay
    // setTimeout(() => {
    //    continueToAnalysis();
    // }, 3000);
  }
  
  // --- Interactive SHIP Animation ---
    const canvas = document.getElementById('ship-animation-canvas') as HTMLCanvasElement;
    const caption = document.getElementById('animation-caption');
    if (!canvas || !caption) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    let points: any[] = [];
    const baseColors = ['#3b82f6', '#10b981', '#f97316', '#8b5cf6'];
    const defaultColor = '#94a3b8';
    let stage = 0;
    let mstEdges: any[] = [];

    function generatePoints() {
        points = [];
        const clusters = [
            { x: width * 0.25, y: height * 0.3, count: 15 },
            { x: width * 0.75, y: height * 0.3, count: 15 },
            { x: width * 0.5, y: height * 0.75, count: 20 },
            { x: width * 0.8, y: height * 0.7, count: 10 }
        ];
        clusters.forEach((cluster, i) => {
            for (let j = 0; j < cluster.count; j++) {
                points.push({
                    id: points.length,
                    x: cluster.x + (Math.random() - 0.5) * width * 0.25,
                    y: cluster.y + (Math.random() - 0.5) * height * 0.3,
                    color: defaultColor,
                    targetColor: baseColors[i % baseColors.length],
                    cluster: i
                });
            }
        });
    }

    function findMST() {
        if (points.length === 0) return [];
        let edges = [];
        let visited = new Set();
        let pq = [{p1: 0, p2: -1, dist: 0}];
        let connections = new Array(points.length).fill(-1);

        while(pq.length > 0 && visited.size < points.length) {
            pq.sort((a,b) => a.dist - b.dist);
            const current = pq.shift();
            if(!current || visited.has(current.p1)) continue;
            
            visited.add(current.p1);
            if(current.p2 !== -1) {
                 edges.push({p1: points[current.p1], p2: points[current.p2]});
            }

            for(let i = 0; i < points.length; i++) {
                if(!visited.has(i)) {
                    const d = Math.hypot(points[current.p1].x - points[i].x, points[current.p1].y - points[i].y);
                    pq.push({p1: i, p2: current.p1, dist: d});
                }
            }
        }
        return edges;
    }

    function draw(progress: number, drawFunc: (progress: number) => void) {
        ctx.clearRect(0, 0, width, height);
        drawFunc(progress);
    }
    
    const drawPointsOnly = () => {
         points.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.fill();
        });
    }

    const drawSimilarity = (progress: number) => {
        drawPointsOnly();
        ctx.strokeStyle = '#cbd5e0';
        ctx.lineWidth = 1.5;
        const edgesToDraw = Math.floor(mstEdges.length * progress);
        for(let i = 0; i < edgesToDraw; i++) {
            const edge = mstEdges[i];
            ctx.beginPath();
            ctx.moveTo(edge.p1.x, edge.p1.y);
            ctx.lineTo(edge.p2.x, edge.p2.y);
            ctx.stroke();
        }
    }
    
    const drawHierarchy = (progress: number) => {
        // Points are static, so we just draw the full MST
        drawSimilarity(1);
        drawPointsOnly();
    }

    const drawPartition = (progress: number) => {
         points.forEach(p => {
            const r1 = 148, g1 = 163, b1 = 184; // slate-400
            const r2 = parseInt(p.targetColor.slice(1,3), 16), g2 = parseInt(p.targetColor.slice(3,5), 16), b2 = parseInt(p.targetColor.slice(5,7), 16);
            const r = Math.round(r1 + (r2 - r1) * progress);
            const g = Math.round(g1 + (g2 - g1) * progress);
            const b = Math.round(b1 + (b2 - b1) * progress);
            p.color = `rgb(${r},${g},${b})`;
        });
        drawSimilarity(1); // Keep MST visible
        drawPointsOnly();
    }

    const drawPartitionSwitching = (progress: number) => {
        // Define different partition solutions with more distinct differences
        const partitionSolutions = [
            // Solution 1: All points as one cluster
            {
                colors: ['#3b82f6'],
                assignments: points.map(p => 0),
                label: 'k=1 cluster (All together)'
            },
            // Solution 2: 2 very different clusters (left vs right)
            {
                colors: ['#ef4444', '#10b981'],
                assignments: points.map(p => p.x < width * 0.5 ? 0 : 1),
                label: 'k=2 clusters (Left vs Right)'
            },
            // Solution 3: 3 clusters (top vs bottom split)
            {
                colors: ['#3b82f6', '#f97316', '#8b5cf6'],
                assignments: points.map(p => {
                    if (p.y < height * 0.4) return p.x < width * 0.5 ? 0 : 1;
                    return 2;
                }),
                label: 'k=3 clusters (Top-Left, Top-Right, Bottom)'
            },
            // Solution 4: Original natural clusters
            {
                colors: ['#3b82f6', '#10b981', '#f97316', '#8b5cf6'],
                assignments: points.map(p => p.cluster),
                label: 'k=4 clusters (Natural groups)'
            },
            // Solution 5: 6 clusters (over-segmentation)
            {
                colors: ['#3b82f6', '#10b981', '#f97316', '#8b5cf6', '#ef4444', '#06b6d4'],
                assignments: points.map((p, i) => {
                    // Create more granular splits
                    if (p.cluster === 0) return i % 3 === 0 ? 0 : 4; // Split cluster 0
                    if (p.cluster === 1) return i % 3 === 0 ? 1 : 5; // Split cluster 1
                    return p.cluster; // Keep clusters 2 and 3 as is
                }),
                label: 'k=6 clusters (Over-segmented)'
            }
        ];

        // Calculate which solution to show based on progress (slower transitions)
        const totalSolutions = partitionSolutions.length;
        const solutionDuration = 1 / totalSolutions;
        const currentSolutionIndex = Math.min(Math.floor(progress / solutionDuration), totalSolutions - 1);
        const solutionProgress = (progress % solutionDuration) / solutionDuration;
        
        const currentSolution = partitionSolutions[currentSolutionIndex];
        const nextSolution = partitionSolutions[(currentSolutionIndex + 1) % totalSolutions];
        
        // Slower transitions - show each solution longer before transitioning
        if (solutionProgress < 0.7) {
            // Show current solution for 70% of the time
            points.forEach((p, i) => {
                const clusterIndex = currentSolution.assignments[i];
                p.color = currentSolution.colors[clusterIndex] || '#94a3b8';
            });
        } else {
            // Transition to next solution for 30% of the time (slower transition)
            const transitionProgress = (solutionProgress - 0.7) / 0.3;
            points.forEach((p, i) => {
                const currentClusterIndex = currentSolution.assignments[i];
                const nextClusterIndex = nextSolution.assignments[i];
                
                const currentColor = currentSolution.colors[currentClusterIndex] || '#94a3b8';
                const nextColor = nextSolution.colors[nextClusterIndex] || '#94a3b8';
                
                // Interpolate between colors
                const r1 = parseInt(currentColor.slice(1,3), 16);
                const g1 = parseInt(currentColor.slice(3,5), 16);
                const b1 = parseInt(currentColor.slice(5,7), 16);
                const r2 = parseInt(nextColor.slice(1,3), 16);
                const g2 = parseInt(nextColor.slice(3,5), 16);
                const b2 = parseInt(nextColor.slice(5,7), 16);
                
                const r = Math.round(r1 + (r2 - r1) * transitionProgress);
                const g = Math.round(g1 + (g2 - g1) * transitionProgress);
                const b = Math.round(b1 + (b2 - b1) * transitionProgress);
                
                p.color = `rgb(${r},${g},${b})`;
            });
        }
        
        // Draw the visualization
        drawSimilarity(1); // Keep MST visible
        drawPointsOnly();
        
        // Draw solution label
        ctx.fillStyle = '#1f2937';
        ctx.font = 'bold 16px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(currentSolution.label, width / 2, 25);
        
        // Draw progress indicator
        const indicatorY = height - 20;
        const indicatorWidth = width * 0.6;
        const indicatorX = (width - indicatorWidth) / 2;
        
        // Background bar
        ctx.fillStyle = '#e5e7eb';
        ctx.fillRect(indicatorX, indicatorY, indicatorWidth, 4);
        
        // Progress bar
        ctx.fillStyle = '#3b82f6';
        ctx.fillRect(indicatorX, indicatorY, indicatorWidth * progress, 4);
        
        // Solution markers
        for (let i = 0; i < totalSolutions; i++) {
            const markerX = indicatorX + (indicatorWidth * i) / (totalSolutions - 1);
            ctx.beginPath();
            ctx.arc(markerX, indicatorY + 2, 4, 0, Math.PI * 2);
            ctx.fillStyle = i === currentSolutionIndex ? '#3b82f6' : '#9ca3af';
            ctx.fill();
        }
    }

    function animate(drawFunc: (progress: number) => void, duration = 800) {
        let start: number | null = null;
        const step = (timestamp: number) => {
            if (!start) start = timestamp;
            const progress = Math.min((timestamp - start) / duration, 1);
            draw(progress, drawFunc);
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        }
        requestAnimationFrame(step);
    }

    let animationInterval: NodeJS.Timeout;

    function runAnimation() {
        stage = (stage % 5) + 1;
        caption.style.opacity = '0';

        setTimeout(() => {
            switch (stage) {
                case 1:
                    caption.textContent = 'Data points are loaded into the space.';
                    generatePoints();
                    mstEdges = findMST();
                    points.forEach(p => p.color = defaultColor);
                    animate((p) => draw(p, drawPointsOnly), 500);
                    break;
                case 2:
                    caption.textContent = '1. A Similarity Tree is built to model data relationships.';
                    animate(drawSimilarity, 800);
                    break;
                case 3:
                    caption.textContent = '2. A Hierarchy is generated, offering one view of the data.';
                    // Since points are static, we just update the text. The hierarchy is an abstract structure.
                    draw(1, drawHierarchy); // Show full MST
                    break;
                case 4:
                    caption.textContent = '3. A Partition is extracted to form the final clusters.';
                    animate(drawPartition, 800);
                    break;
                case 5:
                    caption.textContent = '4. Switch between different partition solutions instantly!';
                    animate(drawPartitionSwitching, 2000);
                    break;
            }
            caption.style.opacity = '1';
        }, 300);
    }

    function startAutoAnimation() {
        // Clear any existing interval
        if (animationInterval) {
            clearInterval(animationInterval);
        }
        
        // Start the animation immediately
        runAnimation();
        
        // Set up automatic cycling every 3 seconds
        animationInterval = setInterval(runAnimation, 3000);
    }

    function stopAutoAnimation() {
        if (animationInterval) {
            clearInterval(animationInterval);
        }
    }
    
    // Start automatic animation
    startAutoAnimation();
    
    // Allow manual control on click (restarts the auto cycle)
    canvas.addEventListener('click', () => {
        stopAutoAnimation();
        runAnimation();
        // Restart auto animation after manual click
        setTimeout(() => {
            startAutoAnimation();
        }, 3000);
    });

    // --- Accordion Logic ---
    const accordions = document.querySelectorAll('.framework-card-header');
    accordions.forEach(accordion => {
        accordion.addEventListener('click', () => {
            const card = accordion.parentElement;
            const content = accordion.nextElementSibling as HTMLElement;
            const wasActive = card?.classList.contains('active');

            // Optional: Close other accordions
            // accordions.forEach(acc => {
            //      acc.parentElement?.classList.remove('active');
            //      const c = acc.nextElementSibling as HTMLElement;
            //      if (c) c.style.maxHeight = '';
            // });

            if (!wasActive) {
                card?.classList.add('active');
                if (content) {
                    content.style.maxHeight = content.scrollHeight + "px";
                }
            } else {
                 card?.classList.remove('active');
                 if (content) content.style.maxHeight = '';
            }
        });
    });

    // --- Collapsible Sections ---
    const collapsibleSections = document.querySelectorAll('[data-collapsible]');
    collapsibleSections.forEach(section => {
        const trigger = section.querySelector('[data-collapsible-trigger]');
        const content = section.querySelector('[data-collapsible-content]') as HTMLElement | null;

        if (!(trigger instanceof HTMLElement) || !content) {
            return;
        }

        const setExpandedState = (expanded: boolean) => {
            trigger.setAttribute('aria-expanded', String(expanded));
            section.classList.toggle('active', expanded);

            if (expanded) {
                content.style.maxHeight = content.scrollHeight + 'px';
            } else {
                content.style.maxHeight = '';
            }
        };

        trigger.addEventListener('click', () => {
            const isExpanded = trigger.getAttribute('aria-expanded') === 'true';
            setExpandedState(!isExpanded);
        });

        // Ensure collapsed state on load
        setExpandedState(false);
    });

    // --- Interactive Demo Logic ---
    initializeInteractiveDemos();
});

function initializeInteractiveDemos() {
    // Tree Type Demo
    initTreeTypeDemo();
    
    // Power Parameter Demo
    initPowerParameterDemo();
    
    // Partition Method Demo
    initPartitionMethodDemo();
    
    // Icicle Plot Demo
    initIciclePlotDemo();
}

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
        
        // Draw points
        points.forEach(point => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
            ctx.fillStyle = colors[point.cluster];
            ctx.fill();
            ctx.strokeStyle = '#1f2937';
            ctx.lineWidth = 1;
            ctx.stroke();
        });
        
        // Draw connections based on tree type
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 2;
        
        if (treeType === 'dctree') {
            // DCTree: Density-based connections
            drawDCTreeConnections(ctx, points);
            caption.textContent = 'DCTree: Builds density-based connections between nearby points, excellent for varying density clusters';
        } else if (treeType === 'covertree') {
            // CoverTree: Hierarchical spheres
            drawCoverTreeConnections(ctx, points);
            caption.textContent = 'CoverTree: Uses hierarchical nested spheres that adapt to data structure, efficient for high dimensions';
        } else if (treeType === 'balltree') {
            // BallTree: Recursive ball partitioning
            drawBallTreeConnections(ctx, points);
            caption.textContent = 'BallTree: Recursively partitions space with hyperspheres, optimized for fast nearest neighbor queries';
        } else if (treeType === 'kdtree') {
            // KDTree: Axis-aligned partitions
            drawKDTreeConnections(ctx, points);
            caption.textContent = 'KDTree: Recursively splits space along coordinate axes, creating rectangular regions - fast for low dimensions';
        } else if (treeType === 'rtree') {
            // RTree: Minimum bounding rectangles
            drawRTreeConnections(ctx, points);
            caption.textContent = 'RTree: Uses minimum bounding rectangles to organize data hierarchically, optimized for spatial queries';
        }
    }
    
    function drawDCTreeConnections(ctx: CanvasRenderingContext2D, points: any[]) {
        // Connect nearest neighbors within clusters (density-based)
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        for (let i = 0; i < points.length; i++) {
            for (let j = i + 1; j < points.length; j++) {
                const dist = Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y);
                if (dist < 50) {
                    ctx.beginPath();
                    ctx.moveTo(points[i].x, points[i].y);
                    ctx.lineTo(points[j].x, points[j].y);
                    ctx.stroke();
                }
            }
        }
    }
    
    function drawCoverTreeConnections(ctx: CanvasRenderingContext2D, points: any[]) {
        // Draw hierarchical covering spheres
        ctx.strokeStyle = '#10b981';
        ctx.setLineDash([5, 5]);
        ctx.lineWidth = 2;
        
        // Level 1: Large covering spheres
        [[150, 120, 80], [250, 150, 70]].forEach(([x, y, r]) => {
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.stroke();
        });
        
        // Level 2: Smaller covering spheres
        ctx.strokeStyle = '#059669';
        [[110, 90, 35], [290, 80, 25], [210, 190, 30]].forEach(([x, y, r]) => {
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.stroke();
        });
        
        ctx.setLineDash([]);
    }
    
    function drawBallTreeConnections(ctx: CanvasRenderingContext2D, points: any[]) {
        // Draw recursive ball partitions
        ctx.strokeStyle = '#f97316';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 2;
        
        // Hierarchical balls with clear parent-child relationships
        [[110, 90, 35], [290, 80, 25], [210, 190, 30]].forEach(([x, y, r]) => {
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.stroke();
        });
        
        ctx.setLineDash([]);
    }
    
    function drawKDTreeConnections(ctx: CanvasRenderingContext2D, points: any[]) {
        // Draw axis-aligned rectangular partitions
        ctx.strokeStyle = '#8b5cf6';
        ctx.lineWidth = 2;
        
        // Vertical splits
        ctx.beginPath();
        ctx.moveTo(200, 50);
        ctx.lineTo(200, 200);
        ctx.stroke();
        
        // Horizontal splits
        ctx.beginPath();
        ctx.moveTo(50, 140);
        ctx.lineTo(200, 140);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(200, 120);
        ctx.lineTo(350, 120);
        ctx.stroke();
        
        // Draw partition labels
        ctx.fillStyle = '#8b5cf6';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText('X-split', 205, 125);
        ctx.fillText('Y-split', 125, 135);
    }
    
    function drawRTreeConnections(ctx: CanvasRenderingContext2D, points: any[]) {
        // Draw minimum bounding rectangles
        ctx.strokeStyle = '#ec4899';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        
        // Level 1: Large bounding rectangles
        ctx.strokeRect(80, 70, 60, 60);  // Cluster 1
        ctx.strokeRect(270, 60, 60, 60); // Cluster 2
        ctx.strokeRect(180, 160, 60, 60); // Cluster 3
        
        // Level 2: Smaller bounding rectangles
        ctx.strokeStyle = '#be185d';
        ctx.strokeRect(85, 75, 25, 25);  // Sub-cluster 1a
        ctx.strokeRect(275, 65, 25, 25); // Sub-cluster 2a
        ctx.strokeRect(185, 165, 25, 25); // Sub-cluster 3a
        
        ctx.setLineDash([]);
    }
    
    // Button event listeners
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            button.classList.add('active');
            const treeType = button.getAttribute('data-tree') || 'dctree';
            drawTreeDemo(treeType);
        });
    });
    
    // Initial draw
    drawTreeDemo('dctree');
}

function initPowerParameterDemo() {
    const canvas = document.getElementById('power-demo-canvas') as HTMLCanvasElement;
    const caption = document.getElementById('power-demo-caption');
    const slider = document.getElementById('power-slider') as HTMLInputElement;
    const valueSpan = document.getElementById('power-value');
    
    if (!canvas || !caption || !slider || !valueSpan) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Create a clear dataset that demonstrates power parameter effects
    const points = [
        // Blue cluster - close to center A
        {x: 85, y: 105, id: 'blue1'}, {x: 95, y: 115, id: 'blue2'}, {x: 80, y: 120, id: 'blue3'},
        // Green cluster - close to center B  
        {x: 315, y: 95, id: 'green1'}, {x: 305, y: 105, id: 'green2'}, {x: 320, y: 110, id: 'green3'},
        // Intermediate points - these will change assignment based on power
        {x: 130, y: 120, id: 'demo'}, {x: 200, y: 110, id: 'demo'}, {x: 270, y: 120, id: 'demo'},
        // Borderline points - may become outliers at high power
        {x: 150, y: 140, id: 'border'}, {x: 250, y: 130, id: 'border'},
        // Far points - will become outliers at higher power
        {x: 200, y: 160, id: 'far'}, {x: 180, y: 80, id: 'far'}
    ];
    
    function drawPowerDemo(power: number) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw title with power explanation
        ctx.fillStyle = '#1f2937';
        ctx.font = '16px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`Power Parameter: ${power}`, 200, 20);
        
        // Draw power explanation
        ctx.fillStyle = '#6b7280';
        ctx.font = '12px Inter, sans-serif';
        const powerExplanations = {
            2: 'Standard k-Means (balanced distance penalty)',
            4: 'Tighter clusters (higher distance penalty)', 
            6: 'Very tight clusters (maximum distance penalty)'
        };
        ctx.fillText(powerExplanations[power], 200, 35);
        
        // Calculate cluster centers
        const centers = [
            {x: 90, y: 110, color: '#3b82f6', label: 'Center A', name: 'Blue Cluster'},
            {x: 310, y: 100, color: '#10b981', label: 'Center B', name: 'Green Cluster'}
        ];
        
        // Calculate cluster assignments using actual power-based distance
        const assignments = assignClustersWithPower(points, centers, power);
        
        // Draw cluster boundaries/influence zones
        drawClusterInfluenceZones(ctx, centers, power);
        
        // Draw connection lines from points to their assigned centers
        drawConnectionLines(ctx, points, centers, assignments, power);
        
        // Draw cluster centers with enhanced visibility
        centers.forEach((center, i) => {
            // Draw influence circle
            ctx.beginPath();
            ctx.arc(center.x, center.y, 8, 0, Math.PI * 2);
            ctx.fillStyle = center.color;
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 3;
            ctx.stroke();
            ctx.strokeStyle = '#1f2937';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Center labels
            ctx.fillStyle = '#1f2937';
            ctx.font = '12px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(center.label, center.x, center.y - 20);
        });
        
        // Draw points with enhanced visualization
        points.forEach((point, i) => {
            const clusterIndex = assignments[i];
            const isOutlier = clusterIndex === -1;
            const color = isOutlier ? '#ef4444' : centers[clusterIndex].color;
            
            // Point circle
            ctx.beginPath();
            ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.strokeStyle = '#1f2937';
            ctx.lineWidth = 1;
            ctx.stroke();
            
            // Special highlighting for key demonstration points
            if (point.id === 'demo') {
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 3;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.arc(point.x, point.y, 12, 0, Math.PI * 2);
                ctx.stroke();
                ctx.setLineDash([]);
                
                // Distance labels removed to clean up visualization
            }
        });
        
        // Draw legend
        drawLegend(ctx, power);
        
        // Update caption with clearer explanation
        const captions = {
            2: 'Power = 2: Moderate penalty for distance. Points join their nearest cluster center.',
            4: 'Power = 4: Higher penalty makes clusters tighter. Some points may become outliers.',
            6: 'Power = 6: Very high penalty creates very tight clusters. More points become outliers.'
        };
        caption.textContent = captions[power] || captions[2];
    }
    
    function drawClusterInfluenceZones(ctx: CanvasRenderingContext2D, centers: any[], power: number) {
        // Draw influence zones that shrink with higher power
        const baseRadius = power === 2 ? 45 : power === 4 ? 35 : 25;
        
        centers.forEach(center => {
            ctx.beginPath();
            ctx.arc(center.x, center.y, baseRadius, 0, Math.PI * 2);
            ctx.strokeStyle = center.color;
            ctx.setLineDash([8, 8]);
            ctx.lineWidth = 2;
            ctx.globalAlpha = 0.3;
            ctx.stroke();
            ctx.globalAlpha = 1;
            ctx.setLineDash([]);
        });
    }
    
    function drawConnectionLines(ctx: CanvasRenderingContext2D, points: any[], centers: any[], assignments: number[], power: number) {
        // Draw lines from points to their assigned centers
        points.forEach((point, i) => {
            const clusterIndex = assignments[i];
            if (clusterIndex >= 0) {
                const center = centers[clusterIndex];
                
                ctx.beginPath();
                ctx.moveTo(point.x, point.y);
                ctx.lineTo(center.x, center.y);
                ctx.strokeStyle = center.color;
                ctx.globalAlpha = 0.4;
                ctx.lineWidth = 1;
                ctx.stroke();
                ctx.globalAlpha = 1;
            }
        });
    }
    

    
    function drawLegend(ctx: CanvasRenderingContext2D, power: number) {
        // Draw legend explaining the visualization
        const legendX = 20;
        const legendY = 200;
        
        ctx.fillStyle = '#f8fafc';
        ctx.fillRect(legendX, legendY, 120, 45);
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;
        ctx.strokeRect(legendX, legendY, 120, 45);
        
        ctx.fillStyle = '#374151';
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('Legend:', legendX + 5, legendY + 12);
        
        // Cluster point
        ctx.beginPath();
        ctx.arc(legendX + 15, legendY + 22, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#3b82f6';
        ctx.fill();
        ctx.fillStyle = '#374151';
        ctx.fillText('Cluster member', legendX + 25, legendY + 25);
        
        // Outlier point
        ctx.beginPath();
        ctx.arc(legendX + 15, legendY + 35, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#ef4444';
        ctx.fill();
        ctx.fillStyle = '#374151';
        ctx.fillText('Outlier (too far)', legendX + 25, legendY + 38);
    }
    
    function assignClustersWithPower(points: any[], centers: any[], power: number) {
        return points.map(point => {
            // Calculate actual distances to each center
            const distances = centers.map(center => 
                Math.hypot(point.x - center.x, point.y - center.y)
            );
            
            // Calculate powered distances (this is what the algorithm actually uses)
            const poweredDistances = distances.map(d => Math.pow(d, power));
            
            // Find the center with minimum powered distance
            const minPoweredDistance = Math.min(...poweredDistances);
            const closestCenter = poweredDistances.indexOf(minPoweredDistance);
            const actualDistance = distances[closestCenter];
            
            // Threshold decreases with higher power (tighter clusters)
            // This simulates how higher power values create more exclusive clusters
            const threshold = power === 2 ? 55 : power === 4 ? 45 : 35;
            
            if (actualDistance > threshold) {
                return -1; // Outlier - too far from any center
            }
            
            return closestCenter;
        });
    }
    

    
    // Slider event listener
    slider.addEventListener('input', () => {
        const power = parseInt(slider.value);
        valueSpan.textContent = power.toString();
        drawPowerDemo(power);
    });
    
    // Initial draw
    drawPowerDemo(2);
}

function initPartitionMethodDemo() {
    const canvas = document.getElementById('partition-demo-canvas') as HTMLCanvasElement;
    const caption = document.getElementById('partition-demo-caption');
    const buttons = document.querySelectorAll('.partition-btn');
    
    if (!canvas || !caption) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Sample hierarchical data
    const points = [
        {x: 80, y: 100, cluster: 0}, {x: 100, y: 110, cluster: 0}, {x: 90, y: 120, cluster: 0},
        {x: 200, y: 80, cluster: 1}, {x: 220, y: 90, cluster: 1}, {x: 210, y: 100, cluster: 1},
        {x: 320, y: 110, cluster: 2}, {x: 340, y: 120, cluster: 2}, {x: 330, y: 130, cluster: 2},
        {x: 160, y: 180, cluster: 3}, {x: 180, y: 190, cluster: 3}
    ];
    
    function drawPartitionDemo(method: string) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (method === 'k') {
            drawKMethodDemo(ctx);
            caption.textContent = 'K Method: You specify exactly how many clusters you want - direct manual control';
        } else if (method === 'elbow') {
            drawElbowMethodDemo(ctx);
            caption.textContent = 'Elbow Method: Finds the "elbow" point where adding more clusters gives diminishing returns';
        } else if (method === 'stability') {
            drawStabilityMethodDemo(ctx);
            caption.textContent = 'Stability Method: Identifies clusters that remain consistent across different parameter values';
        } else if (method === 'qcoverage') {
            drawQCoverageMethodDemo(ctx);
            caption.textContent = 'QCoverage Method: Optimizes the trade-off between cluster coverage and separation quality';
        }
    }
    
    function drawKMethodDemo(ctx: CanvasRenderingContext2D) {
        // Show K selection interface
        ctx.fillStyle = '#1f2937';
        ctx.font = '16px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Choose Number of Clusters', 200, 30);
        
        // Draw K selection buttons
        const kValues = [2, 3, 4, 5];
        const selectedK = 3;
        
        kValues.forEach((k, i) => {
            const x = 80 + i * 60;
            const y = 50;
            const isSelected = k === selectedK;
            
            // Button background
            ctx.fillStyle = isSelected ? '#3b82f6' : '#f1f5f9';
            ctx.fillRect(x - 15, y - 15, 30, 30);
            
            // Button text
            ctx.fillStyle = isSelected ? 'white' : '#374151';
            ctx.font = '14px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(k.toString(), x, y + 5);
        });
        
        // Show resulting clusters
        const clusterData = [
            {x: 100, y: 120, cluster: 0}, {x: 120, y: 130, cluster: 0},
            {x: 200, y: 110, cluster: 1}, {x: 220, y: 120, cluster: 1},
            {x: 300, y: 140, cluster: 2}, {x: 320, y: 150, cluster: 2}
        ];
        
        const colors = ['#3b82f6', '#10b981', '#f97316'];
        clusterData.forEach(point => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 8, 0, Math.PI * 2);
            ctx.fillStyle = colors[point.cluster];
            ctx.fill();
            ctx.strokeStyle = '#1f2937';
            ctx.lineWidth = 2;
            ctx.stroke();
        });
        
        // Labels
        ctx.fillStyle = '#6b7280';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText('Result: Exactly 3 clusters as specified', 200, 200);
    }
    
    function drawElbowMethodDemo(ctx: CanvasRenderingContext2D) {
        // Draw elbow plot
        ctx.fillStyle = '#1f2937';
        ctx.font = '16px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Elbow Plot - Cost vs Number of Clusters', 200, 30);
        
        // Plot axes
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(50, 180);
        ctx.lineTo(350, 180); // X-axis
        ctx.moveTo(50, 50);
        ctx.lineTo(50, 180); // Y-axis
        ctx.stroke();
        
        // Axis labels
        ctx.fillStyle = '#6b7280';
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Number of Clusters (k)', 200, 200);
        
        ctx.save();
        ctx.translate(25, 115);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Cost (Within-Cluster Sum of Squares)', 0, 0);
        ctx.restore();
        
        // Plot data points and line
        const elbowData = [
            {k: 1, cost: 150, x: 80, y: 70},
            {k: 2, cost: 100, x: 120, y: 90},
            {k: 3, cost: 70, x: 160, y: 110}, // Elbow point
            {k: 4, cost: 60, x: 200, y: 120},
            {k: 5, cost: 55, x: 240, y: 125},
            {k: 6, cost: 52, x: 280, y: 128}
        ];
        
        // Draw line
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 3;
        ctx.beginPath();
        elbowData.forEach((point, i) => {
            if (i === 0) ctx.moveTo(point.x, point.y);
            else ctx.lineTo(point.x, point.y);
        });
        ctx.stroke();
        
        // Draw points
        elbowData.forEach((point, i) => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
            ctx.fillStyle = i === 2 ? '#ef4444' : '#3b82f6'; // Highlight elbow
            ctx.fill();
            
            // K labels
            ctx.fillStyle = '#374151';
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(point.k.toString(), point.x, point.y + 20);
        });
        
        // Highlight elbow point
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 3;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.arc(160, 110, 15, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
        
        ctx.fillStyle = '#ef4444';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText('Elbow Point: k=3', 160, 140);
    }
    
    function drawStabilityMethodDemo(ctx: CanvasRenderingContext2D) {
        // Show stability analysis
        ctx.fillStyle = '#1f2937';
        ctx.font = '16px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Cluster Stability Across Parameter Values', 200, 30);
        
        // Draw stability plot
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(50, 180);
        ctx.lineTo(350, 180); // X-axis
        ctx.moveTo(50, 50);
        ctx.lineTo(50, 180); // Y-axis
        ctx.stroke();
        
        // Labels
        ctx.fillStyle = '#6b7280';
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Parameter Value', 200, 200);
        
        ctx.save();
        ctx.translate(25, 115);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Cluster Stability Score', 0, 0);
        ctx.restore();
        
        // Draw stability curves for different cluster counts
        const stabilityData = {
            2: [{x: 80, y: 160}, {x: 120, y: 140}, {x: 160, y: 120}, {x: 200, y: 110}, {x: 240, y: 115}, {x: 280, y: 125}],
            3: [{x: 80, y: 170}, {x: 120, y: 165}, {x: 160, y: 160}, {x: 200, y: 165}, {x: 240, y: 170}, {x: 280, y: 175}],
            4: [{x: 80, y: 150}, {x: 120, y: 130}, {x: 160, y: 100}, {x: 200, y: 90}, {x: 240, y: 100}, {x: 280, y: 120}]
        };
        
        const colors = ['#10b981', '#6b7280', '#f97316'];
        const labels = ['k=2 (Most Stable)', 'k=3', 'k=4'];
        
        Object.entries(stabilityData).forEach(([k, data], i) => {
            ctx.strokeStyle = colors[i];
            ctx.lineWidth = k === '2' ? 4 : 2;
            ctx.beginPath();
            data.forEach((point, j) => {
                if (j === 0) ctx.moveTo(point.x, point.y);
                else ctx.lineTo(point.x, point.y);
            });
            ctx.stroke();
            
            // Legend
            ctx.fillStyle = colors[i];
            ctx.fillRect(60, 60 + i * 20, 15, 3);
            ctx.fillStyle = '#374151';
            ctx.font = '11px Inter, sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText(labels[i], 80, 65 + i * 20);
        });
    }
    
    function drawQCoverageMethodDemo(ctx: CanvasRenderingContext2D) {
        // Show coverage vs separation trade-off
        ctx.fillStyle = '#1f2937';
        ctx.font = '16px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Quality Coverage Analysis', 200, 30);
        
        // Draw scatter plot showing coverage vs separation
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(60, 190);
        ctx.lineTo(340, 190); // X-axis
        ctx.moveTo(60, 60);
        ctx.lineTo(60, 190); // Y-axis
        ctx.stroke();
        
        // Labels
        ctx.fillStyle = '#6b7280';
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Cluster Separation', 200, 210);
        
        ctx.save();
        ctx.translate(30, 125);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Coverage Quality', 0, 0);
        ctx.restore();
        
        // Plot different k values with better spacing
        const qcoverageData = [
            {k: 2, coverage: 0.6, separation: 0.8, x: 260, y: 140, optimal: false},
            {k: 3, coverage: 0.75, separation: 0.7, x: 220, y: 120, optimal: false},
            {k: 4, coverage: 0.85, separation: 0.75, x: 250, y: 100, optimal: true},
            {k: 5, coverage: 0.8, separation: 0.6, x: 190, y: 110, optimal: false},
            {k: 6, coverage: 0.7, separation: 0.5, x: 160, y: 130, optimal: false}
        ];
        
        // Draw Pareto frontier
        ctx.strokeStyle = '#8b5cf6';
        ctx.lineWidth = 2;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(160, 150);
        ctx.lineTo(250, 100);
        ctx.lineTo(290, 120);
        ctx.stroke();
        ctx.setLineDash([]);
        
        // Draw points with better label positioning
        qcoverageData.forEach(point => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 8, 0, Math.PI * 2);
            ctx.fillStyle = point.optimal ? '#8b5cf6' : '#d1d5db';
            ctx.fill();
            ctx.strokeStyle = point.optimal ? '#6d28d9' : '#9ca3af';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Labels with better positioning to avoid overlap
            ctx.fillStyle = point.optimal ? '#6d28d9' : '#6b7280';
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'center';
            
            // Adjust label position based on point location to avoid overlap
            let labelY = point.y - 18;
            if (point.k === 3 || point.k === 5) {
                labelY = point.y + 25; // Move labels below for these points
            }
            
            ctx.fillText(`k=${point.k}`, point.x, labelY);
        });
        
        // Highlight optimal with better positioning
        ctx.fillStyle = '#8b5cf6';
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Optimal: k=4', 250, 75);
    }
    

    
    function calculateClusterCenters(points: any[], clusters: number[], numClusters: number) {
        const centers = [];
        for (let i = 0; i < numClusters; i++) {
            const clusterPoints = points.filter((_, idx) => clusters[idx] === i);
            if (clusterPoints.length > 0) {
                const avgX = clusterPoints.reduce((sum, p) => sum + p.x, 0) / clusterPoints.length;
                const avgY = clusterPoints.reduce((sum, p) => sum + p.y, 0) / clusterPoints.length;
                centers.push({x: avgX, y: avgY});
            }
        }
        return centers;
    }
    
    // Button event listeners
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            button.classList.add('active');
            const method = button.getAttribute('data-method') || 'k';
            drawPartitionDemo(method);
        });
    });
    
    // Initial draw
    drawPartitionDemo('k');
}

function initIciclePlotDemo() {
    const icicleCanvas = document.getElementById('icicle-canvas') as HTMLCanvasElement;
    const dendrogramCanvas = document.getElementById('dendrogram-canvas') as HTMLCanvasElement;
    const caption = document.getElementById('comparison-caption');
    
    if (!icicleCanvas || !dendrogramCanvas || !caption) return;
    
    const icicleCtx = icicleCanvas.getContext('2d');
    const dendrogramCtx = dendrogramCanvas.getContext('2d');
    if (!icicleCtx || !dendrogramCtx) return;
    
    // Sample hierarchical data with deeper nesting
    const hierarchyData = {
        name: 'Dataset',
        value: 100,
        children: [
            {
                name: 'Group A',
                value: 40,
                children: [
                    { 
                        name: 'A1', 
                        value: 25,
                        children: [
                            { name: 'A1a', value: 15 },
                            { name: 'A1b', value: 10 }
                        ]
                    },
                    { name: 'A2', value: 15 }
                ]
            },
            {
                name: 'Group B',
                value: 35,
                children: [
                    { name: 'B1', value: 20 },
                    { name: 'B2', value: 15 }
                ]
            },
            {
                name: 'Group C',
                value: 25,
                children: [
                    { name: 'C1', value: 15 },
                    { name: 'C2', value: 10 }
                ]
            }
        ]
    };
    
    // Colors for different levels
    const colors = {
        level0: '#1e40af', // Dark blue
        level1: '#3b82f6', // Blue
        level2: '#60a5fa', // Light blue
        level3: '#93c5fd'  // Lightest blue
    };
    
    // No interactivity needed - both visualizations are static
    
    function drawIciclePlot() {
        icicleCtx.clearRect(0, 0, icicleCanvas.width, icicleCanvas.height);
        
        const margin = { top: 25, right: 15, bottom: 25, left: 15 };
        const width = icicleCanvas.width - margin.left - margin.right;
        const height = icicleCanvas.height - margin.top - margin.bottom;
        
        // Calculate layout for 4 levels
        const levelHeight = height / 4;
        
        // Root level (level 0)
        const rootHeight = levelHeight * 0.7;
        drawRect(margin.left, margin.top, width, rootHeight, hierarchyData, 0);
        
        // Level 1 - main groups
        let currentX = margin.left;
        const level1Y = margin.top + rootHeight + 5;
        const level1Height = levelHeight * 0.8;
        
        hierarchyData.children?.forEach(child => {
            const proportion = child.value / hierarchyData.value;
            const rectWidth = width * proportion;
            
            drawRect(currentX, level1Y, rectWidth - 2, level1Height, child, 1);
            
            // Level 2 - subgroups
            let subX = currentX;
            const level2Y = level1Y + level1Height + 5;
            const level2Height = levelHeight * 0.7;
            
            child.children?.forEach(subchild => {
                const subProportion = subchild.value / child.value;
                const subWidth = rectWidth * subProportion;
                
                drawRect(subX, level2Y, subWidth - 2, level2Height, subchild, 2);
                
                // Level 3 - deepest level (only for A1 children)
                if (subchild.children) {
                    let deepX = subX;
                    const level3Y = level2Y + level2Height + 5;
                    const level3Height = levelHeight * 0.6;
                    
                    subchild.children.forEach(deepchild => {
                        const deepProportion = deepchild.value / subchild.value;
                        const deepWidth = subWidth * deepProportion;
                        
                        drawRect(deepX, level3Y, deepWidth - 2, level3Height, deepchild, 3);
                        deepX += deepWidth;
                    });
                }
                
                subX += subWidth;
            });
            
            currentX += rectWidth;
        });
        
        // Add level labels
        icicleCtx.fillStyle = '#6b7280';
        icicleCtx.font = '10px Inter, sans-serif';
        icicleCtx.textAlign = 'left';
        icicleCtx.fillText('Root', 5, 18);
        icicleCtx.fillText('Groups', 5, level1Y - 3);
        icicleCtx.fillText('Items', 5, level1Y + level1Height + 5 - 3);
        icicleCtx.fillText('Sub-items', 5, level1Y + level1Height + levelHeight * 0.7 + 10 - 3);
    }
    
    function drawRect(x: number, y: number, width: number, height: number, node: any, level: number) {
        const levelColor = colors[`level${level}` as keyof typeof colors];
        
        // Rectangle fill
        icicleCtx.fillStyle = levelColor;
        icicleCtx.fillRect(x, y, width, height);
        
        // Rectangle border
        icicleCtx.strokeStyle = '#ffffff';
        icicleCtx.lineWidth = 2;
        icicleCtx.strokeRect(x, y, width, height);
        
        // Text rendering
        if (width > 30 && height > 20) {
            icicleCtx.fillStyle = '#ffffff';
            icicleCtx.font = level === 0 ? 'bold 14px Inter, sans-serif' : level === 1 ? 'bold 12px Inter, sans-serif' : '10px Inter, sans-serif';
            icicleCtx.textAlign = 'center';
            icicleCtx.textBaseline = 'middle';
            
            const textX = x + width / 2;
            const textY = y + height / 2 - (level === 0 ? 4 : 0);
            
            // Smart text truncation
            let displayName = node.name;
            const maxWidth = width - 8;
            let textWidth = icicleCtx.measureText(displayName).width;
            
            while (textWidth > maxWidth && displayName.length > 2) {
                displayName = displayName.substring(0, displayName.length - 1);
                textWidth = icicleCtx.measureText(displayName).width;
            }
            
            icicleCtx.fillText(displayName, textX, textY);
            
            // Show value for larger rectangles
            if (height > 40 && width > 60) {
                icicleCtx.font = '9px Inter, sans-serif';
                icicleCtx.fillText(`(${node.value})`, textX, textY + 12);
            }
        }
    }
    
    function drawDendrogram() {
        dendrogramCtx.clearRect(0, 0, dendrogramCanvas.width, dendrogramCanvas.height);
        
        const margin = { top: 30, right: 20, bottom: 60, left: 20 };
        const width = dendrogramCanvas.width - margin.left - margin.right;
        const height = dendrogramCanvas.height - margin.top - margin.bottom;
        
        console.log('Drawing dendrogram with dimensions:', { width, height, canvasWidth: dendrogramCanvas.width, canvasHeight: dendrogramCanvas.height });
        
        // Calculate positions for all levels
        const leafY = margin.top + height - 20;
        const rootY = margin.top + 20;
        const levelHeight = (leafY - rootY) / 3;
        
        const positions: any[] = [];
        
        // Step 1: Position all leaf nodes (bottom level)
        let currentX = margin.left + 40;
        const leafSpacing = (width - 80) / 6; // 7 total leaf nodes: A1a, A1b, A2, B1, B2, C1, C2
        
        // Collect all leaves in order: A1a, A1b, A2, B1, B2, C1, C2
        const leaves = [
            { node: hierarchyData.children[0].children[0].children[0], path: [0, 0, 0], level: 3 }, // A1a
            { node: hierarchyData.children[0].children[0].children[1], path: [0, 0, 1], level: 3 }, // A1b
            { node: hierarchyData.children[0].children[1], path: [0, 1], level: 2 }, // A2
            { node: hierarchyData.children[1].children[0], path: [1, 0], level: 2 }, // B1
            { node: hierarchyData.children[1].children[1], path: [1, 1], level: 2 }, // B2
            { node: hierarchyData.children[2].children[0], path: [2, 0], level: 2 }, // C1
            { node: hierarchyData.children[2].children[1], path: [2, 1], level: 2 }  // C2
        ];
        
        leaves.forEach((leaf, index) => {
            const pos = {
                x: currentX,
                y: leafY,
                node: leaf.node,
                level: leaf.level,
                path: leaf.path
            };
            positions.push(pos);
            currentX += leafSpacing;
        });
        
        // Step 2: Position A1 (parent of A1a and A1b)
        const a1aPos = positions.find(p => p.node.name === 'A1a');
        const a1bPos = positions.find(p => p.node.name === 'A1b');
        if (a1aPos && a1bPos) {
            const a1Pos = {
                x: (a1aPos.x + a1bPos.x) / 2,
                y: rootY + levelHeight * 2,
                node: hierarchyData.children[0].children[0], // A1
                level: 2,
                path: [0, 0]
            };
            positions.push(a1Pos);
        }
        
        // Step 3: Position group nodes (Group A, B, C)
        hierarchyData.children.forEach((group, groupIndex) => {
            const groupChildren = positions.filter(p => p.path[0] === groupIndex && (p.level === 2 || p.level === 3));
            const avgX = groupChildren.reduce((sum, p) => sum + p.x, 0) / groupChildren.length;
            
            const groupPos = {
                x: avgX,
                y: rootY + levelHeight,
                node: group,
                level: 1,
                path: [groupIndex]
            };
            positions.push(groupPos);
        });
        
        // Step 4: Position root
        const groupNodes = positions.filter(p => p.level === 1);
        const rootX = groupNodes.reduce((sum, p) => sum + p.x, 0) / groupNodes.length;
        const rootPos = {
            x: rootX,
            y: rootY,
            node: hierarchyData,
            level: 0,
            path: []
        };
        positions.push(rootPos);
        
        console.log('Positioned nodes:', positions.length);
        
        // Draw connections
        dendrogramCtx.strokeStyle = '#6b7280';
        dendrogramCtx.lineWidth = 2;
        
        // Root to groups
        groupNodes.forEach(groupPos => {
            drawConnection(rootPos, groupPos);
        });
        
        // Groups to their children
        hierarchyData.children.forEach((group, groupIndex) => {
            const groupPos = positions.find(p => p.level === 1 && p.path[0] === groupIndex);
            if (!groupPos) return;
            
            group.children.forEach((child, childIndex) => {
                if (child.children) {
                    // Connect to A1 (intermediate node)
                    const childPos = positions.find(p => p.level === 2 && p.path[0] === groupIndex && p.path[1] === childIndex);
                    if (childPos) {
                        drawConnection(groupPos, childPos);
                    }
                } else {
                    // Connect directly to leaf
                    const leafPos = positions.find(p => p.level === 2 && p.path[0] === groupIndex && p.path[1] === childIndex);
                    if (leafPos) {
                        drawConnection(groupPos, leafPos);
                    }
                }
            });
        });
        
        // A1 to its children
        const a1Node = positions.find(p => p.level === 2 && p.node.name === 'A1');
        if (a1Node) {
            const a1Children = positions.filter(p => p.level === 3);
            a1Children.forEach(childPos => {
                drawConnection(a1Node, childPos);
            });
        }
        
        // Draw nodes with improved text positioning
        positions.forEach(pos => {
            const levelColor = colors[`level${pos.level}` as keyof typeof colors];
            
            // Node circle (no hover effects)
            dendrogramCtx.beginPath();
            dendrogramCtx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
            dendrogramCtx.fillStyle = levelColor;
            dendrogramCtx.fill();
            dendrogramCtx.strokeStyle = '#ffffff';
            dendrogramCtx.lineWidth = 2;
            dendrogramCtx.stroke();
            
            // Determine text position based on node level to avoid connection lines
            let labelY, valueY;
            
            if (pos.level === 0) {
                // Root node - text above
                labelY = pos.y - 12;
                valueY = pos.y - 2;
            } else if (pos.level === 1) {
                // Group nodes - text to the side to avoid vertical connections
                labelY = pos.y - 18;
                valueY = pos.y - 8;
            } else if (pos.level === 2 && pos.node.name === 'A1') {
                // A1 node - text to the side to avoid connections to children
                labelY = pos.y - 18;
                valueY = pos.y - 8;
            } else {
                // Leaf nodes - text below
                labelY = pos.y + 20;
                valueY = pos.y + 32;
            }
            
            // Draw text with background for better readability
            dendrogramCtx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            const nameWidth = dendrogramCtx.measureText(pos.node.name).width;
            const valueText = `(${pos.node.value})`;
            const valueWidth = dendrogramCtx.measureText(valueText).width;
            const maxWidth = Math.max(nameWidth, valueWidth);
            
            // Background rectangles for text
            dendrogramCtx.fillRect(pos.x - maxWidth/2 - 2, labelY - 8, maxWidth + 4, 10);
            dendrogramCtx.fillRect(pos.x - maxWidth/2 - 2, valueY - 6, maxWidth + 4, 8);
            
            // Node label
            dendrogramCtx.fillStyle = '#1f2937';
            dendrogramCtx.font = 'bold 10px Inter, sans-serif';
            dendrogramCtx.textAlign = 'center';
            dendrogramCtx.fillText(pos.node.name, pos.x, labelY);
            
            // Value label
            dendrogramCtx.font = '8px Inter, sans-serif';
            dendrogramCtx.fillStyle = '#6b7280';
            dendrogramCtx.fillText(valueText, pos.x, valueY);
        });
        
        console.log('Dendrogram drawn successfully');
    }
    
    function drawConnection(from: any, to: any) {
        dendrogramCtx.beginPath();
        dendrogramCtx.moveTo(from.x, from.y + 7);
        dendrogramCtx.lineTo(from.x, (from.y + to.y) / 2);
        dendrogramCtx.lineTo(to.x, (from.y + to.y) / 2);
        dendrogramCtx.lineTo(to.x, to.y - 7);
        dendrogramCtx.stroke();
    }
    
    // Both visualizations are now static - no event listeners needed
    
    // Initial draw
    drawIciclePlot();
    drawDendrogram();
}
</script>

<style scoped>
@import '~/assets/css/pages/index.css';
</style>

