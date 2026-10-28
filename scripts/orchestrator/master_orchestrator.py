#!/usr/bin/env python3
"""
ISO Tracker - Master Orchestrator (Fase 5)
Consolidates all phases into single entry point
Execution: manual or via Task Scheduler/cron
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares")
CONFIG = ROOT / "config" / "orchestrator.json"
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

class ISOOrchestrator:
    def __init__(self):
        with open(CONFIG, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def log(self, msg):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file = LOG_DIR / f"orchestrator_{datetime.now().strftime('%Y-%m-%d')}.log"
        line = f"[{ts}] {msg}"
        print(line)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    
    def run_script(self, script_path):
        full_path = ROOT / script_path
        if not full_path.exists():
            self.log(f"SKIP: {script_path} (not found)")
            return False
        self.log(f"RUN: {script_path}")
        try:
            result = subprocess.run([sys.executable, str(full_path)], 
                                  cwd=str(ROOT), 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=300)
            if result.returncode == 0:
                self.log(f"OK: {script_path}")
                if result.stdout:
                    self.log(f"  stdout: {result.stdout.strip()[:200]}")
                return True
            else:
                self.log(f"ERR: {script_path} (code {result.returncode})")
                if result.stderr:
                    self.log(f"  stderr: {result.stderr.strip()[:200]}")
                return False
        except Exception as e:
            self.log(f"EXC: {script_path} - {e}")
            return False
    
    def run_phase(self, phase_id):
        for phase in self.config['phases']:
            if phase['id'] == phase_id:
                self.log(f"=== FASE {phase['id']}: {phase['name']} ===")
                for script in phase['scripts']:
                    self.run_script(script)
                self.log(f"=== FIN FASE {phase['id']} ===\n")
                return
        self.log(f"Phase {phase_id} not found")
    
    def run_all(self):
        self.log("=== ISO TRACKER MASTER ORCHESTRATOR - FASE 5 ===")
        self.log(f"Modo: {self.config['execution']['mode']}")
        self.log("NOTA: Ejecución manual - NO corriendo 24/7\n")
        for phase in self.config['phases']:
            self.log(f"=== FASE {phase['id']}: {phase['name']} ===")
            for script in phase['scripts']:
                self.run_script(script)
            self.log(f"=== FIN FASE {phase['id']} ===\n")
        self.log("=== ORCHESTRATOR COMPLETED ===")
    
    def status(self):
        self.log("=== ESTADO DEL SISTEMA ===")
        for phase in self.config['phases']:
            status_icon = "✓" if phase['status'] == 'completed' else "○"
            self.log(f"{status_icon} Fase {phase['id']}: {phase['name']} - {phase['status']}")
        self.log("")

if __name__ == '__main__':
    orch = ISOOrchestrator()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'all':
            orch.run_all()
        elif cmd.startswith('fase'):
            try:
                pid = int(cmd.replace('fase', ''))
                orch.run_phase(pid)
            except:
                orch.status()
        elif cmd == 'status':
            orch.status()
        else:
            orch.status()
    else:
        orch.status()
        print("\nUso:")
        print("  python scripts/orchestrator/master_orchestrator.py status")
        print("  python scripts/orchestrator/master_orchestrator.py fase3")
        print("  python scripts/orchestrator/master_orchestrator.py all")
"""
AUTORES:
Este sistema ha sido desarrollado siguiendo las fases definidas:
Fase 0-5 completadas
"""
