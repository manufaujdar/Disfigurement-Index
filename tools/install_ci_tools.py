"""Install four SHA256-pinned Linux/x86_64 quality CLIs; execute no setup scripts."""
import hashlib
import platform
import sys
import tarfile
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

TOOLS = {
    "actionlint": ("https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz", "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"),
    "betterleaks": ("https://github.com/betterleaks/betterleaks/releases/download/v1.8.1/betterleaks_1.8.1_linux_x64.tar.gz", "efa407244e1ea8e35f582b8a42becdeac08bdead04f68eb752adda722d583c2a"),
    "lychee": ("https://github.com/lycheeverse/lychee/releases/download/lychee-v0.24.2/lychee-x86_64-unknown-linux-gnu.tar.gz", "1f4e0ef7f6554a6ed33dd7ac144fb2e1bbed98598e7af973042fc5cd43951c9a"),
    "zizmor": ("https://github.com/zizmorcore/zizmor/releases/download/v1.30.1/zizmor-x86_64-unknown-linux-gnu.tar.gz", "e65324f4430c2717591937edcec90ccbefaf14c174f8ec9415e03ca875b46e1a"),
}


def executable(data, digest, name):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"{name}: archive checksum mismatch")
    with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as archive:
        members = [m for m in archive if m.isfile() and Path(m.name).name == name]
        if len(members) != 1:
            raise ValueError(f"{name}: expected one regular executable")
        return archive.extractfile(members[0]).read()


def main():
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        raise SystemExit("CI bootstrap supports Linux/x86_64; use native pinned installs locally")
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 tools/install_ci_tools.py DESTINATION")
    target = Path(sys.argv[1]).resolve()
    target.mkdir(parents=True, exist_ok=True)
    for name, (url, digest) in TOOLS.items():
        with urlopen(url, timeout=120) as response:
            data = response.read(100 * 1024 * 1024 + 1)
        if len(data) > 100 * 1024 * 1024:
            raise SystemExit(f"{name}: unexpected archive size")
        path = target / name
        path.write_bytes(executable(data, digest, name))
        path.chmod(0o755)
        print(f"Installed verified {name}")


if __name__ == "__main__":
    main()
