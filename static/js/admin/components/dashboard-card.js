/* Dashboard Card Web Component */

class DashboardCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    connectedCallback() {
        this.render();
    }

    static get observedAttributes() {
        return ['title', 'value', 'subtitle', 'icon', 'color', 'trend', 'trend-value'];
    }

    attributeChangedCallback() {
        this.render();
    }

    get title() {
        return this.getAttribute('title') || '';
    }

    get value() {
        return this.getAttribute('value') || '0';
    }

    get subtitle() {
        return this.getAttribute('subtitle') || '';
    }

    get icon() {
        return this.getAttribute('icon') || 'CHART';
    }

    get color() {
        return this.getAttribute('color') || 'primary';
    }

    get trend() {
        return this.getAttribute('trend') || 'neutral';
    }

    get trendValue() {
        return this.getAttribute('trend-value') || '';
    }

    render() {
        const colorClasses = {
            primary: 'bg-primary',
            success: 'bg-success',
            info: 'bg-info',
            warning: 'bg-warning',
            danger: 'bg-danger',
            secondary: 'bg-secondary'
        };

        const trendIcons = {
            up: '↗',
            down: '↘',
            neutral: '→'
        };

        const trendColors = {
            up: 'text-success',
            down: 'text-danger',
            neutral: 'text-muted'
        };

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    width: 100%;
                }
                
                .card {
                    border: none;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    transition: all 0.3s ease;
                    overflow: hidden;
                    background: white;
                }
                
                .card:hover {
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    transform: translateY(-2px);
                }
                
                .card-header {
                    padding: 1rem 1.25rem 0.5rem;
                    background: transparent;
                    border: none;
                }
                
                .card-body {
                    padding: 0.5rem 1.25rem 1.25rem;
                }
                
                .icon {
                    font-size: 2rem;
                    margin-bottom: 0.5rem;
                }
                
                .title {
                    font-size: 0.875rem;
                    font-weight: 500;
                    color: #6c757d;
                    margin: 0;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .value {
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: #212529;
                    margin: 0.25rem 0;
                    line-height: 1;
                }
                
                .subtitle {
                    font-size: 0.875rem;
                    color: #6c757d;
                    margin: 0;
                }
                
                .trend {
                    display: flex;
                    align-items: center;
                    gap: 0.25rem;
                    font-size: 0.875rem;
                    font-weight: 500;
                    margin-top: 0.5rem;
                }
                
                .bg-primary { background: linear-gradient(135deg, #007bff, #0056b3); color: white; }
                .bg-success { background: linear-gradient(135deg, #28a745, #1e7e34); color: white; }
                .bg-info { background: linear-gradient(135deg, #17a2b8, #117a8b); color: white; }
                .bg-warning { background: linear-gradient(135deg, #ffc107, #e0a800); color: white; }
                .bg-danger { background: linear-gradient(135deg, #dc3545, #bd2130); color: white; }
                .bg-secondary { background: linear-gradient(135deg, #6c757d, #545b62); color: white; }
                
                .text-success { color: #28a745 !important; }
                .text-danger { color: #dc3545 !important; }
                .text-muted { color: #6c757d !important; }
                
                .colored .title,
                .colored .value,
                .colored .subtitle {
                    color: white;
                }
            </style>
            
            <div class="card ${this.color !== 'white' ? colorClasses[this.color] + ' colored' : ''}">
                <div class="card-header">
                    <div class="icon">${this.icon}</div>
                    <h6 class="title">${this.title}</h6>
                </div>
                <div class="card-body">
                    <div class="value">${this.value}</div>
                    ${this.subtitle ? `<p class="subtitle">${this.subtitle}</p>` : ''}
                    ${this.trendValue ? `
                        <div class="trend ${trendColors[this.trend]}">
                            <span>${trendIcons[this.trend]}</span>
                            <span>${this.trendValue}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    updateValue(newValue) {
        this.setAttribute('value', newValue);
    }

    updateTrend(trend, value) {
        this.setAttribute('trend', trend);
        this.setAttribute('trend-value', value);
    }
}

customElements.define('dashboard-card', DashboardCard);
