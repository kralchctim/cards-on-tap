import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent
TIM_DIR = ROOT_DIR / "tim"
STEVE_DIR = ROOT_DIR / "steve"
VENV_ACTIVATE = ROOT_DIR / ".venv" / "bin" / "activate"
BANNER_PATH = TIM_DIR / "banner.png"
ICONS_DIR = ROOT_DIR / "icons"
TIM_ICON_PATH = ICONS_DIR / "tim.png"
STEVE_ICON_PATH = ICONS_DIR / "steve.png"
LOG_DIR = ROOT_DIR / ".launcher_logs"

TIM_APP_PATH = TIM_DIR / "app.py"
STEVE_APP_PATH = ROOT_DIR / "steve" / "ui" / "streamlit_app.py"

TIM_PORT = 8501
STEVE_PORT = 8502


def _python_for_spawning() -> str:
    """Return the venv's Python *shim path* (do not resolve symlinks).

    Resolving `.venv/bin/python3.11` → Homebrew breaks the venv: the child then
    uses system site-packages and hits `No module named streamlit`.
    """
    venv_bin_dir = ROOT_DIR / ".venv" / "bin"

    for name in ("python3.11", "python3", "python"):
        candidate = venv_bin_dir / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    exe = Path(sys.executable)
    if exe.is_file() and os.access(exe, os.X_OK):
        try:
            exe.relative_to(venv_bin_dir.resolve())
            return str(exe)
        except ValueError:
            pass

    raise FileNotFoundError(
        f"No usable Python in {venv_bin_dir}. "
        "Recreate the venv or ensure python3.11 exists under .venv/bin."
    )


def _read_log_tail(log_path: Path, max_chars: int = 6000) -> str:
    if not log_path.is_file():
        return "(no log file yet)"
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"(could not read log: {exc})"
    return text[-max_chars:] if len(text) > max_chars else text


def launch_streamlit(script_path: Path, run_from_dir: Path, port: int, log_name: str) -> subprocess.Popen:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{log_name}.log"

    python_bin = _python_for_spawning()

    cmd = [
        python_bin,
        "-m",
        "streamlit",
        "run",
        str(script_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]

    env = os.environ.copy()
    venv_bin = str(ROOT_DIR / ".venv" / "bin")
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = str(ROOT_DIR / ".venv")

    header = (
        f"\n\n===== spawn {time.strftime('%Y-%m-%d %H:%M:%S')} "
        f"port={port} cwd={run_from_dir} py={python_bin} =====\n"
        f"cmd: {' '.join(cmd)}\n"
    )
    with log_file.open("ab") as log_handle:
        log_handle.write(header.encode("utf-8", errors="replace"))
        proc = subprocess.Popen(
            cmd,
            cwd=str(run_from_dir),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
    return proc


def _wait_child_or_report(proc: subprocess.Popen, log_file: Path, port: int, label: str) -> None:
    """If the child exits quickly, show log tail; otherwise confirm and open browser."""
    deadline = time.monotonic() + 2.5
    while time.monotonic() < deadline:
        rc = proc.poll()
        if rc is not None:
            st.error(
                f"{label} exited immediately (code {rc}). "
                f"See log: `{log_file}`\n\n{_read_log_tail(log_file)}"
            )
            return
        time.sleep(0.1)

    url = f"http://127.0.0.1:{port}"
    st.success(f"{label} is starting — if the tab does not open, go to {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass


def stop_process_on_port(port: int) -> bool:
    """Kill only processes listening on port (avoids stray matches from generic lsof)."""
    try:
        result = subprocess.run(
            [
                "lsof",
                "-nP",
                f"-iTCP:{port}",
                "-sTCP:LISTEN",
                "-t",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        pids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not pids:
            return False

        for pid in pids:
            subprocess.run(["kill", "-TERM", pid], check=False)
        return True
    except Exception:
        return False


st.set_page_config(page_title="Cards on Tap Launcher", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

    .stApp {
        background-color: #2B102B;
        font-family: 'Nunito', sans-serif;
    }

    html, body, [class*="css"]  {
        font-family: 'Nunito', sans-serif;
    }

    /* Avoid custom .stButton rules — they can break click targets in some layouts */

    /* Extra space below banner before icon row */
    .launcher-after-banner {
        height: 2.75rem;
        min-height: 2.75rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

if not VENV_ACTIVATE.exists():
    st.error(f"Virtual environment not found at: {VENV_ACTIVATE}")
    st.stop()

if not TIM_APP_PATH.exists():
    st.error(f"Missing file: {TIM_APP_PATH}")
if not STEVE_APP_PATH.exists():
    st.error(f"Missing file: {STEVE_APP_PATH}")

banner_left, banner_mid, banner_right = st.columns([1, 2, 1])
with banner_mid:
    banner_inner_left, banner_inner_mid, banner_inner_right = st.columns([1, 2, 1])
    with banner_inner_mid:
        if BANNER_PATH.exists():
            st.image(str(BANNER_PATH), width=390)

st.markdown('<div class="launcher-after-banner"></div>', unsafe_allow_html=True)

# Symmetric layout: Tim nudged toward centre from the left, Steve from the right (even spacing from midline)
tim_zone, _mid_gap, steve_zone = st.columns([2.2, 0.55, 2.2])

with tim_zone:
    _pad_left, tim_toward_centre = st.columns([1, 1])
    with tim_toward_centre:
        if TIM_ICON_PATH.exists():
            st.image(str(TIM_ICON_PATH), width=180)
        if st.button("Launch Tim App", key="launch_tim"):
            stop_process_on_port(TIM_PORT)
            time.sleep(0.35)
            try:
                proc = launch_streamlit(TIM_APP_PATH, TIM_DIR, TIM_PORT, "tim-app")
                _wait_child_or_report(proc, LOG_DIR / "tim-app.log", TIM_PORT, "Tim app")
            except Exception as exc:
                st.error(str(exc))

with steve_zone:
    steve_toward_centre, _pad_right = st.columns([1, 1])
    with steve_toward_centre:
        if STEVE_ICON_PATH.exists():
            st.image(str(STEVE_ICON_PATH), width=180)
        if st.button("Launch Steve App", key="launch_steve"):
            stop_process_on_port(STEVE_PORT)
            time.sleep(0.35)
            try:
                proc = launch_streamlit(STEVE_APP_PATH, STEVE_DIR, STEVE_PORT, "steve-ui")
                _wait_child_or_report(proc, LOG_DIR / "steve-ui.log", STEVE_PORT, "Steve app")
            except Exception as exc:
                st.error(str(exc))
