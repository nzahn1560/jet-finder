#!/usr/bin/env python3

# Script to clean up the aircraft template by removing old Jinja template code

def cleanup_template():
    with open('templates/index.html', 'r') as f:
        content = f.read()
    
    # Find the start and end of the old template section
    start_marker = '<!-- Aircraft cards will be populated dynamically by JavaScript -->'
    end_marker = '            </div>'
    
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("Start marker not found")
        return
    
    # Find the aircraft-grid closing div
    after_start = content[start_idx:]
    grid_close_idx = after_start.find('</div>')
    if grid_close_idx == -1:
        print("Grid close not found")
        return
    
    # Find the next </div> after the grid close (should be the aircraft-grid closing)
    next_close_idx = after_start.find('</div>', grid_close_idx + 6)
    if next_close_idx == -1:
        print("Next close not found")
        return
    
    # Keep everything before start marker, the loading placeholder, and everything after the grid close
    before_start = content[:start_idx]
    after_grid_close = content[start_idx + next_close_idx + 6:]
    
    # The loading placeholder section
    loading_section = '''                <div class="loading-placeholder" style="text-align: center; padding: 40px; color: #6c757d;">
                    <i class="fas fa-plane fa-2x mb-3"></i>
                    <p>Loading aircraft listings...</p>
                </div>'''
    
    # Reconstruct the content
    new_content = before_start + loading_section + '\n            </div>' + after_grid_close
    
    # Write the cleaned content
    with open('templates/index.html', 'w') as f:
        f.write(new_content)
    
    print("Template cleaned up successfully!")

if __name__ == "__main__":
    cleanup_template()
