class ScoreboardApp {
    constructor() {
        this.data = null;
        this.currentSort = { field: 'position', direction: 'asc' };
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSampleData();
    }

    setupEventListeners() {
        const fileInput = document.getElementById('jsonFileInput');
        fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        
        // Sort functionality
        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', (e) => {
                const field = e.target.dataset.sort;
                this.sortBy(field);
            });
        });
    }

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        this.showLoading();
        this.updateFileInfo(file.name, 'Loading...');

        try {
            const text = await file.text();
            const data = JSON.parse(text);
            this.data = data;
            this.displayScoreboard();
            this.updateFileInfo(file.name, 'Loaded successfully');
        } catch (error) {
            this.showError(`Error loading file: ${error.message}`);
            this.updateFileInfo(file.name, 'Error loading file');
        } finally {
            this.hideLoading();
        }
    }

    async loadSampleData() {
        try {
            const response = await fetch('output/scoreboard_data.json');
            if (response.ok) {
                this.data = await response.json();
                this.displayScoreboard();
                this.updateFileInfo('scoreboard_data.json', 'Auto-loaded');
            }
        } catch (error) {
            // Sample data not available, that's okay
        }
    }

    displayScoreboard() {
        if (!this.data || !this.data.players) {
            this.showError('Invalid data format');
            return;
        }

        this.hideError();
        this.renderTable();
        this.renderMetadata();
        this.showScoreboard();
    }

    renderTable() {
        const playersPrefix = document.getElementById('playersPrefix');
        const playersScrollable = document.getElementById('playersScrollable');
        
        playersPrefix.innerHTML = '';
        playersScrollable.innerHTML = '';

        // Sort players by current sort criteria
        const sortedPlayers = this.getSortedPlayers();

        sortedPlayers.forEach((player, index) => {
            const prefixRow = this.createPrefixRow(player, index + 1);
            const scrollableRow = this.createScrollableRow(player);
            
            playersPrefix.appendChild(prefixRow);
            playersScrollable.appendChild(scrollableRow);
        });
    }

    createPrefixRow(player, position) {
        const row = document.createElement('div');
        row.className = 'player-row row-prefix';
        
        row.innerHTML = `
            <div class="col-place">
                <div class="place-number">${position}</div>
            </div>
            <div class="col-player">
                <div class="name-container">
                    <div class="player-name">${player.player_name || 'Unknown'}</div>
                    <div class="name-bottom">
                        <div class="unit-display">
                            <div class="unit-icon"></div>
                            <div class="unit-label">${player.level || 0}</div>
                        </div>
                        <div class="gold-display">
                            <div class="gold-icon"></div>
                            <div class="gold-label">${player.gold || 0}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return row;
    }

    createScrollableRow(player) {
        const row = document.createElement('div');
        row.className = 'player-row row-scrollable';
        
        row.innerHTML = `
            <div class="col-health">
                <div class="health-column">
                    <div class="health-large">${player.health !== null ? player.health : '—'}</div>
                    <div class="health-icon-large"></div>
                </div>
            </div>
            <div class="col-record">
                <div class="record-label">${this.formatRecord(player)}</div>
            </div>
            <div class="col-networth">
                <div class="networth-label">${player.networth !== null ? player.networth : '—'}</div>
            </div>
            <div class="col-roster">
                ${this.createRosterContainer(player.crew || [])}
            </div>
            <div class="col-bench">
                ${this.createBenchContainer(player.bench || [])}
            </div>
        `;
        
        return row;
    }

    createRosterContainer(crew) {
        const container = document.createElement('div');
        container.className = 'roster-container';
        
        crew.forEach(unit => {
            const unitElement = this.createUnitElement(unit);
            container.appendChild(unitElement);
        });
        
        return container.outerHTML;
    }

    createBenchContainer(bench) {
        const container = document.createElement('div');
        container.className = 'bench-container';
        
        bench.forEach(unit => {
            const unitElement = this.createUnitElement(unit);
            container.appendChild(unitElement);
        });
        
        return container.outerHTML;
    }

    createUnitElement(unit) {
        const unitDiv = document.createElement('div');
        unitDiv.className = 'roster-unit';
        
        const heroName = unit.hero_name || 'unknown';
        const starLevel = unit.star_level || 0;
        const heroImage = `assets/icons/hero_icons_scaled_56x56/npc_dota_hero_${heroName}_png.png`;
        
        unitDiv.innerHTML = `
            <img src="${heroImage}" 
                 alt="${heroName}" 
                 class="hero-portrait"
                 onerror="this.src='assets/icons/hero_icons_scaled_56x56/npc_dota_hero_abaddon_png.png'">
            <div class="stars-container">
                <div class="star-list">
                    ${this.createStarIcons(starLevel)}
                </div>
            </div>
        `;
        
        return unitDiv;
    }

    createStarIcons(starLevel) {
        let stars = '';
        for (let i = 0; i < starLevel; i++) {
            stars += `<div class="star-icon rank${Math.min(starLevel, 3)}"></div>`;
        }
        return stars;
    }

    formatRecord(player) {
        if (player.wins === null || player.losses === null) {
            return '—';
        }
        const wins = player.wins || 0;
        const losses = player.losses || 0;
        return `${wins}-${losses}`;
    }

    getSortedPlayers() {
        if (!this.data.players) return [];
        
        const players = [...this.data.players];
        
        return players.sort((a, b) => {
            let aValue, bValue;
            
            switch (this.currentSort.field) {
                case 'health':
                    aValue = a.health !== null ? a.health : -1;
                    bValue = b.health !== null ? b.health : -1;
                    break;
                case 'record':
                    aValue = (a.wins !== null && a.losses !== null) ? (a.wins - a.losses) : -999;
                    bValue = (b.wins !== null && b.losses !== null) ? (b.wins - b.losses) : -999;
                    break;
                case 'networth':
                    aValue = a.networth !== null ? a.networth : -1;
                    bValue = b.networth !== null ? b.networth : -1;
                    break;
                default:
                    aValue = a.position || 0;
                    bValue = b.position || 0;
            }
            
            const result = aValue - bValue;
            return this.currentSort.direction === 'asc' ? result : -result;
        });
    }

    sortBy(field) {
        if (this.currentSort.field === field) {
            this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.currentSort.field = field;
            this.currentSort.direction = 'desc';
        }
        
        this.updateSortIndicators();
        this.renderTable();
    }

    updateSortIndicators() {
        // Remove active class from all headers
        document.querySelectorAll('.sortable').forEach(header => {
            header.classList.remove('active');
            const arrow = header.querySelector('.sort-arrow');
            if (arrow) arrow.remove();
        });
        
        // Add active class and arrow to current sort header
        const activeHeader = document.querySelector(`[data-sort="${this.currentSort.field}"]`);
        if (activeHeader) {
            activeHeader.classList.add('active');
            const arrow = document.createElement('span');
            arrow.className = 'sort-arrow';
            arrow.textContent = this.currentSort.direction === 'asc' ? '▲' : '▼';
            activeHeader.appendChild(arrow);
        }
    }

    renderMetadata() {
        if (!this.data.metadata) return;
        
        const metadata = this.data.metadata;
        document.getElementById('totalPlayers').textContent = metadata.total_players || 0;
        document.getElementById('extractionTime').textContent = `${metadata.extraction_time?.toFixed(3) || 0}s`;
        document.getElementById('crewUnits').textContent = metadata.extraction_summary?.total_crew_units || 0;
        document.getElementById('benchUnits').textContent = metadata.extraction_summary?.total_bench_units || 0;
        
        this.showMetadata();
    }

    updateFileInfo(name, status) {
        document.getElementById('fileName').textContent = name;
        document.getElementById('fileStatus').textContent = status;
    }

    showLoading() {
        document.getElementById('loading').classList.remove('hide');
    }

    hideLoading() {
        document.getElementById('loading').classList.add('hide');
    }

    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.querySelector('.error-text').textContent = message;
        errorDiv.classList.remove('hide');
    }

    hideError() {
        document.getElementById('errorMessage').classList.add('hide');
    }

    showScoreboard() {
        document.getElementById('scoreboard').classList.remove('hide');
    }

    showMetadata() {
        document.getElementById('metadata').classList.remove('hide');
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ScoreboardApp();
}); 