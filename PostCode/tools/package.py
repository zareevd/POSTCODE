"""Build and verify the portable source package without local user data."""
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
files = [ROOT / name for name in ("run.py", "start.cmd", "README.md", "db/.gitkeep")]
for directory, extensions in (("src", {".py", ".css"}), ("docs", {".md"}),
                              ("tests", {".py"}), ("tools", {".py"})):
    files.extend(p for p in (ROOT / directory).rglob("*") if p.suffix in extensions)
files.extend((ROOT / "sites/pochtatech-premium/dist/assets").glob("golos-*.woff2"))
output = ROOT / "deliverables/PostCode-MVP.zip"
output.parent.mkdir(exist_ok=True)
with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, path.relative_to(ROOT))
with tempfile.TemporaryDirectory() as directory:
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        archive.extractall(directory)
    subprocess.run([sys.executable, "tests/integration/test_local_mvp.py"], cwd=directory, check=True)
    subprocess.run([sys.executable, "run.py", "--help"], cwd=directory, check=True)
print(f"Verified: {output.name} ({output.stat().st_size} bytes)")
