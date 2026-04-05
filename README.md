# ecrdashpy

Streamlit + Python implementation of the ecrdash reports dashboard.

## Multipage Streamlit App

This app reproduces the core ecrdash dashboard experience using Streamlit:

- Summary cards (total runs, runtime, input/output size, averages)
- Charts:
	- report runs per tool
	- runtime trend by day
	- report runs per infra
	- memory by tool per day
- Recent runs table and full report explorer filters
- Country-level location map

Pages:

- Home: Dashboard.py
- Help: pages/4_Help.py

## Run Locally

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

	```bash
	pip install -r requirements.txt
	```

3. Start the app:

	```bash
	streamlit run Dashboard.py
	```

4. Open the local URL shown by Streamlit in your browser.

## Data Source

Default source:

- https://github.com/ghoshted/ecrdash/tree/main/reports_output_dir

The app fetches report JSON files from that repository path at runtime.

Fallback behavior:

- If remote fetch fails, it reads local files from `reports_output_dir/`.
- If neither remote nor local files are available, it uses synthetic sample data.

Supported fields include:

- `tool.name`, `tool.version`, `tool.package_version`
- `start_time`, `end_time`, `duration`
- `input_size_bytes`, `final_outputs_size_bytes`
- `memory_used`, `cpu_cores_assigned`, `cpu_cores_used`, `gpu_cores_used`
- `infra[].infra_name`
- `location.address.addressCountry` (used for map)

If no files are present, the app uses synthetic sample data so pages still render.

## Project Structure

```
.
├── Dashboard.py
├── pages
│   └── 4_Help.py
├── requirements.txt
└── utils
	└── data.py
```
