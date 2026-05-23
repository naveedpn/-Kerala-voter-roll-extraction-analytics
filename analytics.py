"""
analytics.py
------------
Generates a highly-premium, interactive HTML dashboard from processed voter roll CSV files.
Uses standard high-contrast Vanilla CSS styling for offline-resilience and layouts, with Chart.js for visualization.
Supports dynamic multi-dataset selection for switching between batch-processed voter rolls.
"""

import os
import csv
import re
import json

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voter Roll Analytics Dashboard</title>
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #090d16;
            --card-bg: rgba(17, 24, 39, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-pink: #fb7185;
            --accent-green: #34d399;
            --accent-amber: #fbbf24;
            --accent-indigo: #6366f1;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }

        /* Ambient glowing backdrop decoration */
        .glowing-bg {
            position: absolute;
            top: 0;
            right: 0;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, rgba(0, 0, 0, 0) 70%);
            pointer-events: none;
            z-index: 1;
        }

        /* Top Header Area */
        .header-container {
            background-color: #020617;
            border-bottom: 1px solid var(--border-color);
            padding: 28px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            position: relative;
            z-index: 10;
        }

        .header-title-section {
            z-index: 10;
        }

        .report-badge {
            display: inline-block;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: var(--accent-green);
            background-color: rgba(52, 211, 153, 0.1);
            padding: 5px 14px;
            border-radius: 12px;
            border: 1px solid rgba(52, 211, 153, 0.2);
        }

        .header-title {
            font-size: 28px;
            font-weight: 800;
            color: #ffffff;
            margin: 10px 0 0 0;
            letter-spacing: -0.5px;
        }

        .header-subtitle {
            font-size: 13px;
            color: var(--text-secondary);
            margin: 6px 0 0 0;
        }

        .header-actions {
            display: flex;
            gap: 12px;
            z-index: 10;
        }

        /* Premium Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 700;
            padding: 10px 20px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.15s ease;
            text-decoration: none;
            box-sizing: border-box;
        }

        .btn-secondary {
            background-color: #1e293b;
            color: var(--text-primary);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .btn-secondary:hover {
            background-color: #334155;
            border-color: rgba(255, 255, 255, 0.2);
        }

        .btn-primary {
            background-color: var(--accent-indigo);
            color: #ffffff;
            border: none;
            box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.35);
        }

        .btn-primary:hover {
            background-color: #4f46e5;
            box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.5);
            transform: translateY(-1px);
        }

        /* Dashboard content layout */
        .dashboard-content {
            max-width: 1280px;
            margin: 40px auto;
            padding: 0 24px;
            display: flex;
            flex-direction: column;
            gap: 32px;
            position: relative;
            z-index: 10;
        }

        /* Metric cards grid */
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 24px;
        }

        /* Standalone Modern Glassmorphism Cards */
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-sizing: border-box;
        }

        .card-glowing-glow {
            position: absolute;
            right: -16px;
            bottom: -16px;
            width: 96px;
            height: 96px;
            border-radius: 50%;
            filter: blur(24px);
            pointer-events: none;
        }

        .card-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
        }

        .card-value {
            font-size: 38px;
            font-weight: 800;
            margin: 10px 0 0 0;
            color: #ffffff;
            letter-spacing: -1px;
        }

        .card-subtext {
            font-size: 12px;
            font-weight: 600;
            margin-top: 12px;
            display: inline-flex;
            align-items: center;
        }

        .badge-green {
            background-color: rgba(52, 211, 153, 0.1);
            color: var(--accent-green);
            padding: 2px 8px;
            border-radius: 8px;
            font-weight: 700;
        }

        /* 2x2 charts grid */
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 32px;
        }

        @media (max-width: 1024px) {
            .chart-grid {
                grid-template-columns: 1fr;
            }
        }

        .chart-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
        }

        .chart-card-header {
            margin-bottom: 20px;
        }

        .chart-title {
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
            margin: 0;
            letter-spacing: -0.2px;
        }

        .chart-subtitle {
            font-size: 12px;
            color: var(--text-secondary);
            margin: 4px 0 0 0;
        }

        .chart-wrapper {
            position: relative;
            flex-grow: 1;
            min-height: 280px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Voter Explorer section */
        .explorer-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
            overflow: hidden;
            box-sizing: border-box;
        }

        .explorer-header {
            padding: 28px;
            border-bottom: 1px solid var(--border-color);
            background-color: rgba(15, 23, 42, 0.4);
        }

        .explorer-header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        .explorer-title-area h3 {
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
            margin: 0;
        }

        .explorer-title-area p {
            font-size: 12px;
            color: var(--text-secondary);
            margin: 4px 0 0 0;
        }

        .search-container {
            position: relative;
            width: 320px;
        }

        @media (max-width: 640px) {
            .search-container {
                width: 100%;
            }
        }

        .search-input {
            width: 100%;
            box-sizing: border-box;
            background-color: #020617;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 14px;
            padding: 12px 16px 12px 42px;
            font-size: 13px;
            color: #ffffff;
            transition: all 0.15s ease;
        }

        .search-input:focus {
            outline: none;
            border-color: var(--accent-indigo);
            box-shadow: 0 0 0 1px var(--accent-indigo);
        }

        .search-icon {
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
            pointer-events: none;
        }

        /* Filter Controls */
        .filters-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-top: 24px;
            align-items: end;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .filter-label {
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-secondary);
        }

        .filter-select {
            background-color: #020617;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 10px 14px;
            font-size: 12px;
            color: #cbd5e1;
            transition: all 0.15s ease;
            cursor: pointer;
        }

        .filter-select:focus {
            outline: none;
            border-color: var(--accent-indigo);
        }

        .count-badge {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 10px;
            text-align: right;
            font-weight: 500;
        }

        @media (max-width: 768px) {
            .count-badge {
                text-align: left;
                margin-top: 10px;
            }
        }

        /* Table Design */
        .table-container {
            overflow-x: auto;
            width: 100%;
        }

        .voter-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        .voter-table th {
            padding: 16px 24px;
            background-color: rgba(15, 23, 42, 0.25);
            border-bottom: 1px solid var(--border-color);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
        }

        .voter-table td {
            padding: 14px 24px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-size: 13px;
            color: #cbd5e1;
            vertical-align: middle;
        }

        .voter-table tr:hover {
            background-color: rgba(255, 255, 255, 0.02);
        }

        /* Status Pills */
        .gender-pill {
            display: inline-flex;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            padding: 3px 10px;
            border-radius: 9999px;
            border: 1px solid transparent;
        }

        .gender-male {
            background-color: rgba(56, 189, 248, 0.1);
            color: var(--accent-blue);
            border-color: rgba(56, 189, 248, 0.2);
        }

        .gender-female {
            background-color: rgba(251, 113, 133, 0.1);
            color: var(--accent-pink);
            border-color: rgba(251, 113, 133, 0.2);
        }

        .gender-unknown {
            background-color: rgba(148, 163, 184, 0.1);
            color: var(--text-secondary);
            border-color: rgba(148, 163, 184, 0.2);
        }

        /* Footer Pagination */
        .table-footer {
            padding: 20px 28px;
            border-top: 1px solid var(--border-color);
            background-color: rgba(15, 23, 42, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-sizing: border-box;
        }

        .page-text {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #020617;
        }
        ::-webkit-scrollbar-thumb {
            background: #1e293b;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #334155;
        }
    </style>
</head>
<body>

    <div class="glowing-bg"></div>

    <!-- Top Header -->
    <div class="header-container">
        <div class="header-title-section">
            <span class="report-badge">Report Generated Successfully</span>
            <h1 class="header-title">Voter Roll Analytics</h1>
            <p class="header-subtitle">Source File: <span style="font-family: monospace; color: #ffffff;" id="fileNameText">voter_list.csv</span></p>
        </div>

        <!-- Synchronized Multi-Dataset Selector -->
        <div class="filter-group" style="min-width: 340px; z-index: 50; margin: 10px 0;">
            <label class="filter-label" style="color: var(--accent-indigo); font-weight: 800; font-size: 10px;">Select Active Voter Roll Dataset</label>
            <select id="voterRollSelector" onchange="switchVoterRoll(this.value)" class="filter-select" style="background-color: #0b0f19; border-color: var(--accent-indigo); font-weight: 700; color: #ffffff; width: 100%;">
                INJECT_VOTER_ROLL_OPTIONS
            </select>
        </div>
        
        <div class="header-actions">
            <button onclick="window.print()" class="btn btn-secondary">
                <svg class="btn-icon" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display:inline-block; vertical-align:middle; margin-right:4px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
                Print Report
            </button>
            <button onclick="copyTableToClipboard()" class="btn btn-primary">
                <svg class="btn-icon" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display:inline-block; vertical-align:middle; margin-right:4px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
                Copy Database
            </button>
        </div>
    </div>

    <!-- Main Dashboard Container -->
    <div class="dashboard-content">
        
        <!-- 4 Summary Stats Cards -->
        <div class="metric-grid">
            <!-- Total Card -->
            <div class="card">
                <div class="card-glowing-glow" style="background-color: rgba(52, 211, 153, 0.12);"></div>
                <div>
                    <span class="card-label">Total Registered Voters</span>
                    <h2 class="card-value" id="statTotal">0</h2>
                </div>
                <div class="card-subtext">
                    <span class="badge-green">✔ Active</span>
                    <span style="color: var(--text-secondary); margin-left: 8px;">100% Extracted</span>
                </div>
            </div>
            
            <!-- Male Card -->
            <div class="card">
                <div class="card-glowing-glow" style="background-color: rgba(56, 189, 248, 0.12);"></div>
                <div>
                    <span class="card-label">Male Voters</span>
                    <h2 class="card-value" id="statMale" style="color: var(--accent-blue);">0</h2>
                </div>
                <div class="card-subtext" id="pctMale" style="color: var(--accent-blue); font-weight: 700;">
                    0% of total
                </div>
            </div>
            
            <!-- Female Card -->
            <div class="card">
                <div class="card-glowing-glow" style="background-color: rgba(251, 113, 133, 0.12);"></div>
                <div>
                    <span class="card-label">Female Voters</span>
                    <h2 class="card-value" id="statFemale" style="color: var(--accent-pink);">0</h2>
                </div>
                <div class="card-subtext" id="pctFemale" style="color: var(--accent-pink); font-weight: 700;">
                    0% of total
                </div>
            </div>
            
            <!-- Gender Ratio Card -->
            <div class="card">
                <div class="card-glowing-glow" style="background-color: rgba(251, 191, 36, 0.12);"></div>
                <div>
                    <span class="card-label">Gender Balance Ratio</span>
                    <h2 class="card-value" id="statRatio" style="color: var(--accent-amber);">1.0</h2>
                </div>
                <div class="card-subtext" id="statUnknowns" style="color: var(--text-secondary);">
                    0 entries unknown gender
                </div>
            </div>
        </div>

        <!-- 2x2 Grid of Demographic Visualizations -->
        <div class="chart-grid">
            <!-- Gender Ratio Doughnut Chart -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <h3 class="chart-title">Gender Ratios</h3>
                    <p class="chart-subtitle">Distribution of male vs. female voters</p>
                </div>
                <div class="chart-wrapper">
                    <canvas id="chartGender"></canvas>
                </div>
            </div>
            
            <!-- Age Distribution Bar Chart -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <h3 class="chart-title">Age Cohorts</h3>
                    <p class="chart-subtitle">Demographic cohorts representing population distribution</p>
                </div>
                <div class="chart-wrapper">
                    <canvas id="chartAge"></canvas>
                </div>
            </div>
            
            <!-- Voter ID Wave Prefixes -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <h3 class="chart-title">Registration Waves (Voter ID Prefix)</h3>
                    <p class="chart-subtitle">Top Voter ID card serial sets indicating registration generations</p>
                </div>
                <div class="chart-wrapper">
                    <canvas id="chartPrefix"></canvas>
                </div>
            </div>
            
            <!-- Household Densities -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <h3 class="chart-title">Joint Families (Top Households)</h3>
                    <p class="chart-subtitle">Top 10 house numbers ordered by number of registered voters</p>
                </div>
                <div class="chart-wrapper">
                    <canvas id="chartHouse"></canvas>
                </div>
            </div>
        </div>

        <!-- Voter Database Explorer -->
        <div class="explorer-card">
            <!-- Explorer Header with Controls -->
            <div class="explorer-header">
                <div class="explorer-header-top">
                    <div class="explorer-title-area">
                        <h3>Voter Database Explorer</h3>
                        <p>Full searchable structured dataset extracted via OCR</p>
                    </div>
                    
                    <!-- Search Input -->
                    <div class="search-container">
                        <svg class="search-icon" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                        <input type="text" id="searchInput" class="search-input" oninput="handleFilterChange()" placeholder="Search name, voter ID, house...">
                    </div>
                </div>
                
                <!-- Filters Grid -->
                <div class="filters-row">
                    <div class="filter-group">
                        <label class="filter-label">Filter Gender</label>
                        <select id="filterGender" onchange="handleFilterChange()" class="filter-select">
                            <option value="All">All Genders</option>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Unknown">Unknown</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label class="filter-label">Filter Age Group</label>
                        <select id="filterAge" onchange="handleFilterChange()" class="filter-select">
                            <option value="All">All Ages</option>
                            <option value="18-25">18 - 25</option>
                            <option value="26-35">26 - 35</option>
                            <option value="36-50">36 - 50</option>
                            <option value="51-65">51 - 65</option>
                            <option value="66+">66+</option>
                            <option value="Unknown">Unknown/OCR Fail</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label class="filter-label">Entries Per Page</label>
                        <select id="pageSize" onchange="handlePageSizeChange()" class="filter-select">
                            <option value="10">10 entries</option>
                            <option value="25" selected>25 entries</option>
                            <option value="50">50 entries</option>
                            <option value="100">100 entries</option>
                        </select>
                    </div>
                    <div class="filter-group" style="align-items: flex-end;">
                        <span class="count-badge" id="countDisplay">Showing 0 of 0 entries</span>
                    </div>
                </div>
            </div>

            <!-- Table Responsive container -->
            <div class="table-container">
                <table class="voter-table">
                    <thead>
                        <tr>
                            <th style="width: 80px; text-align: center;">S.No</th>
                            <th>Voter ID</th>
                            <th>Voter Name</th>
                            <th>Guardian Info</th>
                            <th style="text-align: center;">House No</th>
                            <th style="text-align: center; width: 80px;">Age</th>
                            <th style="text-align: center; width: 120px;">Gender</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
                        <!-- Filled by JavaScript -->
                    </tbody>
                </table>
            </div>

            <!-- Pagination Footer -->
            <div class="table-footer">
                <button id="prevBtn" onclick="changePage(-1)" class="btn btn-secondary" style="padding: 8px 16px;">
                    Previous
                </button>
                <span class="page-text" id="pageDisplay">Page 1 of 1</span>
                <button id="nextBtn" onclick="changePage(1)" class="btn btn-secondary" style="padding: 8px 16px;">
                    Next
                </button>
            </div>
        </div>
        
    </div>

    <!-- Data Injection Block -->
    <script>
        // Injected data from python generator
        const rawFileName = "INJECT_FILE_NAME";
        const statTotalVal = INJECT_TOTAL_VOTERS;
        const statMaleVal = INJECT_MALE_COUNT;
        const statFemaleVal = INJECT_FEMALE_COUNT;
        const statUnknownVal = INJECT_UNKNOWN_GENDER_COUNT;
        
        const ageCohortData = INJECT_AGE_COHORTS;
        const prefixLabels = INJECT_PREFIX_LABELS;
        const prefixCounts = INJECT_PREFIX_COUNTS;
        const houseLabels = INJECT_HOUSE_LABELS;
        const houseCounts = INJECT_HOUSE_COUNTS;
        
        const voterRecords = INJECT_VOTERS_JSON;
        
        // Render statistics onto cards
        document.getElementById('fileNameText').innerText = rawFileName;
        document.getElementById('statTotal').innerText = statTotalVal.toLocaleString();
        document.getElementById('statMale').innerText = statMaleVal.toLocaleString();
        document.getElementById('statFemale').innerText = statFemaleVal.toLocaleString();
        document.getElementById('statUnknowns').innerText = `${statUnknownVal} entries with unknown gender`;
        
        const malePct = statTotalVal > 0 ? ((statMaleVal / statTotalVal) * 100).toFixed(1) : 0;
        const femalePct = statTotalVal > 0 ? ((statFemaleVal / statTotalVal) * 100).toFixed(1) : 0;
        const ratio = statFemaleVal > 0 ? (statMaleVal / statFemaleVal).toFixed(2) : (statMaleVal > 0 ? "∞" : "0.00");
        
        document.getElementById('pctMale').innerText = `${malePct}% of total voters`;
        document.getElementById('pctFemale').innerText = `${femalePct}% of total voters`;
        document.getElementById('statRatio').innerText = `${ratio} M/F`;

        // Redirect browser to switch datasets
        function switchVoterRoll(selectedFile) {
            if (!selectedFile) return;
            const reportName = selectedFile.replace('.csv', '_report.html');
            window.location.href = reportName;
        }

        // ==========================================
        // 1. CHART.JS CONFIGURATION (OFFLINE RESILIENT)
        // ==========================================
        if (typeof Chart !== 'undefined') {
            // Global styling defaults for dark mode
            Chart.defaults.color = '#94a3b8';
            Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
            
            // A. Gender Doughnut Chart
            new Chart(document.getElementById('chartGender'), {
                type: 'doughnut',
                data: {
                    labels: ['Male', 'Female', 'Unknown'],
                    datasets: [{
                        data: [statMaleVal, statFemaleVal, statUnknownVal],
                        backgroundColor: ['#38bdf8', '#fb7185', '#64748b'],
                        borderColor: '#111827',
                        borderWidth: 3,
                        hoverOffset: 12
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                font: { size: 12, weight: '600' }
                            }
                        }
                    },
                    cutout: '70%'
                }
            });

            // B. Age Distribution Chart
            new Chart(document.getElementById('chartAge'), {
                type: 'bar',
                data: {
                    labels: ['18-25', '26-35', '36-50', '51-65', '66+', 'Unknown'],
                    datasets: [{
                        label: 'Voter Count',
                        data: [
                            ageCohortData['18-25'],
                            ageCohortData['26-35'],
                            ageCohortData['36-50'],
                            ageCohortData['51-65'],
                            ageCohortData['66+'],
                            ageCohortData['Unknown']
                        ],
                        backgroundColor: 'rgba(99, 102, 241, 0.75)',
                        hoverBackgroundColor: 'rgba(99, 102, 241, 1)',
                        borderColor: '#6366f1',
                        borderWidth: 1.5,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { grid: { display: false } },
                        y: { 
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            border: { dash: [4, 4] }
                        }
                    }
                }
            });

            // C. Prefix Registration Waves Chart
            new Chart(document.getElementById('chartPrefix'), {
                type: 'bar',
                data: {
                    labels: prefixLabels,
                    datasets: [{
                        label: 'Voters Registered',
                        data: prefixCounts,
                        backgroundColor: 'rgba(14, 165, 233, 0.75)',
                        hoverBackgroundColor: 'rgba(14, 165, 233, 1)',
                        borderColor: '#0ea5e9',
                        borderWidth: 1.5,
                        borderRadius: 8
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { 
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            border: { dash: [4, 4] }
                        },
                        y: { grid: { display: false } }
                    }
                }
            });

            // D. Household Densities Chart
            new Chart(document.getElementById('chartHouse'), {
                type: 'bar',
                data: {
                    labels: houseLabels,
                    datasets: [{
                        label: 'Members Registered',
                        data: houseCounts,
                        backgroundColor: 'rgba(244, 63, 94, 0.75)',
                        hoverBackgroundColor: 'rgba(244, 63, 94, 1)',
                        borderColor: '#f43f5e',
                        borderWidth: 1.5,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { grid: { display: false } },
                        y: { 
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            border: { dash: [4, 4] }
                        }
                    }
                }
            });
        } else {
            console.warn("Chart.js failed to load. Dashboard is in offline mode.");
            document.querySelectorAll('.chart-wrapper').forEach(wrapper => {
                wrapper.innerHTML = `
                    <div style="
                        color: var(--text-secondary);
                        font-weight: 600;
                        font-size: 12px;
                        text-align: center;
                        padding: 40px 20px;
                        border: 1px dashed rgba(255, 255, 255, 0.08);
                        border-radius: 16px;
                        background: rgba(2, 6, 23, 0.4);
                        max-width: 280px;
                        margin: 0 auto;
                    ">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="margin: 0 auto 12px auto; display: block; color: var(--accent-indigo); opacity: 0.8;">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
                        </svg>
                        Visualizations require internet connection to fetch the Chart.js CDN library. All other database metrics & Explorer tables are fully functional offline!
                    </div>
                `;
            });
        }

        // ==========================================
        // 2. INTERACTIVE DATABASE TABLE LOGIC
        // ==========================================
        let filteredRecords = [...voterRecords];
        let currentPage = 1;
        let pageSize = 25;

        function updateTable() {
            const tableBody = document.getElementById('tableBody');
            tableBody.innerHTML = '';

            const startIndex = (currentPage - 1) * pageSize;
            const endIndex = Math.min(startIndex + pageSize, filteredRecords.length);
            const pageRecords = filteredRecords.slice(startIndex, endIndex);

            if (pageRecords.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7" style="padding: 48px; text-align: center; color: var(--text-secondary); font-weight: 500;">
                            No records found matching your filters.
                        </td>
                    </tr>
                `;
            } else {
                pageRecords.forEach(rec => {
                    let genderTag = '';
                    if (rec.gender === 'Male') {
                        genderTag = `<span class="gender-pill gender-male">MALE</span>`;
                    } else if (rec.gender === 'Female') {
                        genderTag = `<span class="gender-pill gender-female">FEMALE</span>`;
                    } else {
                        genderTag = `<span class="gender-pill gender-unknown">UNKNOWN</span>`;
                    }

                    tableBody.innerHTML += `
                        <tr>
                            <td style="text-align: center; color: var(--text-secondary); font-family: monospace; font-size: 12px; font-weight: 600;">${rec.sn}</td>
                            <td style="font-family: monospace; font-size: 12px; font-weight: 700; color: #818cf8; select-all: all;">${rec.voter_id || 'N/A'}</td>
                            <td style="font-weight: 600; color: #ffffff;">${rec.name}</td>
                            <td style="font-size: 12px; color: var(--text-secondary);">${rec.guardian || '—'}</td>
                            <td style="text-align: center; font-weight: 600; color: var(--accent-green); font-size: 12px;">${rec.house}</td>
                            <td style="text-align: center; font-weight: 700; color: #e2e8f0; font-size: 12px;">${rec.age}</td>
                            <td style="text-align: center;">${genderTag}</td>
                        </tr>
                    `;
                });
            }

            // Update page display
            const totalPages = Math.max(1, Math.ceil(filteredRecords.length / pageSize));
            document.getElementById('pageDisplay').innerText = `Page ${currentPage} of ${totalPages}`;
            document.getElementById('countDisplay').innerText = `Showing ${startIndex + 1}-${endIndex} of ${filteredRecords.length} entries`;

            // Enable/disable navigation buttons
            document.getElementById('prevBtn').disabled = (currentPage === 1);
            document.getElementById('nextBtn').disabled = (currentPage === totalPages);
        }

        function handleFilterChange() {
            const searchInput = document.getElementById('searchInput');
            const searchVal = searchInput.value.trim().toLowerCase();
            const genderFilter = document.getElementById('filterGender').value;
            const ageFilter = document.getElementById('filterAge').value;

            filteredRecords = voterRecords.filter(rec => {
                // Search filter
                const nameMatch = rec.name.toLowerCase().includes(searchVal);
                const idMatch = (rec.voter_id || '').toLowerCase().includes(searchVal);
                const houseMatch = rec.house.toLowerCase().includes(searchVal);
                const guardianMatch = (rec.guardian || '').toLowerCase().includes(searchVal);
                
                const matchesSearch = nameMatch || idMatch || houseMatch || guardianMatch;

                // Gender filter
                let matchesGender = true;
                if (genderFilter !== 'All') {
                    matchesGender = (rec.gender === genderFilter);
                }

                // Age filter
                let matchesAge = true;
                if (ageFilter !== 'All') {
                    const ageNum = parseInt(rec.age);
                    if (isNaN(ageNum)) {
                        matchesAge = (ageFilter === 'Unknown');
                    } else {
                        if (ageFilter === '18-25') matchesAge = (ageNum >= 18 && ageNum <= 25);
                        else if (ageFilter === '26-35') matchesAge = (ageNum >= 26 && ageNum <= 35);
                        else if (ageFilter === '36-50') matchesAge = (ageNum >= 36 && ageNum <= 50);
                        else if (ageFilter === '51-65') matchesAge = (ageNum >= 51 && ageNum <= 65);
                        else if (ageFilter === '66+') matchesAge = (ageNum >= 66);
                    }
                }

                return matchesSearch && matchesGender && matchesAge;
            });

            currentPage = 1;
            updateTable();
        }

        function handlePageSizeChange() {
            pageSize = parseInt(document.getElementById('pageSize').value);
            currentPage = 1;
            updateTable();
        }

        function changePage(direction) {
            const totalPages = Math.ceil(filteredRecords.length / pageSize);
            currentPage += direction;
            if (currentPage < 1) currentPage = 1;
            if (currentPage > totalPages) currentPage = totalPages;
            updateTable();
        }

        // Copy plain text table values to clipboard as tab-separated spreadsheet values
        function copyTableToClipboard() {
            let tsv = 'Serial No\\tVoter ID\\tVoter Name\\tGuardian Info\\tHouse No\\tAge\\tGender\\n';
            voterRecords.forEach(rec => {
                tsv += `${rec.sn}\\t${rec.voter_id}\\t${rec.name}\\t${rec.guardian}\\t${rec.house}\\t${rec.age}\\t${rec.gender}\\n`;
            });
            
            navigator.clipboard.writeText(tsv).then(() => {
                alert('Success! Full database copied to clipboard in Spreadsheet/Tab-separated format.');
            }).catch(err => {
                console.error('Clipboard copy failed: ', err);
            });
        }

        // Initialize Table View on page load
        updateTable();
    </script>

</body>
</html>
"""

def compile_csv_data(csv_path):
    """
    Parses a processed voter roll CSV file and extracts structured statistics,
    cohort breakdowns, household density, and full voter list for client-side API.
    """
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} does not exist.")
        return None
        
    csv_name = os.path.basename(csv_path)
    
    total_voters = 0
    males = 0
    females = 0
    unknown_gender = 0
    
    age_cohorts = {
        "18-25": 0,
        "26-35": 0,
        "36-50": 0,
        "51-65": 0,
        "66+": 0,
        "Unknown": 0
    }
    
    prefixes = {}
    households = {}
    voters_list = []
    
    age_pattern = re.compile(r'\b\d+\b')
    
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_voters += 1
            
            serial = row.get("serial_number", "").strip()
            voter_id = row.get("voter_id", "").strip()
            name = row.get("name", "").strip()
            guardian = row.get("guardian", "").strip()
            house = row.get("house_number", "").strip()
            age_gender_raw = row.get("age_gender", "").strip()
            
            # Determine gender
            gender = "Unknown"
            if "പുരുഷൻ" in age_gender_raw or "Male" in age_gender_raw:
                gender = "Male"
                males += 1
            elif any(f_var in age_gender_raw for f_var in ["സ്ത്രീ", "Female", "സ്കീ", "സ്തീ", "സൂീ", "സ്ലീ"]):
                gender = "Female"
                females += 1
            else:
                unknown_gender += 1
                
            # Determine age
            age_val = None
            age_match = age_pattern.search(age_gender_raw)
            if age_match:
                age_val = int(age_match.group())
                if 18 <= age_val <= 25:
                    age_cohorts["18-25"] += 1
                elif 26 <= age_val <= 35:
                    age_cohorts["26-35"] += 1
                elif 36 <= age_val <= 50:
                    age_cohorts["36-50"] += 1
                elif 51 <= age_val <= 65:
                    age_cohorts["51-65"] += 1
                elif age_val >= 66:
                    age_cohorts["66+"] += 1
                else:
                    age_cohorts["Unknown"] += 1
            else:
                age_cohorts["Unknown"] += 1
                
            # Prefix Wave (first 3 letters of voter_id)
            if len(voter_id) >= 3:
                pref = voter_id[:3].upper()
                if pref.isalpha():
                    prefixes[pref] = prefixes.get(pref, 0) + 1
                    
            # Households (clean house number)
            clean_house = house.replace("വീട്ടു നമ്പർ", "").replace("വിട്ടു നമ്പർ", "").replace("നമ്പർ", "").replace(":", "").strip()
            clean_house = re.sub(r'^[\s/]+', '', clean_house).strip()
            if clean_house:
                households[clean_house] = households.get(clean_house, 0) + 1
                
            voters_list.append({
                "sn": serial,
                "voter_id": voter_id,
                "name": name,
                "guardian": guardian,
                "house": clean_house if clean_house else "—",
                "age": age_val if age_val is not None else "Unknown",
                "gender": gender
            })
            
    # Sort and slice top datasets
    sorted_houses = sorted(households.items(), key=lambda x: x[1], reverse=True)[:10]
    top_houses_labels = [x[0] for x in sorted_houses]
    top_houses_counts = [x[1] for x in sorted_houses]
    
    sorted_prefixes = sorted(prefixes.items(), key=lambda x: x[1], reverse=True)[:10]
    top_pref_labels = [x[0] for x in sorted_prefixes]
    top_pref_counts = [x[1] for x in sorted_prefixes]
    
    return {
        "fileName": csv_name,
        "totalVoters": total_voters,
        "maleCount": males,
        "femaleCount": females,
        "unknownGenderCount": unknown_gender,
        "ageCohorts": age_cohorts,
        "prefixLabels": top_pref_labels,
        "prefixCounts": top_pref_counts,
        "houseLabels": top_houses_labels,
        "houseCounts": top_houses_counts,
        "voters": voters_list
    }


def generate_analytics_report(csv_path, regenerate_all=True):
    """
    Parses a processed voter roll CSV file and outputs a matching, beautiful HTML dashboard report.
    Returns the absolute path of the generated HTML report.
    Also synchronizes dropdown options across all existing sibling reports in the same directory.
    """
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} does not exist.")
        return None
        
    csv_dir = os.path.dirname(csv_path)
    csv_name = os.path.basename(csv_path)
    
    # List all CSVs in directory to populate dropdown selector
    all_csvs = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    all_csvs.sort()
    
    # Build select option tags
    options_html = ""
    for csv_file in all_csvs:
        selected_attr = "selected" if csv_file == csv_name else ""
        options_html += f'<option value="{csv_file}" {selected_attr}>{csv_file}</option>'
        
    data = compile_csv_data(csv_path)
    if not data:
        return None
        
    total_voters = data["totalVoters"]
    males = data["maleCount"]
    females = data["femaleCount"]
    unknown_gender = data["unknownGenderCount"]
    age_cohorts = data["ageCohorts"]
    top_pref_labels = data["prefixLabels"]
    top_pref_counts = data["prefixCounts"]
    top_houses_labels = data["houseLabels"]
    top_houses_counts = data["houseCounts"]
    voters_list = data["voters"]
    
    # Inject data into HTML template
    html_content = HTML_TEMPLATE
    html_content = html_content.replace("INJECT_FILE_NAME", csv_name)
    html_content = html_content.replace("INJECT_VOTER_ROLL_OPTIONS", options_html)
    html_content = html_content.replace("INJECT_TOTAL_VOTERS", str(total_voters))
    html_content = html_content.replace("INJECT_MALE_COUNT", str(males))
    html_content = html_content.replace("INJECT_FEMALE_COUNT", str(females))
    html_content = html_content.replace("INJECT_UNKNOWN_GENDER_COUNT", str(unknown_gender))
    
    html_content = html_content.replace("INJECT_AGE_COHORTS", json.dumps(age_cohorts))
    html_content = html_content.replace("INJECT_PREFIX_LABELS", json.dumps(top_pref_labels))
    html_content = html_content.replace("INJECT_PREFIX_COUNTS", json.dumps(top_pref_counts))
    html_content = html_content.replace("INJECT_HOUSE_LABELS", json.dumps(top_houses_labels))
    html_content = html_content.replace("INJECT_HOUSE_COUNTS", json.dumps(top_houses_counts))
    
    html_content = html_content.replace("INJECT_VOTERS_JSON", json.dumps(voters_list, ensure_ascii=False))
    
    # Save the report
    base_name = os.path.splitext(csv_name)[0]
    report_name = f"{base_name}_report.html"
    report_path = os.path.join(csv_dir, report_name)
    
    with open(report_path, "w", encoding="utf-8") as out:
        out.write(html_content)
        
    print(f"Generated voter analytics dashboard at: {report_path}")
    
    # Batch Synchronization to update sibling reports with the new dropdown list
    if regenerate_all:
        for other_csv in all_csvs:
            if other_csv != csv_name:
                other_csv_path = os.path.join(csv_dir, other_csv)
                # Call generate_analytics_report with regenerate_all=False to prevent infinite loop
                generate_analytics_report(other_csv_path, regenerate_all=False)
                
    return report_path

if __name__ == "__main__":
    # Test generation with a sample CSV if running directly
    import glob
    csvs = glob.glob("Processed_CSVs/*.csv")
    if csvs:
        print(f"Testing dashboard generation on {csvs[0]}")
        generate_analytics_report(csvs[0])
    else:
        print("No CSVs found in Processed_CSVs directory to test on.")
