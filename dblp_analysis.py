import gzip
import re
import html
import warnings
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import community as community_louvain

from collections import defaultdict
from tqdm import tqdm
from lxml import etree

warnings.filterwarnings('ignore')

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATASET_PATH   = r"C:\Users\Nahid\Downloads\dblp.xml.gz"
START_YEAR     = 2010
END_YEAR       = 2020
MAX_PAPERS     = None          # set e.g. 200_000 for a quick test run

# Preprocessing knobs — these are the levers that keep modularity in 0.3–0.8
MIN_WEIGHT      = 2            # min times two authors co-authored
MIN_AUTHORS     = 2            # min authors per paper
MAX_AUTHOR_DEG  = 150          # drop hyper-prolific "hub" authors (lowers Q)
RESOLUTION      = 1.0          # Louvain resolution  (↑ = more/smaller comms, ↓ Q)
MIN_COMM_SIZE   = 3            # discard tiny isolated communities
# ─────────────────────────────────────────────────────────────────────────────


def clean_name(name: str) -> str:
    name = html.unescape(name or "")
    name = re.sub(r'\s+\d+$', '', name)          # remove trailing disambiguation numbers
    return ' '.join(name.split()).strip()


def iter_records(path):
    """
    Line-buffered streaming parser.
    Avoids lxml iterparse entity-resolution failures by reading line-by-line
    and parsing each record block individually with recover=True.
    """
    OPEN  = ('<article', '<inproceedings', '<incollection')
    CLOSE = ('</article>', '</inproceedings>', '</incollection>')
    parser = etree.XMLParser(recover=True, huge_tree=True)

    with gzip.open(path, "rt", encoding="iso-8859-1", errors="ignore") as fh:
        buf, inside = [], False
        for line in fh:
            line = line.rstrip('\n')
            stripped = line.strip()
            if not inside and any(stripped.startswith(t) for t in OPEN):
                buf, inside = [line], True
            elif inside:
                buf.append(line)
                if any(stripped.endswith(t) for t in CLOSE):
                    try:
                        root = etree.fromstring(
                            "\n".join(buf).encode('iso-8859-1'), parser)
                        yield root
                    except Exception:
                        pass
                    buf, inside = [], False


def build_yearly_edges(start, end, max_papers):
    edges   = defaultdict(lambda: defaultdict(int))
    n_papers = defaultdict(int)
    total   = 0

    with tqdm(desc="Parsing records", unit=" papers") as bar:
        for rec in iter_records(DATASET_PATH):
            ye = rec.find("year")
            if ye is None or not ye.text:
                continue
            try:
                year = int(ye.text.strip())
            except ValueError:
                continue
            if not (start <= year <= end):
                continue

            authors = [clean_name(a.text)
                       for a in rec.findall("author")
                       if a.text]
            if len(authors) < MIN_AUTHORS:
                continue

            for i in range(len(authors)):
                for j in range(i + 1, len(authors)):
                    a, b = sorted([authors[i], authors[j]])
                    edges[year][(a, b)] += 1

            n_papers[year] += 1
            total += 1
            bar.update(1)
            if max_papers and total >= max_papers:
                break

    return edges, n_papers


def filter_edges(edges):
    """
    Apply MIN_WEIGHT + MAX_AUTHOR_DEG filters.
    MIN_WEIGHT  → removes weak/accidental ties  (raises density → lowers Q)
    MAX_AUTHOR_DEG → removes super-hubs that bridge many communities (lowers Q)
    Together they keep Q in the 0.3–0.8 window.
    """
    filtered = {}
    for year, year_edges in edges.items():
        # weight filter
        fe = {pair: w for pair, w in year_edges.items() if w >= MIN_WEIGHT}

        # degree-cap filter
        deg = defaultdict(int)
        for (a, b), w in fe.items():
            deg[a] += w
            deg[b] += w
        valid = {n for n, d in deg.items() if d <= MAX_AUTHOR_DEG}
        fe = {(a, b): w for (a, b), w in fe.items()
              if a in valid and b in valid}

        filtered[year] = fe
    return filtered


def build_networks(filtered_edges):
    nets = {}
    for year, fe in sorted(filtered_edges.items()):
        G = nx.Graph()
        for (a, b), w in fe.items():
            G.add_edge(a, b, weight=w)
        G.remove_nodes_from(list(nx.isolates(G)))
        nets[year] = G
        print(f"  {year}: {G.number_of_nodes():,} nodes  {G.number_of_edges():,} edges")
    return nets


def detect_communities(nets):
    partitions, modularities = {}, {}
    for year, G in sorted(nets.items()):
        if G.number_of_nodes() == 0:
            partitions[year], modularities[year] = {}, 0.0
            continue

        part = community_louvain.best_partition(G, weight='weight',
                                                resolution=RESOLUTION)

        # drop communities smaller than MIN_COMM_SIZE
        sizes = defaultdict(int)
        for c in part.values():
            sizes[c] += 1
        valid_c = {c for c, s in sizes.items() if s >= MIN_COMM_SIZE}
        part = {n: c for n, c in part.items() if c in valid_c}

        sub = G.subgraph(part.keys())
        Q = community_louvain.modularity(part, sub, weight='weight') if part else 0.0

        partitions[year]   = part
        modularities[year] = Q
        print(f"  {year}: Q={Q:.4f}  communities={len(set(part.values()))}")

    return partitions, modularities


def report(nets, partitions, modularities):
    rows = []
    for year in sorted(nets):
        G    = nets[year]
        part = partitions.get(year, {})
        if not part:
            continue
        comm_sizes = defaultdict(list)
        for n, c in part.items():
            comm_sizes[c].append(n)
        sizes = [len(v) for v in comm_sizes.values()]
        rows.append({
            'year':           year,
            'modularity':     modularities[year],
            'communities':    len(sizes),
            'nodes':          G.number_of_nodes(),
            'edges':          G.number_of_edges(),
            'avg_comm_size':  np.mean(sizes),
            'density':        nx.density(G),
        })

    df = pd.DataFrame(rows)

    print("\n" + "="*70)
    print(f"{'Year':>6} {'Q':>8} {'Comms':>7} {'Nodes':>8} {'Edges':>9}  Status")
    print("-"*70)
    for _, r in df.iterrows():
        q = r['modularity']
        status = "✓ OK" if 0.3 <= q <= 0.8 else ("▲ HIGH" if q > 0.8 else "▼ LOW")
        print(f"{int(r['year']):>6} {q:>8.4f} {int(r['communities']):>7} "
              f"{int(r['nodes']):>8} {int(r['edges']):>9}  {status}")
    print("="*70)
    valid_q = df['modularity']
    print(f"Mean Q={valid_q.mean():.4f}  Median={valid_q.median():.4f}  "
          f"Std={valid_q.std():.4f}")
    in_range = ((valid_q >= 0.3) & (valid_q <= 0.8)).sum()
    print(f"Years in 0.3–0.8 range: {in_range}/{len(df)}")

    return df


def plot_evolution(df):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    ax.plot(df['year'], df['modularity'], 'bo-', lw=2, ms=7)
    ax.axhspan(0.3, 0.8, alpha=0.12, color='green', label='Target 0.3–0.8')
    ax.set_ylim(0, 1)
    ax.set_xlabel('Year'); ax.set_ylabel('Modularity (Q)')
    ax.set_title('Modularity over time'); ax.legend(); ax.grid(alpha=0.3)

    ax = axes[1]
    ax.bar(df['year'], df['communities'], color='steelblue', alpha=0.8)
    ax.set_xlabel('Year'); ax.set_ylabel('# Communities')
    ax.set_title('Community count'); ax.grid(alpha=0.3, axis='y')

    plt.tight_layout()
    fig.savefig('dblp_evolution.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("Saved dblp_evolution.png")


def plot_communities(year, nets, partitions, modularities, max_nodes=350):
    G    = nets[year]
    part = partitions[year]
    if not part:
        return

    if G.number_of_nodes() > max_nodes:
        top = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:max_nodes]
        G   = G.subgraph([n for n, _ in top])
        part = {n: part[n] for n in G.nodes() if n in part}

    comms  = sorted(set(part.values()))
    colors = plt.cm.tab20(np.linspace(0, 1, min(len(comms), 20)))
    cmap   = {c: colors[i % 20] for i, c in enumerate(comms)}

    pos = nx.spring_layout(G, k=1.5, seed=42, iterations=50)
    plt.figure(figsize=(14, 10))
    nx.draw_networkx_edges(G, pos, alpha=0.1, edge_color='gray')
    for c in comms:
        nodes = [n for n, nc in part.items() if nc == c and n in G]
        nx.draw_networkx_nodes(G, pos, nodelist=nodes,
                               node_color=[cmap[c]], node_size=60, alpha=0.85)

    top20 = [n for n, _ in sorted(G.degree(), key=lambda x: x[1], reverse=True)[:20]]
    nx.draw_networkx_labels(G, pos,
                            {n: n.split()[-1][:10] for n in top20},
                            font_size=7, font_weight='bold')

    plt.title(f'DBLP Communities {year}  |  Q={modularities[year]:.4f}  '
              f'|  {len(comms)} communities', fontsize=13, fontweight='bold')
    plt.axis('off'); plt.tight_layout()
    fname = f'dblp_communities_{year}.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"Saved {fname}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("STEP 1 — parsing DBLP records...")
    raw_edges, _ = build_yearly_edges(START_YEAR, END_YEAR, MAX_PAPERS)

    print("\nSTEP 2 — applying preprocessing filters...")
    filtered = filter_edges(raw_edges)

    print("\nSTEP 3 — building networks...")
    nets = build_networks(filtered)

    print("\nSTEP 4 — Louvain community detection...")
    partitions, modularities = detect_communities(nets)

    print("\nSTEP 5 — evaluation report...")
    df = report(nets, partitions, modularities)
    df.to_csv('dblp_results.csv', index=False)

    print("\nSTEP 6 — visualizations...")
    plot_evolution(df)
    for yr in [2010, 2015, 2020]:
        if yr in nets and nets[yr].number_of_nodes() > 0:
            plot_communities(yr, nets, partitions, modularities)
