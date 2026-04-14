# Exoplanet Explorer

A powerful command-line interface (CLI) tool for astronomers and space enthusiasts to explore exoplanet data from the [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/).

## Features

- 🔭 **Search**: Query the NASA Exoplanet Archive TAP service with custom filters
- 🌍 **Earth-like Finder**: Identify potentially habitable exoplanets using Earth Similarity Index (ESI)
- 🏠 **Habitable Zone**: Find planets within the conservative or optimistic habitable zones
- 🤖 **ML Analysis**: Detect anomalies, cluster planets by characteristics, and identify uncertain measurements
- 📊 **Export**: Save results in CSV, JSON, or formatted table output

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Install from Source

```bash
git clone https://github.com/exoplanet-explorer/exoplanet-explorer.git
cd exoplanet-explorer
pip install -r requirements.txt
```

### Install as Package

```bash
pip install -e .
```

This will install the `exoplanet-explorer` command globally.

## Quick Start

```bash
# Search for exoplanets
python -m src.cli search --limit 10

# Find Earth-like candidates
python -m src.cli earth-like --min-radius 0.8 --max-radius 1.5

# Find planets in habitable zone
python -m src.cli habitable --conservative

# Analyze data with ML
python -m src.cli analyze --input data.csv --anomalies --clusters 4
```

## Usage

### Search Command

Search for exoplanets with custom filters:

```bash
# Basic search
exoplanet-explorer search --limit 20

# Custom columns
exoplanet-explorer search --columns pl_name,pl_rade,pl_orper,pl_insol --limit 50

# With WHERE clause
exoplanet-explorer search --where "pl_rade > 1.0 AND pl_orper < 365" --limit 100

# Filter by discovery method
exoplanet-explorer search --method "Transit" --order pl_rade --limit 50

# Export to CSV
exoplanet-explorer search --output results.csv --format csv
```

### Earth-like Command

Find potentially Earth-like exoplanets:

```bash
# Default parameters (ESI > 0.8, radius 0.8-1.5 Earth radii)
exoplanet-explorer earth-like --limit 50

# Custom parameters
exoplanet-explorer earth-like \
    --min-esi 0.85 \
    --min-radius 0.9 \
    --max-radius 1.2 \
    --min-period 250 \
    --max-period 450
```

### Habitable Command

Find planets in the habitable zone:

```bash
# Conservative habitable zone
exoplanet-explorer habitable --conservative --limit 100

# Optimistic habitable zone
exoplanet-explorer habitable --limit 100
```

### Analyze Command

Perform machine learning analysis on exoplanet data:

```bash
# Detect anomalies
exoplanet-explorer analyze --input exoplanets.csv --anomalies

# Cluster into groups
exoplanet-explorer analyze --input exoplanets.csv --clusters 4

# Find uncertain measurements
exoplanet-explorer analyze --input exoplanets.csv --uncertain

# Combined analysis
exoplanet-explorer analyze \
    --input exoplanets.csv \
    --anomalies \
    --clusters 5 \
    --uncertain \
    --output analysis_results.csv
```

## Command-Line Options

### Global Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable verbose/debug output |
| `--version` | Show version information |
| `-h, --help` | Show help message |

### Search Options

| Option | Description | Default |
|--------|-------------|---------|
| `-t, --table` | Target table (ps, pscomppars, koi_cumulative, k2pandc) | ps |
| `-c, --columns` | Comma-separated column names | pl_name,pl_rade,... |
| `-w, --where` | Custom WHERE clause | - |
| `-l, --limit` | Maximum results | 100 |
| `-o, --order` | Order by column (prefix with - for DESC) | - |
| `-m, --method` | Filter by discovery method | - |
| `-O, --output` | Output file path | - |
| `-f, --format` | Output format (csv, json, table) | table |

## Environment Variables

Configure the application via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `EXOPLANET_EXPLORER_TIMEOUT` | Request timeout in seconds | 30 |
| `EXOPLANET_EXPLORER_RETRIES` | Max retry attempts | 3 |
| `EXOPLANET_EXPLORER_LIMIT` | Default query limit | 100 |

Example:
```bash
export LOG_LEVEL=DEBUG
export EXOPLANET_EXPLORER_TIMEOUT=60
exoplanet-explorer search --limit 10
```

## Project Structure

```
exoplanet_explorer/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── api/
│   │   ├── __init__.py
│   │   ├── tap_client.py    # NASA TAP API client
│   │   └── query_builder.py # ADQL query builder
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── filters.py       # Scientific filters
│   │   ├── metrics.py       # Planetary metrics (ESI, HZ)
│   │   └── discovery.py     # ML-based discovery
│   ├── models/
│   │   ├── __init__.py
│   │   └── exoplanet.py     # Exoplanet dataclass
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py        # Logging configuration
│   │   └── helpers.py       # Utility functions
│   └── cli.py               # CLI entry point
├── tests/
│   ├── __init__.py
│   └── test_api.py          # API tests
├── requirements.txt         # Dependencies
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Available TAP Tables

| Table | Description |
|-------|-------------|
| `ps` | Confirmed exoplanets (default) |
| `pscomppars` | Planet comparison parameters |
| `koi_cumulative` | Kepler Object of Interest cumulative |
| `k2pandc` | K2 planet candidates |

## Common Columns

| Column | Description |
|--------|-------------|
| `pl_name` | Planet name |
| `hostname` | Host star name |
| `pl_rade` | Planet radius (Earth radii) |
| `pl_mass` | Planet mass (Earth masses) |
| `pl_orper` | Orbital period (days) |
| `pl_orbsmax` | Semi-major axis (AU) |
| `pl_insol` | Insolation flux (Earth units) |
| `pl_eccen` | Orbital eccentricity |
| `disc_method` | Discovery method |
| `st_mass` | Stellar mass (Solar masses) |
| `st_rad` | Stellar radius (Solar radii) |
| `st_teff` | Stellar temperature (Kelvin) |
| `st_lum` | Stellar luminosity (Solar units) |

## Examples

### Finding Super-Earths in Habitable Zones

```bash
# First, get planets with radius between 1.25 and 2 Earth radii
exoplanet-explorer search \
    --columns pl_name,pl_rade,pl_orper,pl_insol,hostname \
    --where "pl_rade BETWEEN 1.25 AND 2.0" \
    --limit 100 \
    --output super_earths.csv
```

### Analyzing Discovery Methods

```bash
# Get all transit discoveries
exoplanet-explorer search \
    --method Transit \
    --columns pl_name,pl_rade,pl_orper,disc_method \
    --limit 500 \
    --format json \
    --output transit_planets.json
```

### Pipeline Example

```bash
# Create a comprehensive dataset
exoplanet-explorer search \
    --columns pl_name,pl_rade,pl_mass,pl_orper,pl_orbsmax,pl_insol,pl_eccen,st_mass,st_rad,st_teff,disc_method,hostname \
    --limit 1000 \
    --output all_planets.csv

# Analyze for anomalies and clustering
exoplanet-explorer analyze \
    --input all_planets.csv \
    --anomalies \
    --clusters 5 \
    --output analyzed_planets.csv
```

## Tests
	
search --limit 5
habitable --conservative
earth-like --min-radius 0.8 --max-radius 1.5
search --columns ... --where "pl_rade BETWEEN 0.8 AND 1.5"
analyze --input all_planets.csv --anomalies
search --method Transit --limit 10
search --where "hostname LIKE '%TRAPPIST%'"
search --where "pl_insol BETWEEN 0.8 AND 1.2"
search --where "pl_rade < 1.3 AND pl_insol BETWEEN 0.8 AND 1.2"
python -m unittest tests.test_api

## Development

### Running Tests

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=src
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Linting
ruff check src/ tests/
```

## API Reference

### TAPClient

```python
from src.api.tap_client import TAPClient

with TAPClient(timeout=60) as client:
    df = client.query("SELECT * FROM ps LIMIT 10")
    
    # Cone search
    results = client.cone_search(
        ra=285.0,
        dec=65.0,
        radius=1.0,
        columns=["pl_name", "pl_rade"]
    )
```

### QueryBuilder

```python
from src.api.query_builder import QueryBuilder
from src.api.tap_client import TAPClient

client = TAPClient()

df = (QueryBuilder()
    .select(["pl_name", "pl_rade", "pl_orper"])
    .from_table("ps")
    .where("rowtype", "=", "planet")
    .where_range("pl_rade", 0.8, 1.5)
    .order("pl_insol", ascending=True)
    .set_limit(100)
    .execute(client))
```

### Filters

```python
from src.analysis.filters import CandidateFilter

# Earth-like planets
earth_like = CandidateFilter.earth_like(
    df,
    min_radius=0.8,
    max_radius=1.5,
    min_period=200,
    max_period=500
)

# Habitable zone
hz_planets = CandidateFilter.in_habitable_zone(df, conservative=True)

# High confidence
high_conf = CandidateFilter.high_confidence(
    df,
    min_signals=3,
    require_radial_velocity=False
)
```

## Acknowledgments

Data provided by the NASA Exoplanet Archive, which is operated by the California Institute of Technology, under contract with the National Aeronautics and Space Administration under the Exoplanet Exploration Program.

**Citation**: When using data from the NASA Exoplanet Archive, please cite:
> Akeson, R. L., et al. "The NASA Exoplanet Archive: Data and Tools for Exoplanet Research." Publications of the Astronomical Society of the Pacific 125.930 (2013): 989.

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Next Steps / Future Enhancements

- [ ] Async support with aiohttp for improved performance
- [ ] Interactive TUI with Textual/ Rich
- [ ] Web interface with FastAPI
- [ ] Additional ML models (autoencoders, GMMs)
- [ ] Transit light curve analysis
- [ ] Radial velocity curve fitting
- [ ] Multi-planet system dynamics
- [ ] Integration with other archives (MAST, SIMBAD)
