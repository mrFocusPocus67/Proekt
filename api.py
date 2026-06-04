from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional

app = FastAPI(title="Config Validator API", description="API для проверки конфигураций")

class ConfigRequest(BaseModel):
    content: str
    filename: str

class Rule(BaseModel):
    name: str
    pattern: str
    message: str
    severity: str
    enabled: bool

@app.get("/")
def root():
    return {
        "service": "Config Validator API",
        "version": "1.0",
        "endpoints": ["/validate", "/stats", "/history", "/rules", "/docs"]
    }

@app.post("/validate")
def validate(config: ConfigRequest):
    temp_file = Path("temp_config.yaml")
    temp_file.write_text(config.content)
    
    result = subprocess.run(
        ['python', '.github/scripts/check-config.py'],
        capture_output=True,
        text=True
    )
    
    temp_file.unlink()
    
    return {
        "filename": config.filename,
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "output": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
    }

@app.get("/stats")
def get_stats():
    if not Path("scans.db").exists():
        return {"error": "Нет данных. Запустите хотя бы одну проверку."}
    
    conn = sqlite3.connect('scans.db')
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) FROM scans')
    total_scans = cur.fetchone()[0]
    
    cur.execute('SELECT SUM(total_errors) FROM scans')
    total_errors = cur.fetchone()[0] or 0
    
    cur.execute('SELECT SUM(total_warnings) FROM scans')
    total_warnings = cur.fetchone()[0] or 0
    
    cur.execute('SELECT AVG(total_errors) FROM scans')
    avg_errors = cur.fetchone()[0] or 0
    
    cur.execute('''
        SELECT rule_name, COUNT(*) FROM scan_results 
        WHERE severity = 'error' 
        GROUP BY rule_name 
        ORDER BY COUNT(*) DESC 
        LIMIT 5
    ''')
    top_rules = cur.fetchall()
    
    conn.close()
    
    return {
        "total_scans": total_scans,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "avg_errors_per_scan": round(avg_errors, 2),
        "top_errors": [{"rule": r[0], "count": r[1]} for r in top_rules]
    }

@app.get("/history")
def get_history(limit: int = 10):
    if not Path("scans.db").exists():
        return {"error": "Нет данных"}
    
    conn = sqlite3.connect('scans.db')
    cur = conn.cursor()
    cur.execute('SELECT id, scan_date, total_errors, total_warnings, passed FROM scans ORDER BY id DESC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()
    
    return [{"id": r[0], "date": r[1], "errors": r[2], "warnings": r[3], "passed": r[4]} for r in rows]

@app.get("/rules")
def get_rules():
    with open('rules.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@app.post("/rules")
def add_rule(rule: Rule):
    with open('rules.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['rules'].append(rule.dict())
    
    with open('rules.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return {"message": "Правило добавлено", "rule": rule.dict()}

@app.delete("/rules/{rule_name}")
def delete_rule(rule_name: str):
    with open('rules.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data['rules'])
    data['rules'] = [r for r in data['rules'] if r['name'] != rule_name]
    
    if len(data['rules']) == original_count:
        raise HTTPException(status_code=404, detail=f"Правило '{rule_name}' не найдено")
    
    with open('rules.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return {"message": f"Правило '{rule_name}' удалено"}
