from __future__ import annotations
import os, subprocess, threading, time, signal
from pathlib import Path
from settings import PIPELINE_ROOT, LOG_DIR, MONITORING_ROOT
from config_store import get_all

COLLECTORS = {
    "reddit_discovery": "reddit_discovery",
    "reddit_comments": "reddit_comments",
    "youtube": "youtube",
    "x": "x",
    "finance": "finance",
}

class ProcessManager:
    def __init__(self, python_exe: str):
        self.python_exe = python_exe
        self._lock = threading.RLock()
        self._procs = {}
        self._meta = {name: {"started_at": None, "finished_at": None, "exit_code": None, "duration": None, "last_status": "never"} for name in COLLECTORS}
        self._chains = {"reddit_full": {"running": False, "stage": "idle", "last_status": "never", "message": ""}}

    def _env(self):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        cfg = get_all(False)
        # Only native environment settings are exported. Non-native tuning is
        # applied by runtime_wrapper.py in memory after importing the original module.
        for k in [
            "REDDIT_FIREFOX_PROFILE", "YOUTUBE_API_KEY", "YOUTUBE_DAILY_QUOTA_BUDGET",
            "YOUTUBE_REGIONS_PER_DAY", "AUTHOR_HASH_SALT", "X_ACCOUNTS_JSON",
            "X_OUTPUT_ROOT", "PROJECT_AUTHOR_SALT", "FRED_API_KEY", "FINANCIAL_RUN_ID",
        ]:
            v = cfg.get(k, "")
            if v != "": env[k] = v
        return env

    def start(self, name):
        if name not in COLLECTORS: raise KeyError(name)
        with self._lock:
            p = self._procs.get(name)
            if p and p.poll() is None:
                return False, f"{name} is already running (PID {p.pid})."

            # Reddit stages share the same Firefox profile and native handoff files.
            # Running them concurrently can lock the profile and make stage 2 read an
            # incomplete checkpoint. Keep the native two-stage flow sequential.
            if name == "reddit_discovery" and self.status("reddit_comments")["running"]:
                return False, "reddit_comments is running. Stop it before starting discovery."
            if name == "reddit_comments" and self.status("reddit_discovery")["running"]:
                return False, "reddit_discovery is still running. Use Full Reddit Flow or wait until discovery finishes."

            log_path = LOG_DIR / f"{name}.log"
            log = open(log_path, "a", encoding="utf-8", buffering=1)
            stamp = time.strftime('%Y-%m-%d %H:%M:%S')
            log.write(f"\n\n===== OVERLAY START {stamp} | {name} =====\n")
            log.flush()
            wrapper = MONITORING_ROOT / "runtime_wrapper.py"
            cmd = [self.python_exe, "-u", str(wrapper), COLLECTORS[name]]
            kwargs = dict(cwd=str(PIPELINE_ROOT), env=self._env(), stdout=log, stderr=subprocess.STDOUT)
            if os.name == 'nt': kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
            else: kwargs['start_new_session'] = True
            p = subprocess.Popen(cmd, **kwargs)
            self._procs[name] = p
            self._meta[name].update(started_at=time.time(), finished_at=None, exit_code=None, duration=None, last_status="running")
            threading.Thread(target=self._watch, args=(name,p,log), daemon=True).start()
            return True, f"Started {name} (PID {p.pid})."

    def _watch(self, name, p, log):
        code = p.wait(); end = time.time()
        with self._lock:
            start = self._meta[name].get('started_at') or end
            self._meta[name].update(finished_at=end, exit_code=code, duration=end-start, last_status="success" if code == 0 else "failed")
        log.write(f"===== OVERLAY END | exit={code} | duration={end-start:.1f}s =====\n"); log.flush(); log.close()

    def stop(self, name):
        with self._lock:
            p = self._procs.get(name)
            if not p or p.poll() is not None: return False, f"{name} is not running."
            pid = p.pid
        try:
            if os.name == 'nt': subprocess.run(["taskkill","/PID",str(pid),"/T","/F"], capture_output=True, timeout=20)
            else: os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try: p.terminate()
            except Exception: pass
        return True, f"Stop requested for {name} (PID {pid})."

    def status(self, name):
        with self._lock:
            p=self._procs.get(name); m=dict(self._meta[name]); running=bool(p and p.poll() is None)
            return {"name":name,"running":running,"pid":p.pid if running else None, **m}

    def all_status(self): return {name:self.status(name) for name in COLLECTORS}

    def chain_status(self):
        with self._lock:
            return dict(self._chains["reddit_full"])

    def start_reddit_full(self):
        with self._lock:
            state = self._chains["reddit_full"]
            if state["running"]:
                return False, "Full Reddit Flow is already running."
            if self.status("reddit_discovery")["running"] or self.status("reddit_comments")["running"]:
                return False, "A Reddit stage is already running. Stop it first or wait for it to finish."
            state.update(running=True, stage="starting_discovery", last_status="running", message="Starting discovery")
        threading.Thread(target=self._run_reddit_full, daemon=True).start()
        return True, "Full Reddit Flow started: Discovery -> Raw JSON/Comments."

    def _run_reddit_full(self):
        try:
            with self._lock:
                self._chains["reddit_full"].update(stage="discovery", message="Running parent-post discovery")
            ok, msg = self.start("reddit_discovery")
            if not ok:
                raise RuntimeError(msg)
            while self.status("reddit_discovery")["running"]:
                time.sleep(1)
            if self.status("reddit_discovery").get("last_status") != "success":
                raise RuntimeError("Discovery did not finish successfully; Raw JSON stage was not started.")

            with self._lock:
                self._chains["reddit_full"].update(stage="handoff", message="Discovery finished; handing parent URLs to Raw JSON pipeline")
            time.sleep(0.5)
            ok, msg = self.start("reddit_comments")
            if not ok:
                raise RuntimeError(msg)
            with self._lock:
                self._chains["reddit_full"].update(stage="raw_json", message="Running Reddit Raw JSON + comment audit")
            while self.status("reddit_comments")["running"]:
                time.sleep(1)
            if self.status("reddit_comments").get("last_status") != "success":
                raise RuntimeError("Raw JSON/comments stage failed.")
            with self._lock:
                self._chains["reddit_full"].update(running=False, stage="done", last_status="success", message="Discovery and Raw JSON/comments completed")
        except Exception as e:
            with self._lock:
                self._chains["reddit_full"].update(running=False, stage="failed", last_status="failed", message=str(e))
