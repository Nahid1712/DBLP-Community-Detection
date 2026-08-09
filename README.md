# Adaptive DBLP Community Analyzer

A Python tool for analyzing **co-authorship networks** from the DBLP computer science bibliography.  
It builds yearly collaboration graphs, applies **Louvain community detection** with adaptive resolution tuning to achieve a target modularity range, and visualizes the network using a **SIR (Susceptible-Infected-Recovered) epidemic model analogy** for community spread dynamics.

---

## 🎯 Features

- **Efficient DBLP parsing**  
  Streams large gzipped XML files (e.g., `dblp.xml.gz`) without loading the entire file into memory.

- **Year-wise co-authorship graphs**  
  Builds weighted collaboration networks for each year (2000–2020 by default).

- **Adaptive modularity control**
  - Automatically adjusts the Louvain resolution parameter.
  - Applies edge densification/sharpening strategies.
  - Maintains modularity within a target range (default `0.3 – 0.8`).

- **SIR-style network visualization**

  Maps detected communities into epidemic states:

  | State | Meaning |
  |---|---|
  | **I (Infected)** | Largest community (active spreader) |
  | **C (Counter)** | Second-largest community (competing community) |
  | **R (Recovered)** | Medium-sized stable communities |
  | **S (Susceptible)** | Small vulnerable communities |

- **Animation frame generation**
  - Simulates infection spread from infected communities to neighboring susceptible nodes.

- **Comprehensive reporting**
  - Modularities
  - Community counts
  - Node and edge statistics
  - CSV export

- **Multi-panel evolution visualization**
  - Modularity evolution
  - Community count
  - Network size
  - Graph density

---

# 📦 Requirements

- Python 3.7+

Required libraries:

```
networkx
numpy
pandas
matplotlib
lxml
python-louvain
```

Install dependencies:

```bash
pip install networkx numpy pandas matplotlib lxml python-louvain
```

---

# 🚀 Usage

## 1. Download DBLP Dataset

Download the official DBLP XML dataset:

https://dblp.org/xml/

Place:

```
dblp.xml.gz
```

inside your project directory.

---

## 2. Configure Dataset Path

Open:

```
dblp_analyzer.py
```

Modify:

```python
path = r"path/to/your/dblp.xml.gz"
```

Example:

```python
path = r"D:\Dataset\dblp.xml.gz"
```

---

## 3. Run Analyzer

Execute:

```bash
python dblp_analyzer.py
```

Default configuration:

- Years: **2000–2020**
- Maximum papers: **1 million**
- Generates all visualizations automatically

---

# ⚙️ Custom Configuration

Modify parameters inside:

```python
if __name__ == "__main__":
```

Example:

```python
model = AdaptiveDBLPAnalyzer(path)

model.run(
    start=2005,
    end=2015,
    max_papers=500000,
    visualize_sir=True
)
```

---

# 🧠 How It Works

## 1. Graph Construction

The analyzer:

1. Parses DBLP XML records:
   - `<article>`
   - `<inproceedings>`

2. Extracts:
   - Publication year
   - Author information

3. Cleans author names.

4. Creates co-authorship edges:

Example:

```
Author A ---- Author B
      \        /
       \      /
        Author C
```

Each collaboration increases edge weight.

The result is a yearly weighted undirected graph.

---

# 2. Adaptive Modularity Control

The system applies Louvain community detection:

```python
community.best_partition()
```

The modularity score:

\[
Q = \frac{1}{2m}
\sum_{ij}
(A_{ij}-\frac{k_i k_j}{2m})
\delta(c_i,c_j)
\]


The algorithm automatically adjusts:

### If modularity is too high

```
Q > target_high
```

The graph is densified:

- Adds weak random connections
- Reduces excessive separation


### If modularity is too low

```
Q < target_low
```

The graph is sharpened:

- Removes weak edges
- Enhances community boundaries


Resolution adjustment:

```
Low modularity  → increase resolution
High modularity → decrease resolution
```

The process repeats until:

```
target_low <= Q <= target_high
```

---

# 3. SIR Community Mapping

Detected communities are sorted by size.

Mapping:

```
Largest community
        |
        ↓
       I

Second largest
        |
        ↓
       C

Medium communities
        |
        ↓
       R

Small communities
        |
        ↓
       S
```

Meaning:

| State | Interpretation |
|-|-|
| I | Dominant research community |
| C | Competitive research cluster |
| R | Established stable groups |
| S | Emerging/small communities |

---

# 4. Visualization

Generated outputs:

## Evolution Analysis

A 2×2 dashboard:

- Modularity trend
- Community evolution
- Node growth
- Network density


## SIR Network Visualization

For each year:

```
sir_year_YYYY.png
```

Contains:

- Sampled network
- Community structure
- SIR state colors


## Animation Frames

Optional:

```
community_viz/sir_frames/
```

Shows infection spreading:

```
I → Neighbor Communities → S
```

---

# 📊 Example Output

Example:

```
============================================================
FINAL REPORT
============================================================

2000: Q=0.4977 | ✅ IN RANGE | Nodes=17,037 | Communities=4774

2001: Q=0.4978 | ✅ IN RANGE | Nodes=18,909 | Communities=5072

...

2020: Q=0.4184 | ✅ IN RANGE | Nodes=226,796 | Communities=20843


============================================================

Statistics:

Average Modularity: 0.4823

Std Deviation: 0.0247

Years in target range:

21/21 (100%)
```

---

# 📁 Project Structure

```
.
├── dblp_analyzer.py
│
├── community_viz/
│   ├── evolution_all_years.png
│   ├── sir_year_2000.png
│   ├── sir_year_2001.png
│   └── sir_frames/
│
├── community_analysis_results.csv
│
└── README.md
```

---

# 🔬 Future Improvements

Possible extensions:

## Advanced Community Detection

Replace Louvain with:

- Leiden Algorithm
- Infomap
- Girvan-Newman


## Temporal Community Tracking

Add:

- Community persistence
- Jaccard similarity
- Research group evolution


## Metadata Integration

Include:

- Citation impact
- Venue information
- Research topics
- Author ranking


## Machine Learning Extensions

Possible additions:

- Graph Neural Networks
- Node embeddings
- Link prediction
- Community forecasting

---

# 🤝 Contributing

Contributions are welcome.

If you find bugs or have improvement ideas:

1. Open an issue
2. Submit a pull request
3. Share suggestions

---

# 📄 License

This project is released under the MIT License.

See:

```
LICENSE
```

for details.

---

# 🙏 Acknowledgements

Special thanks to:

- DBLP team for providing open bibliographic data  
  https://dblp.org/

- NetworkX developers

- python-louvain contributors

- The research community advancing network science and bibliometrics
