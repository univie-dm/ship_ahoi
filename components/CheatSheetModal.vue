<template>
  <div v-if="isOpen" class="cheatsheet-overlay" @click.self="close">
    <div class="cheatsheet-modal">
        <div class="modal-header">
            <h2 class="modal-title">SHIP.AHOI Quick Reference</h2>
            <button class="close-btn" @click="close" aria-label="Close">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
        
        <div class="modal-content">
            <div class="intro-text">
                Need more details? Visit the <NuxtLink to="/explanation" target="_blank" class="explanation-link">Interactive Explanations Page</NuxtLink>.
            </div>

            <!-- Trees Section -->
            <section class="cheatsheet-section">
                <h3><span class="icon">🌲</span> Similarity Trees</h3>
                <p class="section-desc">How data points are connected into a hierarchy.</p>
                <div class="items-grid">
                    <div class="item-card">
                        <strong>DCTree</strong> <span class="badge badge-blue">Density</span>
                        <p>Connects points in dense regions. Great for arbitrary shapes and varying densities (like DBSCAN).</p>
                    </div>
                    <div class="item-card">
                        <strong>CoverTree / BallTree</strong> <span class="badge badge-green">Spatial</span>
                        <p>Hierarchical spheres. Good for finding round, compact clusters and spatial proximity.</p>
                    </div>
                </div>
            </section>

            <!-- Power Section -->
            <section class="cheatsheet-section">
                <h3><span class="icon">⚡</span> Power Parameter</h3>
                <p class="section-desc">Controls how much distance is penalized.</p>
                <div class="items-grid">
                    <div class="item-card">
                        <strong>Power ~0</strong> <span class="badge badge-gray">Loose</span>
                        <p>Minimizes exactly the max distance (k-Center). Allows long, connected components (chains).</p>
                    </div>
                    <div class="item-card">
                        <strong>Power = 2</strong> <span class="badge badge-gray">Balanced</span>
                        <p>Standard squared distance (k-Means). Enforces balanced, spherical compactness.</p>
                    </div>
                    <div class="item-card">
                        <strong>Power > 2</strong> <span class="badge badge-gray">Strict</span>
                        <p>Creates extremely tight clusters. Outliers will emerge more quickly.</p>
                    </div>
                </div>
            </section>

            <!-- Partition Methods -->
            <section class="cheatsheet-section">
                <h3><span class="icon">✂️</span> Partition (K-Finding)</h3>
                <p class="section-desc">Strategies to cut the tree into final clusters.</p>
                <div class="items-grid">
                    <div class="item-card">
                        <strong>K (Manual)</strong>
                        <p>You explicitly define exactly how many clusters you want.</p>
                    </div>
                    <div class="item-card">
                        <strong>Elbow</strong>
                        <p>Finds the "knee" point where adding more clusters provides diminishing returns in quality.</p>
                    </div>
                    <div class="item-card">
                        <strong>Stability</strong>
                        <p>Extracts clusters that persist over a wide range of density/distance thresholds.</p>
                    </div>
                    <div class="item-card">
                        <strong>Silhouette</strong>
                        <p>Maximizes the mathematical Silhouette score across the whole hierarchy.</p>
                    </div>
                     <div class="item-card">
                        <strong>QCoverage</strong>
                        <p>Optimizes the trade-off between coverage and variance separation.</p>
                    </div>
                </div>
            </section>

            <!-- Metrics -->
            <section class="cheatsheet-section">
                <h3><span class="icon">📊</span> Metrics</h3>
                <p class="section-desc">How cluster quality is evaluated.</p>
                <div class="items-grid list-view">
                    <div class="item-row">
                        <div class="row-header"><strong>Silhouette</strong> <span>(-1 to +1)</span></div>
                        <p>High is better. Measures density and separation.</p>
                    </div>
                    <div class="item-row">
                        <div class="row-header"><strong>Davies-Bouldin</strong> <span>(Close to 0)</span></div>
                        <p>Low is better. Measures ratio of within-cluster spread to between-cluster separation.</p>
                    </div>
                    <div class="item-row">
                        <div class="row-header"><strong>Calinski-Harabasz</strong> <span>(Higher is better)</span></div>
                        <p>Variance Ratio. High means dense, well-separated clusters.</p>
                    </div>
                    <div class="item-row">
                        <div class="row-header"><strong>ARI</strong> <span>(0 to +1)</span></div>
                        <p>High is better (1 = perfect). Agreement with Ground Truth labels.</p>
                    </div>
                </div>
            </section>

        </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const isOpen = ref(false);

const open = () => {
    isOpen.value = true;
    document.body.style.overflow = 'hidden';
};

const close = () => {
    isOpen.value = false;
    document.body.style.overflow = '';
};

// Expose open and close methods
defineExpose({
    open,
    close
});
</script>

<style scoped>
.cheatsheet-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(15, 23, 42, 0.6);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    backdrop-filter: blur(4px);
}

.cheatsheet-modal {
    background: #ffffff;
    width: 90%;
    max-width: 800px;
    max-height: 90vh;
    border-radius: 12px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: modal-enter 0.2s ease-out;
}

@keyframes modal-enter {
    from { opacity: 0; transform: scale(0.95) translateY(10px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #e2e8f0;
    background: #f8fafc;
}

.modal-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
}

.close-btn {
    background: transparent;
    border: none;
    color: #64748b;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 4px;
    transition: all 0.2s;
}

.close-btn:hover {
    background: #e2e8f0;
    color: #0f172a;
}

.modal-content {
    padding: 1.5rem;
    overflow-y: auto;
    flex: 1;
}

.intro-text {
    background: #eff6ff;
    padding: 1rem;
    border-radius: 8px;
    color: #1e40af;
    margin-bottom: 2rem;
    font-size: 0.95rem;
    border: 1px solid #bfdbfe;
    text-align: center;
}

.explanation-link {
    font-weight: 600;
    color: #2563eb;
    text-decoration: underline;
}

.cheatsheet-section {
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #f1f5f9;
}

.cheatsheet-section h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.15rem;
    color: #1e293b;
    margin: 0 0 0.25rem 0;
}

.section-desc {
    color: #64748b;
    font-size: 0.9rem;
    margin: 0 0 1rem 0;
}

.items-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 1rem;
}

.item-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 1rem;
    border-radius: 8px;
}

.item-card strong {
    display: inline-block;
    color: #0f172a;
    margin-bottom: 0.25rem;
}

.item-card p {
    font-size: 0.85rem;
    color: #475569;
    margin: 0.5rem 0 0 0;
    line-height: 1.4;
}

.badge {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    text-transform: uppercase;
    margin-left: 0.5rem;
    vertical-align: middle;
}

.badge-blue { background: #dbeafe; color: #1e40af; }
.badge-green { background: #dcfce3; color: #166534; }
.badge-gray { background: #e2e8f0; color: #475569; }

.list-view {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.item-row {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 0.75rem 1rem;
    border-radius: 8px;
}

.row-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.25rem;
}

.row-header strong {
    color: #0f172a;
}

.row-header span {
    font-size: 0.8rem;
    color: #64748b;
    background: #e2e8f0;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
}

.item-row p {
    font-size: 0.85rem;
    color: #475569;
    margin: 0;
}
</style>
