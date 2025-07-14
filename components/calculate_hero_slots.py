def calculate_hero_slots(crew_column_start_x, crew_column_end_x, row_start_y=93, hero_icon_width=56, center_spacing=80, top_margin=5, max_slots=None):
    """
    Calculate complete hero slot positions within a column.
    
    Layout:
    - First hero center: 28px from column start (56px/2)
    - Each subsequent center: 80px apart
    - Hero width: 56px (±28px from center)
    - Hero height: Same as width (56px)
    - Top margin: 5px from row start
    
    Args:
        crew_column_start_x: Start x position of column
        crew_column_end_x: End x position of column
        row_start_y: Start y position of row
        hero_icon_width: Width/height of each hero slot in pixels (default 56px)
        center_spacing: Distance between hero centers (default 80px)
        top_margin: Top margin from row start (default 5px)
        max_slots: Maximum number of slots (None for unlimited, 10 for crew, 8 for bench)
    
    Returns:
        List of slot dictionaries with complete positioning:
        {
            'x_start': int, 'x_end': int, 'x_center': int,
            'y_start': int, 'y_end': int, 'y_center': int,
            'width': int, 'height': int
        }
    """
    hero_icon_height = hero_icon_width  # Height equals width
    first_center_offset = hero_icon_width // 2  # 28px from column start
    half_hero_width = hero_icon_width // 2      # 28px
    half_hero_height = hero_icon_height // 2    # 28px
    
    # Calculate vertical positions (same for all slots in this row)
    y_start = row_start_y + top_margin
    y_end = y_start + hero_icon_height
    y_center = y_start + half_hero_height
    
    # Calculate maximum slots that fit within column boundaries
    column_width = crew_column_end_x - crew_column_start_x
    available_width = column_width - first_center_offset - half_hero_width
    
    # Maximum slots based on spacing (first slot doesn't need spacing)
    max_slots_by_width = 1 + max(0, available_width // center_spacing)
    
    # Apply user-defined max_slots limit if provided
    if max_slots is not None:
        max_slots_by_width = min(max_slots_by_width, max_slots)
    
    # Generate all slots at once with complete positioning
    slots = [
        {
            'x_start': crew_column_start_x + first_center_offset + (i * center_spacing) - half_hero_width,
            'x_end': crew_column_start_x + first_center_offset + (i * center_spacing) + half_hero_width,
            'x_center': crew_column_start_x + first_center_offset + (i * center_spacing),
            'y_start': y_start,
            'y_end': y_end,
            'y_center': y_center,
            'width': hero_icon_width,
            'height': hero_icon_height
        }
        for i in range(max_slots_by_width)
    ]
    
    return slots


def calculate_crew_slots(crew_column_start_x, crew_column_end_x, row_start_y, hero_icon_width=56, center_spacing=80, top_margin=5):
    """
    Calculate crew hero slot positions (max 10 slots).
    
    Convenience function that calls calculate_hero_slots with max_slots=10.
    """
    return calculate_hero_slots(crew_column_start_x, crew_column_end_x, row_start_y, 
                               hero_icon_width, center_spacing, top_margin, max_slots=11)


def calculate_bench_slots(bench_column_start_x, bench_column_end_x, row_start_y, hero_icon_width=56, center_spacing=80, top_margin=5):
    """
    Calculate bench hero slot positions (max 8 slots).
    
    Convenience function that calls calculate_hero_slots with max_slots=8.
    """
    return calculate_hero_slots(bench_column_start_x, bench_column_end_x, row_start_y, 
                               hero_icon_width, center_spacing, top_margin, max_slots=8)


def get_row_boundaries(header_end=93, row_height=80, num_rows=8):
    # Returns row start positions: [93, 173, 253, 333, 413, 493, 573, 653, 733]
    return [header_end + (i * row_height) for i in range(num_rows)]  # 8 rows + end boundary


if __name__ == "__main__":
    # Test the function with sample data
    print("Testing calculate_hero_slots function")
    print("=" * 50)
    
    # Test case 1: Normal crew column
    crew_start = 400
    crew_end = 800
    row_start = 93  # First row start from get_row_boundaries
    
    print(f"\nTest 1: Crew column from {crew_start} to {crew_end}, row starts at {row_start}")
    slots = calculate_hero_slots(crew_start, crew_end, row_start)
    print(f"Number of slots: {len(slots)}")
    for i, slot in enumerate(slots):
        print(f"  Slot {i+1}: x={slot['x_start']}-{slot['x_end']} (center={slot['x_center']}), "
              f"y={slot['y_start']}-{slot['y_end']} (center={slot['y_center']}), "
              f"size={slot['width']}x{slot['height']}")
    