from __future__ import annotations

import json

if __name__ == "__main__":
    """Execute the first code block of the app.ipynb notebook."""
    with open("app.ipynb", "r") as notebook:
        nb = json.load(notebook)
    idxs = [idx for idx, cell in enumerate(nb["cells"]) if cell["cell_type"] == "code"]
    exec("".join(nb["cells"][idxs[0]]["source"]))
