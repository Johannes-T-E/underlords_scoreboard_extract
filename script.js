// This frontend now uses polling to fetch scoreboard_data.json and update the UI live, without reloading the page or re-instantiating ScoreboardApp.

class ScoreboardApp {
    constructor() {
        console.log('ScoreboardApp instance created');
        this.data = null;
        this.lastState = null; // <-- Add this
        this.currentSort = { field: 'position', direction: 'asc' };
        this.playerChangeEvents = {}; // Store change events per player
        this.init();
        this.pollScoreboardData(); // Start polling for live updates
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

    // Helper to check if player order is the same
    samePlayerOrder(arr1, arr2) {
        if (!arr1 || !arr2 || arr1.length !== arr2.length) return false;
        for (let i = 0; i < arr1.length; i++) {
            if (arr1[i].row_number !== arr2[i].row_number) return false;
        }
        return true;
    }

    displayScoreboard() {
        if (!this.data || !this.data.players) {
            this.showError('Invalid data format');
            return;
        }

        this.hideError();
        let shouldRender = false;
        if (!this.lastState) {
            shouldRender = true;
            console.log('[Scoreboard] Full render: no lastState');
        } else if (this.lastState.players.length !== this.data.players.length) {
            shouldRender = true;
            console.log('[Scoreboard] Full render: player count changed');
        } else if (!this.samePlayerOrder(this.lastState.players, this.data.players)) {
            shouldRender = true;
            console.log('[Scoreboard] Full render: player order changed');
        }
        if (shouldRender) {
            this.renderTable();
            this.lastState = JSON.parse(JSON.stringify(this.data));
        } else {
            this.updateTableWithDiff(this.data.players);
        }
        this.renderMetadata();
        this.showScoreboard();
    }

    // Helper for deep array comparison
    arraysEqual(arr1, arr2) {
        if (arr1 === arr2) return true;
        if (!arr1 || !arr2) return false;
        if (arr1.length !== arr2.length) return false;
        for (let i = 0; i < arr1.length; i++) {
            if (!this.objectsEqual(arr1[i], arr2[i])) return false;
        }
        return true;
    }
    objectsEqual(obj1, obj2) {
        // Shallow compare for now, can be deep if needed
        return JSON.stringify(obj1) === JSON.stringify(obj2);
    }

    updateTableWithDiff(players) {
        if (!this.lastState) {
            this.renderTable();
            this.lastState = JSON.parse(JSON.stringify(this.data));
            return;
        }

        players.forEach((player, idx) => {
            const lastPlayer = this.lastState.players[idx];
            const playerId = player.row_number;

            // Debug logging for all players
            console.log(`[DEBUG] ${player.player_name} - Current health: ${player.health}, Last health: ${lastPlayer.health}`);

            // Gold - only update if new value is not null and different from last valid value
            if (player.gold !== null && player.gold !== lastPlayer.gold) {
                this.updateGoldDisplay(playerId, player.gold);
                this.logGoldChange(player, lastPlayer);
                // Only show change event if the last value was also not null (avoid false positives)
                if (lastPlayer.gold !== null) {
                    this.addChangeEvent(playerId, { type: 'gold', delta: player.gold - lastPlayer.gold });
                }
            }
            // Health - only update if new value is not null and different from last valid value
            if (player.health !== null && player.health !== lastPlayer.health) {
                console.log(`[DEBUG] Health change detected for ${player.player_name}: ${lastPlayer.health} -> ${player.health} (delta: ${delta})`);
                this.updateHealthDisplay(playerId, player.health);
                this.logHealthChange(player, lastPlayer);
                // Only show change event if the last value was also not null (avoid false positives)
                if (lastPlayer.health !== null) {
                    this.addChangeEvent(playerId, { type: 'health', delta: player.health - lastPlayer.health });
                }
            }
            // Level - only update if new value is not null and different from last valid value
            if (player.level !== null && player.level !== lastPlayer.level) {
                this.updateLevelDisplay(playerId, player.level);
                this.logLevelChange(player, lastPlayer);
                // Only show change event if the last value was also not null (avoid false positives)
                if (lastPlayer.level !== null) {
                    this.addChangeEvent(playerId, { type: 'level', delta: player.level - lastPlayer.level });
                }
            }
            // Bench/Crew (units) - only update if arrays are different and not null
            if (player.bench && !this.arraysEqual(player.bench, lastPlayer.bench)) {
                this.updateBenchDisplay(playerId, player.bench);
                this.logBenchChange(player, lastPlayer);
                this.addChangeEvent(playerId, { type: 'bench', delta: 1 }); // Placeholder
            }
            if (player.crew && !this.arraysEqual(player.crew, lastPlayer.crew)) {
                this.updateCrewDisplay(playerId, player.crew);
                this.logCrewChange(player, lastPlayer);
                this.addChangeEvent(playerId, { type: 'crew', delta: 1 }); // Placeholder
            }
        });

        // Save new state, but preserve last known valid values for null fields
        const newState = JSON.parse(JSON.stringify(this.data));
        newState.players.forEach((player, idx) => {
            const lastPlayer = this.lastState.players[idx];
            // Preserve last known valid values for null fields
            if (player.gold === null && lastPlayer.gold !== null) {
                newState.players[idx].gold = lastPlayer.gold;
                console.log(`[DEBUG] Preserving gold: ${lastPlayer.gold} for ${player.player_name}`);
            }
            if (player.health === null && lastPlayer.health !== null) {
                newState.players[idx].health = lastPlayer.health;
                console.log(`[DEBUG] Preserving health: ${lastPlayer.health} for ${player.player_name}`);
            }
            if (player.level === null && lastPlayer.level !== null) {
                newState.players[idx].level = lastPlayer.level;
                console.log(`[DEBUG] Preserving level: ${lastPlayer.level} for ${player.player_name}`);
            }
        });
        this.lastState = newState;
    }

    // Add a change event to the scrolling bar for a player
    addChangeEvent(playerId, event) {
        if (!this.playerChangeEvents[playerId]) this.playerChangeEvents[playerId] = [];
        // Prune old events (keep only last 10 or those not expired)
        this.pruneChangeEvents(playerId);
        // Add new event to the front
        this.playerChangeEvents[playerId].unshift({ ...event, timestamp: Date.now() });
        // Update the DOM if the bar exists
        const bar = document.querySelector(`#player-${playerId} .change-bar`);
        if (bar) this.renderChangeBar(playerId, bar);
        // Remove after 4s
        setTimeout(() => {
            this.pruneChangeEvents(playerId);
            const bar2 = document.querySelector(`#player-${playerId} .change-bar`);
            if (bar2) this.renderChangeBar(playerId, bar2);
        }, 4000);
    }

    pruneChangeEvents(playerId) {
        const now = Date.now();
        if (!this.playerChangeEvents[playerId]) return;
        // Remove events older than 4s, keep max 10
        this.playerChangeEvents[playerId] = this.playerChangeEvents[playerId].filter(e => now - e.timestamp < 4000).slice(0, 10);
    }

    renderChangeBar(playerId, bar) {
        bar.innerHTML = '';
        const events = this.playerChangeEvents[playerId] || [];
        events.forEach(event => {
            const el = document.createElement('div');
            el.className = 'change-event';
            if (event.type === 'gold') {
                el.textContent = (event.delta > 0 ? '+' : '') + event.delta + 'g';
                el.style.color = event.delta < 0 ? '#e6c200' : '#bada55';
            } else if (event.type === 'health') {
                el.textContent = (event.delta > 0 ? '+' : '') + event.delta + 'hp';
                el.style.color = event.delta < 0 ? '#e74c3c' : '#2ecc40';
            } else if (event.type === 'level') {
                el.textContent = 'Lv' + (event.delta > 0 ? '+' : '') + event.delta;
                el.style.color = '#00bfff';
            } else if (event.type === 'bench') {
                el.textContent = 'Bench';
                el.style.color = '#aaa';
            } else if (event.type === 'crew') {
                el.textContent = 'Crew';
                el.style.color = '#aaa';
            }
            el.style.marginBottom = '2px';
            el.style.fontSize = '12px';
            el.style.whiteSpace = 'nowrap';
            bar.appendChild(el);
        });
    }

    updateGoldDisplay(playerId, gold) {
        const el = document.querySelector(`#playersPrefix #player-${playerId} .gold-label`);
        if (el) el.textContent = gold;
    }
    updateHealthDisplay(playerId, health) {
        const el = document.querySelector(`#playersScrollable #player-${playerId} .health-large`);
        if (el) el.textContent = health;
    }
    updateLevelDisplay(playerId, level) {
        const el = document.querySelector(`#playersPrefix #player-${playerId} .unit-label`);
        if (el) el.textContent = level;
    }
    updateBenchDisplay(playerId, bench) {
        // Find the player's row in the scrollable table
        const playerRow = document.querySelector(`#playersScrollable #player-${playerId}`);
        if (!playerRow) return;
        // Find the bench container inside this row
        const benchCol = playerRow.querySelector('.col-bench');
        if (!benchCol) return;
        // Replace the bench container's HTML
        benchCol.innerHTML = this.createBenchContainer(bench);
    }
    updateCrewDisplay(playerId, crew) {
        // Find the player's row in the scrollable table
        const playerRow = document.querySelector(`#playersScrollable #player-${playerId}`);
        if (!playerRow) return;
        // Find the roster container inside this row
        const rosterCol = playerRow.querySelector('.col-roster');
        if (!rosterCol) return;
        // Replace the roster container's HTML
        rosterCol.innerHTML = this.createRosterContainer(crew);
    }

    // Logging functions
    logGoldChange(player, lastPlayer) {
        const delta = player.gold - lastPlayer.gold;
        if (delta > 0) {
            console.log(`${player.player_name} gained ${delta} gold`);
        } else if (delta < 0) {
            console.log(`${player.player_name} spent ${-delta} gold`);
        }
    }
    logHealthChange(player, lastPlayer) {
        const delta = player.health - lastPlayer.health;
        console.log(`[DEBUG] logHealthChange called: ${player.player_name} - ${lastPlayer.health} -> ${player.health} (delta: ${delta})`);
        if (delta < 0) {
            console.log(`${player.player_name} lost ${-delta} HP`);
        } else if (delta > 0) {
            console.log(`${player.player_name} gained ${delta} HP`);
        }
    }
    logLevelChange(player, lastPlayer) {
        if (player.level > lastPlayer.level) {
            console.log(`${player.player_name} leveled up to ${player.level}`);
        }
    }
    logBenchChange(player, lastPlayer) {
        // Compare arrays for new units
        // ...your code here...
    }
    logCrewChange(player, lastPlayer) {
        // Compare arrays for new units
        // ...your code here...
    }

    renderTable() {
        console.log('[Scoreboard] renderTable called: full DOM re-render');
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
        row.id = `player-${player.row_number}`;
        row.innerHTML = `
            <div class="col-place" style="display: flex; align-items: center;">
                <div class="change-bar" style="width: 40px; min-height: 40px; display: flex; flex-direction: column; align-items: flex-end; justify-content: flex-start; margin-right: 4px; background: rgba(0,0,0,0.08); border-radius: 6px;"></div>
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
        // After row is created, populate the change bar with any existing events
        setTimeout(() => {
            const bar = row.querySelector('.change-bar');
            if (bar) this.renderChangeBar(player.row_number, bar);
        }, 0);
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

    pollScoreboardData(intervalMs = 1000) {
        const fetchAndUpdate = async () => {
            try {
                // Use Flask backend endpoint
                const response = await fetch('http://localhost:5000/api/scoreboard', { cache: 'no-store' });
                if (response.ok) {
                    const data = await response.json();
                    this.data = data;
                    this.displayScoreboard();
                }
            } catch (e) {
                // Optionally show error
            } finally {
                setTimeout(fetchAndUpdate, intervalMs);
            }
        };
        fetchAndUpdate();
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (!window.scoreboardApp) {
        window.scoreboardApp = new ScoreboardApp();
    }
}); 