/* Dashboard Chart Web Component */

class DashboardChart extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.chartData = null;
    }

    connectedCallback() {
        this.render();
    }

    static get observedAttributes() {
        return ['title', 'type', 'height'];
    }

    attributeChangedCallback() {
        this.render();
    }

    get title() {
        return this.getAttribute('title') || 'Chart';
    }

    get type() {
        return this.getAttribute('type') || 'bar';
    }

    get height() {
        return this.getAttribute('height') || '300px';
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    width: 100%;
                }
                
                .chart-container {
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 1.5rem;
                    transition: all 0.3s ease;
                }
                
                .chart-container:hover {
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                }
                
                .chart-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1rem;
                    padding-bottom: 0.75rem;
                    border-bottom: 2px solid #f8f9fa;
                }
                
                .chart-title {
                    font-size: 1.125rem;
                    font-weight: 600;
                    color: #212529;
                    margin: 0;
                }
                
                .chart-actions {
                    display: flex;
                    gap: 0.5rem;
                }
                
                .chart-btn {
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 0.375rem 0.75rem;
                    font-size: 0.875rem;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .chart-btn:hover {
                    background: #e9ecef;
                    border-color: #adb5bd;
                }
                
                .chart-content {
                    position: relative;
                    height: ${this.height};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .chart-canvas {
                    width: 100%;
                    height: 100%;
                }
                
                .chart-placeholder {
                    text-align: center;
                    color: #6c757d;
                    font-style: italic;
                }
                
                .loading {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    color: #6c757d;
                }
                
                .spinner {
                    width: 1rem;
                    height: 1rem;
                    border: 2px solid #f3f3f3;
                    border-top: 2px solid #007bff;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
            
            <div class="chart-container">
                <div class="chart-header">
                    <h3 class="chart-title">${this.title}</h3>
                    <div class="chart-actions">
                        <button class="chart-btn" id="refresh-btn" title="Refresh">🔄</button>
                        <button class="chart-btn" id="export-btn" title="Export">📊</button>
                    </div>
                </div>
                <div class="chart-content">
                    <div class="chart-placeholder" id="placeholder">
                        <div class="loading">
                            <div class="spinner"></div>
                            <span>Loading chart data...</span>
                        </div>
                    </div>
                    <canvas class="chart-canvas" id="chart-canvas" style="display: none;"></canvas>
                </div>
            </div>
        `;

        this.setupEventListeners();
    }

    setupEventListeners() {
        const refreshBtn = this.shadowRoot.getElementById('refresh-btn');
        const exportBtn = this.shadowRoot.getElementById('export-btn');

        refreshBtn?.addEventListener('click', () => {
            this.dispatchEvent(new CustomEvent('refresh', { bubbles: true }));
        });

        exportBtn?.addEventListener('click', () => {
            this.exportChart();
        });
    }

    setData(data, options = {}) {
        this.chartData = data;
        const placeholder = this.shadowRoot.getElementById('placeholder');
        const canvas = this.shadowRoot.getElementById('chart-canvas');

        if (!data || data.length === 0) {
            placeholder.innerHTML = '<div class="chart-placeholder">No data available</div>';
            canvas.style.display = 'none';
            return;
        }

        placeholder.style.display = 'none';
        canvas.style.display = 'block';

        this.renderChart(data, options);
    }

    renderChart(data, options) {
        const canvas = this.shadowRoot.getElementById('chart-canvas');
        const ctx = canvas.getContext('2d');

        // Simple chart rendering based on type
        switch (this.type) {
            case 'bar':
                this.renderBarChart(ctx, canvas, data, options);
                break;
            case 'line':
                this.renderLineChart(ctx, canvas, data, options);
                break;
            case 'pie':
                this.renderPieChart(ctx, canvas, data, options);
                break;
            default:
                this.renderBarChart(ctx, canvas, data, options);
        }
    }

    renderBarChart(ctx, canvas, data, options) {
        const { width, height } = canvas.getBoundingClientRect();
        canvas.width = width;
        canvas.height = height;

        const padding = 40;
        const chartWidth = width - 2 * padding;
        const chartHeight = height - 2 * padding;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        if (!data || data.length === 0) return;

        // Find max value
        const maxValue = Math.max(...data.map(d => d.value));
        const barWidth = chartWidth / data.length * 0.8;
        const barSpacing = chartWidth / data.length * 0.2;

        // Colors
        const colors = ['#007bff', '#28a745', '#17a2b8', '#ffc107', '#dc3545', '#6c757d'];

        // Draw bars
        data.forEach((item, index) => {
            const barHeight = (item.value / maxValue) * chartHeight;
            const x = padding + index * (barWidth + barSpacing) + barSpacing / 2;
            const y = height - padding - barHeight;

            // Bar
            ctx.fillStyle = colors[index % colors.length];
            ctx.fillRect(x, y, barWidth, barHeight);

            // Value label
            ctx.fillStyle = '#212529';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(item.value.toString(), x + barWidth / 2, y - 5);

            // Category label
            ctx.save();
            ctx.translate(x + barWidth / 2, height - padding + 15);
            ctx.rotate(-Math.PI / 6);
            ctx.textAlign = 'right';
            ctx.fillText(item.label, 0, 0);
            ctx.restore();
        });

        // Draw axes
        ctx.strokeStyle = '#dee2e6';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();
    }

    renderLineChart(ctx, canvas, data, options) {
        const { width, height } = canvas.getBoundingClientRect();
        canvas.width = width;
        canvas.height = height;

        const padding = 40;
        const chartWidth = width - 2 * padding;
        const chartHeight = height - 2 * padding;

        ctx.clearRect(0, 0, width, height);

        if (!data || data.length === 0) return;

        const maxValue = Math.max(...data.map(d => d.value));
        const pointSpacing = chartWidth / (data.length - 1);

        // Draw line
        ctx.strokeStyle = '#007bff';
        ctx.lineWidth = 3;
        ctx.beginPath();

        data.forEach((item, index) => {
            const x = padding + index * pointSpacing;
            const y = height - padding - (item.value / maxValue) * chartHeight;

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Draw points
        ctx.fillStyle = '#007bff';
        data.forEach((item, index) => {
            const x = padding + index * pointSpacing;
            const y = height - padding - (item.value / maxValue) * chartHeight;

            ctx.beginPath();
            ctx.arc(x, y, 4, 0, 2 * Math.PI);
            ctx.fill();

            // Value label
            ctx.fillStyle = '#212529';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(item.value.toString(), x, y - 10);

            // Category label
            ctx.fillText(item.label, x, height - padding + 15);
        });

        // Draw axes
        ctx.strokeStyle = '#dee2e6';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();
    }

    renderPieChart(ctx, canvas, data, options) {
        const { width, height } = canvas.getBoundingClientRect();
        canvas.width = width;
        canvas.height = height;

        ctx.clearRect(0, 0, width, height);

        if (!data || data.length === 0) {
            // Draw "No data" message
            ctx.fillStyle = '#6c757d';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No data available', width / 2, height / 2);
            return;
        }

        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.max(10, Math.min(width, height) / 2 - 40); // Ensure minimum radius of 10

        const total = data.reduce((sum, item) => sum + item.value, 0);
        
        if (total === 0) {
            // Draw "No data" message
            ctx.fillStyle = '#6c757d';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No data available', centerX, centerY);
            return;
        }
        
        const colors = ['#007bff', '#28a745', '#17a2b8', '#ffc107', '#dc3545', '#6c757d'];

        let currentAngle = -Math.PI / 2;

        data.forEach((item, index) => {
            if (item.value <= 0) return; // Skip zero or negative values
            
            const sliceAngle = (item.value / total) * 2 * Math.PI;

            // Draw slice
            ctx.fillStyle = colors[index % colors.length];
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            ctx.closePath();
            ctx.fill();

            // Draw label only if slice is large enough
            if (sliceAngle > 0.2) { // Only show label if slice is larger than ~11 degrees
                const labelAngle = currentAngle + sliceAngle / 2;
                const labelX = centerX + Math.cos(labelAngle) * (radius * 0.7);
                const labelY = centerY + Math.sin(labelAngle) * (radius * 0.7);

                ctx.fillStyle = 'white';
                ctx.font = 'bold 12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(item.value.toString(), labelX, labelY);
            }

            currentAngle += sliceAngle;
        });
    }

    exportChart() {
        const canvas = this.shadowRoot.getElementById('chart-canvas');
        if (canvas && this.chartData) {
            const link = document.createElement('a');
            link.download = `${this.title.toLowerCase().replace(/\s+/g, '-')}-chart.png`;
            link.href = canvas.toDataURL();
            link.click();
        }
    }

    showLoading() {
        const placeholder = this.shadowRoot.getElementById('placeholder');
        const canvas = this.shadowRoot.getElementById('chart-canvas');
        
        placeholder.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <span>Loading chart data...</span>
            </div>
        `;
        placeholder.style.display = 'flex';
        canvas.style.display = 'none';
    }

    showError(message) {
        const placeholder = this.shadowRoot.getElementById('placeholder');
        const canvas = this.shadowRoot.getElementById('chart-canvas');
        
        placeholder.innerHTML = `<div class="chart-placeholder">Error: ${message}</div>`;
        placeholder.style.display = 'block';
        canvas.style.display = 'none';
    }
}

customElements.define('dashboard-chart', DashboardChart);
