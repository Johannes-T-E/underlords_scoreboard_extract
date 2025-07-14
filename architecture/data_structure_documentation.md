# Scoreboard Data Structure Documentation

## Overview
This document describes the data structure for extracting scoreboard information from auto-chess games, designed to provide all necessary information for frontend UI recreation.

## Root Structure
```json
{
  "scoreboard": {
    "metadata": { ... },
    "players": [ ... ],
    "alliances": [ ... ],
    "extraction_info": { ... }
  }
}
```

## Field Descriptions

### Metadata
- `round`: Current round number in the game
- `game_id`: Unique identifier for the game session
- `timestamp`: ISO 8601 timestamp of when the scoreboard was captured
- `game_mode`: Game mode (e.g., "ranked", "normal", "tournament")
- `lobby_size`: Number of players in the lobby
- `current_phase`: Current game phase - "preparation", "combat", "post_combat"
- `time_remaining`: Seconds remaining in current phase

### Players
Each player object contains:
- `player_name`: Player's display name
- `position`: Current leaderboard position (1-8)
- `level`: Player level (affects shop and unit capacity)
- `gold`: Current gold amount
- `health`: Current health
- `max_health`: Maximum health (usually 100)
- `wins`: Number of wins/rounds won
- `losses`: Number of losses/rounds lost
- `net_worth`: Total value of all units and items
- `winstreak`: Current winning streak
- `is_eliminated`: Whether player is eliminated
- `avatar`: Avatar URL or identifier
- `crew`: Array of units currently on the board
- `bench`: Array of units on the bench
- `items`: Array of items in inventory

### Units (Crew and Bench)
Each unit object contains:
- `unit_name`: Name of the unit
- `level`: Star level (1-3)
- `position`: Position on board (x, y coordinates) - only for crew
- `items`: Array of items equipped on this unit
- `alliance`: Primary alliance/faction
- `cost`: Gold cost of the unit
- `health`: Current health
- `max_health`: Maximum health
- `mana`: Current mana
- `max_mana`: Maximum mana

### Items
Each item object contains:
- `name`: Item name
- `id`: Item identifier
- `type`: Item type - "component", "equipment", "consumable"

### Alliances
Each alliance object contains:
- `name`: Alliance name
- `active_level`: Current active level
- `required_units`: Units required for this level
- `current_units`: Current units contributing to this alliance
- `bonus_description`: Description of the alliance bonus

### Extraction Info
- `confidence`: OCR/extraction confidence level (0-1)
- `extraction_time`: When the extraction was performed
- `errors`: Array of any errors encountered during extraction
- `partial_data`: Boolean indicating if some data couldn't be extracted

## Usage Notes

1. **Frontend Implementation**: The frontend can use this structure to recreate the scoreboard with full fidelity
2. **Missing Data**: If extraction fails for certain fields, they should be null or empty arrays
3. **Confidence**: Use the confidence field to indicate reliability of extracted data
4. **Error Handling**: The errors array can contain specific extraction failures for debugging
5. **Extensibility**: Additional fields can be added as needed for specific game variations

## Example Processing Flow

1. Screenshot captured
2. OCR applied to extract text
3. Computer vision used to identify board positions
4. Data parsed into this structure
5. Confidence scores calculated
6. Structure returned to frontend for rendering 