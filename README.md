# SHIP.AHOI

**SHIP.AHOI** is an interactive web application for hierarchical clustering analysis built upon the powerful SHiP (Similarity-Hierarchy-Partition) framework. Generate and explore vast landscapes of clustering solutions with unprecedented speed and flexibility.

## Features

- **Ultra-Fast Clustering**: Build similarity trees once, derive countless clusterings instantly
- **Interactive Visualizations**: D3.js-powered tree visualizations and scatter plots with real-time interaction
- **Research-Grade Metrics**: Integrated DISCO evaluation metric for advanced clustering assessment
- **Scalable Architecture**: Handles large datasets with intelligent caching
- **Comprehensive Analysis**: 7 specialized pages covering the complete clustering workflow

## Docker Quick Start
```bash
docker compose up
```
Then open
http://localhost:3000

### Prerequisites

- **Python 3.9+** with virtual environment
- **Node.js 18+** with pnpm package manager
- **Redis** (optional, for persistence)

### Backend Setup

```bash
# Activate virtual environment (REQUIRED)
source .venv/bin/activate

# Install dependencies
pip install -r server/requirements.txt

# Start Python backend server
python -m uvicorn server.clustering_api:app --reload --port 8000
```

### Frontend Setup

```bash
# Install dependencies
pnpm install

# Start Nuxt development server
pnpm run dev
```

### Redis Setup
```bash
# Required Docker !
docker run --name redis -d -p 6379:6379 redis
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Recommended: Docker Compose

For easier setup, you can use Docker Compose to start the entire application:

```bash
# Start both frontend and backend
docker-compose up

# Start in detached mode
docker-compose up -d
```

## Project Structure

```
├── components/              # Vue 3 interactive components
├── composables/             # Vue composition functions
├── pages/                   # Application pages (7 main views)
├── server/                  # FastAPI backend services
├── DISCO-main/              # DISCO research framework
├── docs/                    # Comprehensive documentation
```

## Development

```bash
# Frontend
pnpm run build              # Production build
pnpm run generate           # Static generation
pnpm run preview            # Preview production build

# Backend
python -m uvicorn server.clustering_api:app --reload --log-level debug
```

## Contributions and Acknowledgments

### Research Framework Integration

This project integrates cutting-edge research in clustering analysis:

- **DISCO Framework**: Internal evaluation metric for density-based clustering with noise labels (IEEE ICDM 2025 submission)
- **SHIP Framework**: Similarity-Hierarchy-Partition clustering framework ([arXiv:2502.14018](https://arxiv.org/abs/2502.14018))

### Core Technologies

- **Frontend**: Vue 3, Nuxt 3, TypeScript, D3.js, PapaParse
- **Backend**: FastAPI, Python, NumPy, Scikit-learn, SciPy, Pandas
- **Visualization**: D3.js, with custom interactive components
- **Infrastructure**: Redis caching, Docker containerization, pnpm package management

## 📄 License

This project is developed for academic research purposes. Please refer to individual framework licenses for specific components.
