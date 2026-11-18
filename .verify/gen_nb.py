"""Fork-only: execute the local image-converter doc cells and splice the new cells' real outputs into the notebooks."""
import json
import pathlib

import jupytext
import nbclient
import nbformat

root = pathlib.Path("doc/code/converters")


def run(cells, cwd):
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell(c) for c in cells]
    nbclient.NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(cwd)}}).execute()
    return nb.cells


# 3_image_converters: run every code cell up to and including the new one (all local converters, no endpoints)
py = jupytext.read(root / "3_image_converters.py")
code = [c.source for c in py.cells if c.cell_type == "code"]
end = next(i for i, s in enumerate(code) if "ImageNoiseConverter(" in s)
done = run(code[: end + 1], root)
noise_outputs = done[-1].outputs
md = next(c.source for c in py.cells if c.cell_type == "markdown" and "### ImageNoiseConverter" in c.source)

path = root / "3_image_converters.ipynb"
nb = json.load(open(path, encoding="utf-8"))
ids = [int(c["id"]) for c in nb["cells"] if str(c.get("id", "")).isdigit()]
idx = next(i for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code" and "ImageRotationConverter(" in "".join(c["source"]))
src_lines = lambda s: [l + "\n" for l in s.split("\n")[:-1]] + [s.split("\n")[-1]]
new_md = {"cell_type": "markdown", "id": str(max(ids) + 1), "metadata": {}, "source": src_lines(md)}
new_code = {"cell_type": "code", "execution_count": None, "id": str(max(ids) + 2), "metadata": {},
            "outputs": [json.loads(json.dumps(o)) for o in noise_outputs], "source": src_lines(code[end])}
for o in new_code["outputs"]:
    o.pop("execution_count", None) if o["output_type"] != "execute_result" else None
nb["cells"][idx + 1:idx + 1] = [new_md, new_code]
open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
print("inserted at", idx + 1, [o["output_type"] for o in new_code["outputs"]])

# 0_converters: regenerate the modality table output only
py0 = jupytext.read(root / "0_converters.py")
table_src = next(c.source for c in py0.cells if c.cell_type == "code" and "get_converter_modalities" in c.source)
out = run([table_src], root)[0].outputs
table = "".join(o["text"] for o in out if o["output_type"] == "stream" and "Input Modality" in o["text"])
path0 = root / "0_converters.ipynb"
nb0 = json.load(open(path0, encoding="utf-8"))
cell = next(c for c in nb0["cells"] if c["cell_type"] == "code" and "get_converter_modalities" in "".join(c["source"]))
hits = [o for o in cell["outputs"] if o["output_type"] == "stream" and "Input Modality" in "".join(o["text"])]
assert len(hits) == 1
hits[0]["text"] = src_lines(table)
open(path0, "w", encoding="utf-8", newline="\n").write(json.dumps(nb0, indent=1, ensure_ascii=False) + "\n")
print(table)
