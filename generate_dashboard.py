#!/usr/bin/env python3
"""
Resume Explorer - Test Dashboard Generator
Generates HTML dashboard from test results JSON
Usage: python generate_dashboard.py test_results.json
"""

import json
import sys
import os
from datetime import datetime

def generate_dashboard(test_data):
    """Generate HTML dashboard from test data"""

    # Calculate summary stats
    total_tests = len(test_data['test_cases'])
    passed = sum(1 for tc in test_data['test_cases'] if tc['status'] == 'PASS')
    failed = sum(1 for tc in test_data['test_cases'] if tc['status'] == 'FAIL')
    skipped = sum(1 for tc in test_data['test_cases'] if tc['status'] == 'SKIP')
    pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

    # Provider metrics
    providers = test_data.get('provider_metrics', [])

    # Generate provider comparison rows
    provider_rows = ""
    if providers:
        provider_headers = "".join([f"<th>{p['provider'].title()}</th>" for p in providers])
        provider_rows = f"""
            <tr>
                <td><strong>Extraction Time</strong></td>
                {"".join([f"<td>{p['extraction_time_sec']:.1f}s</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Total Entities</strong></td>
                {"".join([f"<td>{sum(p['entities_extracted'].values())}</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Jobs Extracted</strong></td>
                {"".join([f"<td>{p['entities_extracted'].get('jobs', 0)}</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Skills Extracted</strong></td>
                {"".join([f"<td>{p['entities_extracted'].get('skills', 0)}</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Avg Confidence</strong></td>
                {"".join([f"<td>{p['avg_confidence']:.2f}</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Accuracy %</strong></td>
                {"".join([f"<td>{p.get('accuracy_percent', 'N/A')}%</td>" for p in providers])}
            </tr>
        """

    # Generate test result rows
    test_rows = ""
    for tc in test_data['test_cases']:
        status_class = f"status-{tc['status'].lower()}"
        test_rows += f"""
            <tr>
                <td>{tc['test_id']}</td>
                <td>{tc['category']}</td>
                <td>{tc['name']}</td>
                <td class="{status_class}">{tc['status']}</td>
                <td>{tc.get('execution_time_sec', 'N/A')}s</td>
                <td>{tc.get('notes', '')[:100]}</td>
            </tr>
        """

    # Prepare provider data for Chart.js
    provider_data = json.dumps([{
        'provider': p['provider'],
        'total': sum(p['entities_extracted'].values()),
        'jobs': p['entities_extracted'].get('jobs', 0),
        'skills': p['entities_extracted'].get('skills', 0),
        'time': p['extraction_time_sec']
    } for p in providers])

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Explorer - E2E Test Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        .status-pass {{ color: #28a745; font-weight: bold; }}
        .status-fail {{ color: #dc3545; font-weight: bold; }}
        .status-skip {{ color: #6c757d; font-weight: bold; }}
        .metric-card {{ border-left: 4px solid #007bff; }}
        .chart-container {{ position: relative; height: 300px; margin: 20px 0; }}
        .provider-winner {{ background-color: #d4edda; }}
    </style>
</head>
<body>
<div class="container my-5">
    <!-- Section 1: Executive Summary -->
    <div class="card metric-card mb-4">
        <div class="card-body">
            <h1 class="card-title">📊 Resume Explorer - End-to-End Test Report</h1>
            <p class="text-muted">
                Test Date: {test_data['test_execution']['start_time'][:10]} |
                Tester: {test_data['test_execution'].get('tester_name', 'N/A')} |
                Duration: {test_data['test_execution'].get('end_time', 'N/A')[:10]}
            </p>
            <hr>
            <div class="row text-center">
                <div class="col-md-3">
                    <h2 class="{"status-pass" if pass_rate >= 90 else "status-fail"}">{pass_rate:.1f}%</h2>
                    <p class="text-muted">Pass Rate</p>
                </div>
                <div class="col-md-3">
                    <h2>{total_tests}</h2>
                    <p class="text-muted">Total Tests</p>
                </div>
                <div class="col-md-3">
                    <h2 class="status-pass">{passed}</h2>
                    <p class="text-muted">Passed</p>
                </div>
                <div class="col-md-3">
                    <h2 class="{"status-fail" if failed > 0 else "text-muted"}">{failed}</h2>
                    <p class="text-muted">Failed</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Section 2: Visual Charts -->
    <div class="row mb-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Test Results by Status</h5>
                    <div class="chart-container">
                        <canvas id="statusPieChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Provider Comparison - Total Entities</h5>
                    <div class="chart-container">
                        <canvas id="providerBarChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="row mb-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Extraction Time Comparison</h5>
                    <div class="chart-container">
                        <canvas id="timeBarChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Provider Accuracy Radar</h5>
                    <div class="chart-container">
                        <canvas id="accuracyRadarChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Section 3: Provider Comparison Table -->
    {"<div class='card mb-4'><div class='card-body'><h5>🔬 Multi-Provider Comparison Matrix</h5><table class='table table-bordered'><thead><tr><th>Metric</th>" + provider_headers + "</tr></thead><tbody>" + provider_rows + "</tbody></table></div></div>" if providers else ""}

    <!-- Section 4: Detailed Test Results -->
    <div class="card mb-4">
        <div class="card-body">
            <h5>📋 Detailed Test Results</h5>
            <div class="table-responsive">
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            <th>Test ID</th>
                            <th>Category</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Time</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {test_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="text-center text-muted mt-5 mb-3">
        <p>Generated by Resume Explorer Test Dashboard Generator</p>
        <p>Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</div>

<script>
// Test data
const providerData = {provider_data};

// Chart 1: Status Pie Chart
const statusCtx = document.getElementById('statusPieChart').getContext('2d');
new Chart(statusCtx, {{
    type: 'pie',
    data: {{
        labels: ['Passed', 'Failed', 'Skipped'],
        datasets: [{{
            data: [{passed}, {failed}, {skipped}],
            backgroundColor: ['#28a745', '#dc3545', '#6c757d']
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ position: 'bottom' }}
        }}
    }}
}});

// Chart 2: Provider Entity Bar Chart
if (providerData.length > 0) {{
    const providerCtx = document.getElementById('providerBarChart').getContext('2d');
    new Chart(providerCtx, {{
        type: 'bar',
        data: {{
            labels: providerData.map(p => p.provider.charAt(0).toUpperCase() + p.provider.slice(1)),
            datasets: [
                {{
                    label: 'Jobs',
                    data: providerData.map(p => p.jobs),
                    backgroundColor: '#28a745'
                }},
                {{
                    label: 'Skills',
                    data: providerData.map(p => p.skills),
                    backgroundColor: '#ffc107'
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom' }}
            }},
            scales: {{
                y: {{ beginAtZero: true }}
            }}
        }}
    }});

    // Chart 3: Extraction Time Bar Chart
    const timeCtx = document.getElementById('timeBarChart').getContext('2d');
    new Chart(timeCtx, {{
        type: 'bar',
        data: {{
            labels: providerData.map(p => p.provider.charAt(0).toUpperCase() + p.provider.slice(1)),
            datasets: [{{
                label: 'Extraction Time (seconds)',
                data: providerData.map(p => p.time),
                backgroundColor: '#007bff'
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }}
            }},
            scales: {{
                y: {{ beginAtZero: true }}
            }}
        }}
    }});

    // Chart 4: Accuracy Radar (placeholder with sample data)
    const radarCtx = document.getElementById('accuracyRadarChart').getContext('2d');
    new Chart(radarCtx, {{
        type: 'radar',
        data: {{
            labels: ['Person', 'Jobs', 'Skills', 'Education', 'Relationships'],
            datasets: providerData.map((p, i) => ({{
                label: p.provider.charAt(0).toUpperCase() + p.provider.slice(1),
                data: [95, 90, 85, 88, 92], // Placeholder - replace with actual accuracy data
                backgroundColor: ['rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)'][i],
                borderColor: ['rgb(255, 99, 132)', 'rgb(54, 162, 235)', 'rgb(255, 206, 86)'][i],
                borderWidth: 2
            }}))
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                r: {{
                    beginAtZero: true,
                    max: 100
                }}
            }},
            plugins: {{
                legend: {{ position: 'bottom' }}
            }}
        }}
    }});
}}
</script>
</body>
</html>
"""
    return html

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_dashboard.py test_results.json")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    with open(input_file, 'r') as f:
        test_data = json.load(f)

    html = generate_dashboard(test_data)

    output_file = "test_report.html"
    with open(output_file, 'w') as f:
        f.write(html)

    abs_path = os.path.abspath(output_file)
    print(f"✅ Dashboard generated: {output_file}")
    print(f"📊 Open in browser: file://{abs_path}")
