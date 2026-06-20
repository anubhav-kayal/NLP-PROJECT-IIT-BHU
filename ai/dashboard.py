import os
import json
import time
import threading
import tempfile
from pathlib import Path
from typing import Optional
from io import BytesIO

from pii_mask import PIIMask
from file_redactor import FileRedactor
from transcript_processor import TranscriptProcessor
from pdf_exporter import PDFExporter
from whitelist import Whitelist
from audit_log import AuditLog

try:
    from flask import (
        Flask, request, jsonify, render_template_string,
        send_file, send_from_directory
    )
except ImportError:
    Flask = None

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard_data")
os.makedirs(DASHBOARD_DIR, exist_ok=True)


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Privacy Voice Assistant - Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f1a; color: #e0e0e0; min-height: 100vh; }
.header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 1.2em 2em; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #2a2a4a; }
.header h1 { font-size: 1.3em; color: #fff; }
.header .subtitle { color: #8888aa; font-size: 0.85em; margin-top: 0.2em; }
.nav { display: flex; gap: 0.5em; flex-wrap: wrap; }
.nav a { color: #8888aa; text-decoration: none; padding: 0.5em 1em; border-radius: 6px; font-size: 0.9em; transition: all 0.2s; }
.nav a:hover, .nav a.active { background: #2a2a4a; color: #fff; }
.container { max-width: 1200px; margin: 0 auto; padding: 2em; }
.section { display: none; }
.section.active { display: block; }
.card { background: #1a1a2e; border-radius: 10px; padding: 1.5em; margin-bottom: 1.5em; border: 1px solid #2a2a4a; }
.card h2 { font-size: 1.1em; color: #fff; margin-bottom: 1em; }
.card h3 { font-size: 0.95em; color: #aaaacc; margin-bottom: 0.8em; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1em; margin-bottom: 1.5em; }
.stat-card { background: #22223a; border-radius: 8px; padding: 1.2em; text-align: center; border: 1px solid #2a2a4a; }
.stat-value { font-size: 2em; font-weight: bold; color: #4fc3f7; }
.stat-label { color: #8888aa; font-size: 0.85em; margin-top: 0.3em; }
.stat-card.warn .stat-value { color: #ffb74d; }
.stat-card.danger .stat-value { color: #e57373; }
.stat-card.success .stat-value { color: #81c784; }
table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
th, td { padding: 0.6em 0.8em; text-align: left; border-bottom: 1px solid #2a2a4a; }
th { color: #8888aa; font-weight: 600; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.05em; }
td { color: #ccccee; }
tr:hover td { background: #22223a; }
.badge { display: inline-block; padding: 0.15em 0.5em; border-radius: 10px; font-size: 0.8em; font-weight: 500; }
.badge-danger { background: #4a1a1a; color: #e57373; }
.badge-warn { background: #4a3a1a; color: #ffb74d; }
.badge-ok { background: #1a3a1a; color: #81c784; }
.form-group { margin-bottom: 1em; }
.form-group label { display: block; color: #aaaacc; font-size: 0.9em; margin-bottom: 0.4em; }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 0.7em; background: #22223a; border: 1px solid #2a2a4a; border-radius: 6px; color: #e0e0e0; font-size: 0.95em; }
.form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline: none; border-color: #4fc3f7; }
.btn { display: inline-block; padding: 0.6em 1.2em; border-radius: 6px; border: none; cursor: pointer; font-size: 0.9em; font-weight: 500; transition: all 0.2s; }
.btn-primary { background: #4fc3f7; color: #0f0f1a; }
.btn-primary:hover { background: #29b6f6; }
.btn-danger { background: #e57373; color: #fff; }
.btn-danger:hover { background: #ef5350; }
.btn-outline { background: transparent; border: 1px solid #2a2a4a; color: #8888aa; }
.btn-outline:hover { background: #2a2a4a; color: #fff; }
.flex { display: flex; gap: 1em; align-items: center; }
.flex-wrap { flex-wrap: wrap; }
.mt-1 { margin-top: 1em; }
.mb-1 { margin-bottom: 1em; }
.text-center { text-align: center; }
input[type="range"] { width: 100%; accent-color: #4fc3f7; }
.toggle { position: relative; display: inline-block; width: 44px; height: 24px; }
.toggle input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; inset: 0; background: #2a2a4a; border-radius: 24px; transition: 0.3s; }
.slider:before { content: ""; position: absolute; height: 18px; width: 18px; left: 3px; bottom: 3px; background: #fff; border-radius: 50%; transition: 0.3s; }
.toggle input:checked + .slider { background: #4fc3f7; }
.toggle input:checked + .slider:before { transform: translateX(20px); }
.file-drop { border: 2px dashed #2a2a4a; border-radius: 10px; padding: 3em; text-align: center; cursor: pointer; transition: all 0.2s; }
.file-drop:hover { border-color: #4fc3f7; background: #22223a; }
.file-drop.dragover { border-color: #4fc3f7; background: #1a2a3a; }
.spinner { display: inline-block; width: 20px; height: 20px; border: 2px solid #2a2a4a; border-top-color: #4fc3f7; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
#toast { position: fixed; bottom: 2em; right: 2em; padding: 1em 1.5em; border-radius: 8px; color: #fff; font-size: 0.9em; display: none; z-index: 1000; animation: slideIn 0.3s ease; }
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.empty-state { text-align: center; padding: 3em; color: #666688; }
.empty-state .icon { font-size: 3em; margin-bottom: 0.5em; }
.pii-count { font-size: 0.85em; color: #8888aa; }
pre { background: #22223a; padding: 1em; border-radius: 6px; overflow-x: auto; font-size: 0.85em; color: #ccccee; }
</style>
</head>
<body>
<div class="header">
<div><h1>Privacy Voice Assistant</h1><div class="subtitle">IIT BHU NLP Project - Redaction Dashboard</div></div>
<div class="nav">
<a href="#" class="active" data-section="overview">Overview</a>
<a href="#" data-section="redact">Redact File</a>
<a href="#" data-section="transcript">Transcript</a>
<a href="#" data-section="history">History</a>
<a href="#" data-section="whitelist">Whitelist</a>
<a href="#" data-section="settings">Settings</a>
</div>
</div>
<div class="container">

<div id="section-overview" class="section active">
<div class="stats-grid" id="stats-grid">
<div class="stat-card"><div class="stat-value" id="stat-total">-</div><div class="stat-label">Total Sessions</div></div>
<div class="stat-card warn"><div class="stat-value" id="stat-pii">-</div><div class="stat-label">PII Events</div></div>
<div class="stat-card success"><div class="stat-value" id="stat-whitelist">-</div><div class="stat-label">Whitelist Terms</div></div>
<div class="stat-card danger"><div class="stat-value" id="stat-pii-types">-</div><div class="stat-label">PII Categories</div></div>
</div>
<div class="card"><h2>Recent Redaction Events</h2><div id="recent-events"><div class="empty-state"><div class="icon">🛡️</div><p>No events recorded yet. Redact a file or run the assistant to see events.</p></div></div></div>
<div class="card"><h2>PII Category Distribution</h2><div id="pii-chart"><div class="empty-state"><p>No data yet.</p></div></div></div>
</div>

<div id="section-redact" class="section">
<div class="card">
<h2>Redact Audio File</h2>
<p style="color:#8888aa; margin-bottom:1em;">Upload a WAV or MP3 file to redact PII from the audio and generate a redacted transcript.</p>
<div class="file-drop" id="file-drop" onclick="document.getElementById('file-input').click()">
<div style="font-size:2em; margin-bottom:0.5em;">📁</div>
<div style="color:#8888aa;">Drop audio file here or click to browse</div>
<div style="color:#666688; font-size:0.85em; margin-top:0.3em;">Supports WAV, MP3, M4A, OGG, FLAC</div>
</div>
<input type="file" id="file-input" accept=".wav,.mp3,.m4a,.ogg,.flac" style="display:none">
<div class="flex flex-wrap mt-1">
<div class="form-group" style="flex:1;">
<label>Context Mode</label>
<select id="redact-context-mode">
<option value="all">All PII</option>
<option value="personal">Personal Disclosure Only</option>
<option value="public">Public Reference Only</option>
</select>
</div>
<div class="form-group" style="flex:1;">
<label>Export Format</label>
<select id="redact-export-format">
<option value="all">All (WAV + JSON + TXT + PDF)</option>
<option value="txt">Text Only</option>
<option value="json">JSON Report Only</option>
</select>
</div>
</div>
<button class="btn btn-primary mt-1" id="redact-btn" onclick="redactFile()">Redact File</button>
<div id="redact-result" class="mt-1" style="display:none;"></div>
</div>
</div>

<div id="section-transcript" class="section">
<div class="card">
<h2>Redact Transcript</h2>
<p style="color:#8888aa; margin-bottom:1em;">Paste transcript text or upload a VTT/TXT transcript file to redact PII.</p>
<div class="form-group">
<label>Transcript Text</label>
<textarea id="transcript-text" rows="8" placeholder="Paste transcript text here..."></textarea>
</div>
<div class="flex flex-wrap" style="gap:1em;">
<div class="form-group" style="flex:1;">
<label>Or Upload File</label>
<input type="file" id="transcript-file" accept=".vtt,.txt">
</div>
<div class="form-group" style="flex:1;">
<label>Context Mode</label>
<select id="transcript-context-mode">
<option value="all">All PII</option>
<option value="personal">Personal Disclosure Only</option>
<option value="public">Public Reference Only</option>
</select>
</div>
</div>
<button class="btn btn-primary" onclick="redactTranscript()">Redact Transcript</button>
<div id="transcript-result" class="mt-1" style="display:none;"></div>
</div>
</div>

<div id="section-history" class="section">
<div class="card">
<h2>Session History</h2>
<div id="history-list"><div class="empty-state"><div class="icon">📋</div><p>No history yet.</p></div></div>
</div>
</div>

<div id="section-whitelist" class="section">
<div class="card">
<h2>Whitelist Management</h2>
<p style="color:#8888aa; margin-bottom:1em;">Terms in the whitelist will not be redacted. Useful for names you want to keep.</p>
<div class="flex" style="gap:0.5em;">
<input type="text" id="whitelist-input" placeholder="Enter a term to whitelist..." style="flex:1; padding:0.7em; background:#22223a; border:1px solid #2a2a4a; border-radius:6px; color:#e0e0e0;">
<button class="btn btn-primary" onclick="addWhitelist()">Add</button>
</div>
<div id="whitelist-list" class="mt-1"></div>
</div>
</div>

<div id="section-settings" class="section">
<div class="card">
<h2>PII Category Toggles</h2>
<p style="color:#8888aa; margin-bottom:1em;">Enable or disable specific PII detection categories.</p>
<div id="pii-toggles"></div>
</div>
<div class="card">
<h2>Sensitivity</h2>
<div class="form-group">
<label>Confidence Threshold: <span id="sensitivity-value">0.75</span></label>
<input type="range" id="sensitivity-slider" min="0.5" max="1.0" step="0.05" value="0.75" oninput="updateSensitivity(this.value)">
</div>
</div>
<div class="card">
<h2>System Status</h2>
<pre id="system-status">Loading...</pre>
</div>
</div>

</div>
<div id="toast"></div>
<script>
const BASE = '';

function showToast(msg, type='success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.display = 'block';
    t.style.background = type === 'error' ? '#e57373' : '#4fc3f7';
    t.style.color = type === 'error' ? '#fff' : '#0f0f1a';
    setTimeout(() => t.style.display = 'none', 3000);
}

document.querySelectorAll('.nav a').forEach(a => {
    a.addEventListener('click', e => {
        e.preventDefault();
        document.querySelectorAll('.nav a').forEach(x => x.classList.remove('active'));
        a.classList.add('active');
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.getElementById('section-' + a.dataset.section).classList.add('active');
    });
});

const dropZone = document.getElementById('file-drop');
const fileInput = document.getElementById('file-input');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); if(e.dataTransfer.files.length) fileInput.files = e.dataTransfer.files; });

async function redactFile() {
    const file = fileInput.files[0];
    if (!file) { showToast('Please select a file', 'error'); return; }
    const btn = document.getElementById('redact-btn');
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Processing...';
    const resultDiv = document.getElementById('redact-result');
    resultDiv.style.display = 'none';

    const formData = new FormData();
    formData.append('file', file);
    formData.append('context_mode', document.getElementById('redact-context-mode').value);
    formData.append('export_format', document.getElementById('redact-export-format').value);

    try {
        const res = await fetch('/api/redact', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.error) { showToast(data.error, 'error'); resultDiv.innerHTML = '<pre class="error">' + data.error + '</pre>'; resultDiv.style.display = 'block'; return; }
        showToast('File redacted successfully!');
        let html = '<h3>Redaction Result</h3>';
        html += '<table><tr><th>Metric</th><th>Value</th></tr>';
        html += '<tr><td>Duration</td><td>' + (data.duration_seconds || '?') + 's</td></tr>';
        html += '<tr><td>Words</td><td>' + (data.num_words || '?') + '</td></tr>';
        html += '<tr><td>PII Items</td><td>' + (data.pii_count || 0) + '</td></tr>';
        html += '<tr><td>PII Summary</td><td>' + (data.pii_summary || 'None') + '</td></tr>';
        html += '</table>';
        html += '<div class="flex mt-1" style="gap:0.5em; flex-wrap:wrap;">';
        if (data.downloads) {
            for (const [label, url] of Object.entries(data.downloads)) {
                html += '<a href="' + url + '" class="btn btn-outline" download>Download ' + label + '</a>';
            }
        }
        html += '</div>';
        html += '<div class="mt-1"><h3>Original</h3><pre>' + escapeHtml(data.original_text || '') + '</pre></div>';
        html += '<div class="mt-1"><h3>Redacted</h3><pre>' + escapeHtml(data.redacted_text || '') + '</pre></div>';
        resultDiv.innerHTML = html;
        resultDiv.style.display = 'block';
        loadOverview();
    } catch(e) {
        showToast('Error: ' + e.message, 'error');
    }
    btn.disabled = false; btn.textContent = 'Redact File';
}

async function redactTranscript() {
    const text = document.getElementById('transcript-text').value;
    const file = document.getElementById('transcript-file').files[0];
    const mode = document.getElementById('transcript-context-mode').value;
    const resultDiv = document.getElementById('transcript-result');
    resultDiv.style.display = 'none';

    let body;
    if (file) {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('context_mode', mode);
        body = fd;
    } else if (text.trim()) {
        body = new URLSearchParams({ text, context_mode: mode });
    } else {
        showToast('Enter text or upload a file', 'error'); return;
    }

    try {
        const url = file ? '/api/redact-transcript-file' : '/api/redact-transcript';
        const headers = file ? {} : { 'Content-Type': 'application/x-www-form-urlencoded' };
        const res = await fetch(url, { method: 'POST', body, headers });
        const data = await res.json();
        if (data.error) { showToast(data.error, 'error'); resultDiv.innerHTML = '<pre class="error">' + data.error + '</pre>'; resultDiv.style.display = 'block'; return; }
        showToast('Transcript redacted!');
        let html = '<h3>Result</h3>';
        html += '<p>PII Items: ' + (data.pii_count || 0) + ' | Segments: ' + (data.num_segments || 0) + '</p>';
        html += '<div class="mt-1"><h3>Redacted Text</h3><pre>' + escapeHtml(data.redacted_text || '') + '</pre></div>';
        if (data.downloads) {
            html += '<div class="flex mt-1" style="gap:0.5em; flex-wrap:wrap;">';
            for (const [label, url] of Object.entries(data.downloads)) {
                html += '<a href="' + url + '" class="btn btn-outline" download>Download ' + label + '</a>';
            }
            html += '</div>';
        }
        resultDiv.innerHTML = html;
        resultDiv.style.display = 'block';
        loadOverview();
    } catch(e) {
        showToast('Error: ' + e.message, 'error');
    }
}

async function addWhitelist() {
    const input = document.getElementById('whitelist-input');
    const term = input.value.trim();
    if (!term) return;
    try {
        const res = await fetch('/api/whitelist/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ term }) });
        const data = await res.json();
        if (data.ok) { showToast('Added "' + term + '" to whitelist'); input.value = ''; loadWhitelist(); loadOverview(); }
        else showToast(data.error || 'Failed', 'error');
    } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

async function removeWhitelist(term) {
    try {
        const res = await fetch('/api/whitelist/remove', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ term }) });
        const data = await res.json();
        if (data.ok) { showToast('Removed "' + term + '"'); loadWhitelist(); loadOverview(); }
        else showToast(data.error || 'Failed', 'error');
    } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

async function togglePiiCategory(cat) {
    try {
        const res = await fetch('/api/settings/pii-toggle', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: cat }) });
        const data = await res.json();
        if (data.ok) showToast('Updated');
    } catch(e) {}
}

function updateSensitivity(val) {
    document.getElementById('sensitivity-value').textContent = val;
    fetch('/api/settings/sensitivity', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ threshold: parseFloat(val) }) });
}

function escapeHtml(str) { const d = document.createElement('div'); d.textContent = str; return d.innerHTML; }

async function loadOverview() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stat-total').textContent = data.total_sessions || 0;
        document.getElementById('stat-pii').textContent = data.total_pii_events || 0;
        document.getElementById('stat-whitelist').textContent = data.whitelist_count || 0;
        document.getElementById('stat-pii-types').textContent = data.pii_category_count || 0;

        const eventsDiv = document.getElementById('recent-events');
        if (data.recent_events && data.recent_events.length) {
            let html = '<table><tr><th>Time</th><th>PII Types</th><th>Original</th><th>Redacted</th></tr>';
            data.recent_events.forEach(e => {
                const types = (e.pii_detected || []).map(p => '<span class="badge badge-danger">' + p.label + '</span>').join(' ');
                html += '<tr><td>' + (e.timestamp || '') + '</td><td>' + types + '</td><td>' + escapeHtml((e.original_text || '').slice(0,60)) + '</td><td>' + escapeHtml((e.redacted_text || '').slice(0,60)) + '</td></tr>';
            });
            html += '</table>';
            eventsDiv.innerHTML = html;
        }

        const chartDiv = document.getElementById('pii-chart');
        if (data.pii_distribution && Object.keys(data.pii_distribution).length) {
            let html = '<table><tr><th>Category</th><th>Count</th></tr>';
            for (const [cat, count] of Object.entries(data.pii_distribution)) {
                html += '<tr><td>' + cat + '</td><td>' + count + '</td></tr>';
            }
            html += '</table>';
            chartDiv.innerHTML = html;
        }
    } catch(e) {}
}

async function loadWhitelist() {
    try {
        const res = await fetch('/api/whitelist');
        const data = await res.json();
        const div = document.getElementById('whitelist-list');
        if (data.entries && data.entries.length) {
            let html = '<table><tr><th>Term</th><th></th></tr>';
            data.entries.forEach(t => {
                html += '<tr><td>' + escapeHtml(t) + '</td><td><button class="btn btn-danger" style="padding:0.3em 0.6em;font-size:0.8em;" onclick="removeWhitelist(\'' + t.replace(/'/g, "\\'") + '\')">Remove</button></td></tr>';
            });
            html += '</table>';
            div.innerHTML = html;
        } else {
            div.innerHTML = '<div class="empty-state"><p>No whitelisted terms.</p></div>';
        }
    } catch(e) {}
}

async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        const div = document.getElementById('history-list');
        if (data.events && data.events.length) {
            let html = '<table><tr><th>Time</th><th>PII Types</th><th>Speaker</th><th>Original</th><th>Redacted</th></tr>';
            data.events.forEach(e => {
                const types = (e.pii_detected || []).map(p => '<span class="badge badge-danger">' + p.label + '</span>').join(' ');
                html += '<tr><td>' + (e.timestamp || '') + '</td><td>' + types + '</td><td>' + escapeHtml(e.speaker || '') + '</td><td>' + escapeHtml((e.original_text || '').slice(0,60)) + '</td><td>' + escapeHtml((e.redacted_text || '').slice(0,60)) + '</td></tr>';
            });
            html += '</table>';
            div.innerHTML = html;
        } else {
            div.innerHTML = '<div class="empty-state"><div class="icon">📋</div><p>No history yet.</p></div>';
        }
    } catch(e) {}
}

async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        const togglesDiv = document.getElementById('pii-toggles');
        if (data.categories) {
            let html = '';
            for (const [cat, enabled] of Object.entries(data.categories)) {
                html += '<div class="flex" style="justify-content:space-between; padding:0.5em 0; border-bottom:1px solid #2a2a4a;"><span>' + cat + '</span><label class="toggle"><input type="checkbox" ' + (enabled ? 'checked' : '') + ' onchange="togglePiiCategory(\'' + cat + '\')"><span class="slider"></span></label></div>';
            }
            togglesDiv.innerHTML = html;
        }
        document.getElementById('sensitivity-value').textContent = data.sensitivity || '0.75';
        document.getElementById('sensitivity-slider').value = data.sensitivity || '0.75';
        document.getElementById('system-status').textContent = JSON.stringify(data.system, null, 2);
    } catch(e) {}
}

async function loadPiiToggles() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        const togglesDiv = document.getElementById('pii-toggles');
        if (data.categories) {
            let html = '';
            for (const [cat, enabled] of Object.entries(data.categories)) {
                html += '<div class="flex" style="justify-content:space-between; padding:0.5em 0; border-bottom:1px solid #2a2a4a;"><span>' + cat + '</span><label class="toggle"><input type="checkbox" ' + (enabled ? 'checked' : '') + ' onchange="togglePiiCategory(\'' + cat + '\')"><span class="slider"></span></label></div>';
            }
            togglesDiv.innerHTML = html;
        }
    } catch(e) {}
}

document.getElementById('file-input').addEventListener('change', () => {
    const file = document.getElementById('file-input').files[0];
    if (file) document.getElementById('file-drop').innerHTML = '<div style="font-size:1em; color:#4fc3f7;">📄 ' + file.name + ' (' + (file.size/1024).toFixed(1) + ' KB)</div>';
});

loadOverview();
loadWhitelist();
loadHistory();
loadSettings();
setInterval(loadOverview, 5000);
</script>
</body>
</html>"""


class DashboardServer:
    def __init__(self, host="127.0.0.1", port=5000, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.pii = PIIMask()
        self.file_redactor = FileRedactor()
        self.transcript_processor = TranscriptProcessor()
        self.pdf_exporter = PDFExporter()
        self.whitelist = Whitelist()
        self.audit = AuditLog(enabled=True)
        self.pii_toggles = {cat: True for cat in self.pii.RULE_PRIORITY}
        self.sensitivity = self.pii.CONFIDENCE_THRESHOLD
        self.app = None
        self.server_thread = None

    def _build_app(self):
        app = Flask(__name__)
        pii = self.pii
        file_redactor = self.file_redactor
        transcript_processor = self.transcript_processor
        pdf_exporter = self.pdf_exporter
        whitelist_obj = self.whitelist
        audit = self.audit
        pii_toggles = self.pii_toggles
        sensitivity_ref = self  # to access self.sensitivity

        @app.route("/")
        def index():
            return render_template_string(INDEX_HTML)

        @app.route("/api/stats")
        def stats():
            events = []
            try:
                events = AuditLog.view()
            except Exception:
                pass

            pii_distribution = {}
            total_pii = 0
            for e in events:
                for p in e.get("pii_detected", []):
                    label = p.get("label", "?")
                    pii_distribution[label] = pii_distribution.get(label, 0) + 1
                    total_pii += 1

            recent = [
                {
                    "timestamp": time.strftime("%H:%M:%S", time.localtime(e.get("timestamp", 0))),
                    "original_text": e.get("original_text", ""),
                    "redacted_text": e.get("redacted_text", ""),
                    "pii_detected": e.get("pii_detected", []),
                    "speaker": e.get("speaker", ""),
                }
                for e in events[-20:]
            ][::-1]

            return jsonify({
                "total_sessions": len(events),
                "total_pii_events": total_pii,
                "whitelist_count": len(whitelist_obj.list()),
                "pii_category_count": len(pii_distribution),
                "pii_distribution": pii_distribution,
                "recent_events": recent,
            })

        @app.route("/api/redact", methods=["POST"])
        def redact_file():
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400
            f = request.files["file"]
            tmp = tempfile.NamedTemporaryFile(suffix=os.path.splitext(f.filename)[1], delete=False)
            f.save(tmp.name)
            context_mode = request.form.get("context_mode", "all")
            export_format = request.form.get("export_format", "all")

            try:
                base = os.path.splitext(os.path.basename(f.filename))[0]
                out_dir = tempfile.mkdtemp()
                out_wav = os.path.join(out_dir, f"{base}_redacted.wav")
                out_json = os.path.join(out_dir, f"{base}_report.json")
                out_txt = os.path.join(out_dir, f"{base}_redacted.txt")

                result = file_redactor.redact_file(tmp.name, out_wav, out_json, out_txt, context_mode)

                os.unlink(tmp.name)

                downloads = {}
                if export_format in ("all", "wav"):
                    downloads["Redacted WAV"] = f"/api/download?path={out_wav}"
                if export_format in ("all", "txt"):
                    downloads["Redacted TXT"] = f"/api/download?path={out_txt}"
                if export_format in ("all", "json"):
                    downloads["Report JSON"] = f"/api/download?path={out_json}"
                if export_format in ("all",):
                    try:
                        pdf_path = os.path.join(out_dir, f"{base}_redacted.pdf")
                        pdf_exporter.export_redacted_report_pdf(result, pdf_path)
                        downloads["Report PDF"] = f"/api/download?path={pdf_path}"
                    except Exception:
                        pass

                result["downloads"] = downloads
                return jsonify(result)
            except Exception as e:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
                return jsonify({"error": str(e)}), 500

        @app.route("/api/redact-transcript", methods=["POST"])
        def redact_transcript():
            text = request.form.get("text", "")
            context_mode = request.form.get("context_mode", "all")
            if not text:
                return jsonify({"error": "No text provided"}), 400

            redacted_text, spans = pii.analyze(text, context_mode=context_mode)
            return jsonify({
                "original_text": text,
                "redacted_text": redacted_text,
                "spans": [{"label": s.label, "text": s.text} for s in spans],
                "pii_count": len(spans),
                "pii_found": len(spans) > 0,
                "num_segments": 1,
            })

        @app.route("/api/redact-transcript-file", methods=["POST"])
        def redact_transcript_file():
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400
            f = request.files["file"]
            tmp = tempfile.NamedTemporaryFile(suffix=os.path.splitext(f.filename)[1], delete=False)
            f.save(tmp.name)
            context_mode = request.form.get("context_mode", "all")

            try:
                result = transcript_processor.process_transcript(tmp.name, context_mode)
                os.unlink(tmp.name)
                downloads = {}
                for key, path in [("Redacted TXT", result.get("output_txt")),
                                  ("Redacted VTT", result.get("output_vtt")),
                                  ("Report JSON", result.get("output_json"))]:
                    if path and os.path.exists(path):
                        downloads[key] = f"/api/download?path={path}"
                result["downloads"] = downloads
                return jsonify(result)
            except Exception as e:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
                return jsonify({"error": str(e)}), 500

        @app.route("/api/download")
        def download():
            path = request.args.get("path", "")
            if not path or not os.path.exists(path):
                return "File not found", 404
            return send_file(path, as_attachment=True)

        @app.route("/api/whitelist")
        def get_whitelist():
            return jsonify({"entries": whitelist_obj.list()})

        @app.route("/api/whitelist/add", methods=["POST"])
        def add_whitelist():
            data = request.get_json()
            term = data.get("term", "").strip()
            if term:
                whitelist_obj.add(term)
                return jsonify({"ok": True})
            return jsonify({"error": "No term provided"}), 400

        @app.route("/api/whitelist/remove", methods=["POST"])
        def remove_whitelist():
            data = request.get_json()
            term = data.get("term", "").strip()
            if term:
                whitelist_obj.remove(term)
                return jsonify({"ok": True})
            return jsonify({"error": "No term provided"}), 400

        @app.route("/api/history")
        def history():
            events = []
            try:
                events = AuditLog.view()
            except Exception:
                pass
            formatted = [
                {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get("timestamp", 0))),
                    "original_text": e.get("original_text", ""),
                    "redacted_text": e.get("redacted_text", ""),
                    "pii_detected": e.get("pii_detected", []),
                    "speaker": e.get("speaker", ""),
                }
                for e in events
            ][::-1]
            return jsonify({"events": formatted})

        @app.route("/api/settings")
        def get_settings():
            return jsonify({
                "categories": dict(pii_toggles),
                "sensitivity": sensitivity_ref.sensitivity,
                "system": {
                    "version": "1.0.0",
                    "project": "Privacy-Preserving Voice Assistant",
                    "institution": "IIT BHU",
                    "pii_categories": list(pii_toggles.keys()),
                    "whitelist_terms": len(whitelist_obj.list()),
                    "audit_log_entries": len(AuditLog.view()),
                }
            })

        @app.route("/api/settings/pii-toggle", methods=["POST"])
        def toggle_pii():
            data = request.get_json()
            cat = data.get("category", "")
            if cat in pii_toggles:
                pii_toggles[cat] = not pii_toggles[cat]
                return jsonify({"ok": True, "enabled": pii_toggles[cat]})
            return jsonify({"error": "Category not found"}), 400

        @app.route("/api/settings/sensitivity", methods=["POST"])
        def set_sensitivity():
            data = request.get_json()
            val = float(data.get("threshold", 0.75))
            sensitivity_ref.sensitivity = max(0.5, min(1.0, val))
            pii.CONFIDENCE_THRESHOLD = sensitivity_ref.sensitivity
            return jsonify({"ok": True, "threshold": sensitivity_ref.sensitivity})

        return app

    def start(self, open_browser=True):
        if Flask is None:
            print("  Flask not installed. Install with: pip install flask")
            return

        self.app = self._build_app()
        url = f"http://{self.host}:{self.port}"

        print(f"\n  {'='*60}")
        print(f"  DASHBOARD STARTING")
        print(f"  {'='*60}")
        print(f"  URL: {url}")
        print(f"  {'='*60}\n")

        if open_browser:
            try:
                import webbrowser
                threading.Timer(0.5, lambda: webbrowser.open(url)).start()
            except Exception:
                pass

        self.app.run(host=self.host, port=self.port, debug=self.debug)

    def start_in_thread(self, open_browser=True):
        if Flask is None:
            print("  Flask not installed. Install with: pip install flask")
            return
        self.app = self._build_app()
        self.server_thread = threading.Thread(
            target=self.app.run,
            kwargs={"host": self.host, "port": self.port, "debug": self.debug, "use_reloader": False},
            daemon=True,
        )
        self.server_thread.start()
        url = f"http://{self.host}:{self.port}"
        print(f"  Dashboard: {url}")
        if open_browser:
            try:
                import webbrowser
                threading.Timer(0.5, lambda: webbrowser.open(url)).start()
            except Exception:
                pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Privacy Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    server = DashboardServer(host=args.host, port=args.port)
    server.start(open_browser=not args.no_browser)
