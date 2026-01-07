#!/usr/bin/env python3

# Script to clean up the aircraft template by removing old Jinja template code

def cleanup_template():
    with open('templates/index.html', 'r') as f:
        lines = f.readlines()
    
    # Find the start and end markers
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if 'loading-placeholder' in line and 'Loading aircraft listings' in lines[i+2]:
            start_line = i + 3  # After the loading placeholder div
        if '<!-- Bottom Pagination Controls -->' in line:
            end_line = i
            break
    
    if start_line is None or end_line is None:
        print("Could not find start or end markers")
        return
    
    # Keep everything before start_line and after end_line
    new_lines = lines[:start_line] + lines[end_line:]
    
    # Write the cleaned content
    with open('templates/index.html', 'w') as f:
        f.writelines(new_lines)
    
    print(f"Template cleaned up successfully! Removed lines {start_line} to {end_line}")

if __name__ == "__main__":
    cleanup_template()
