"""Fix all template csrf_token references for AWS deployment."""
import os
import re

def fix_file(filepath):
    """Remove csrf_token references from a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Remove csrf_token hidden input lines
        content = re.sub(r'\s*<input type="hidden" name="csrf_token" value="{{ csrf_token\(\) }}">\s*\n?', '\n', content)
        
        # Remove X-CSRFToken header lines in JavaScript
        content = re.sub(r"'X-CSRFToken':\s*'{{ csrf_token\(\) }}',?\s*\n?", '', content)
        
        # Remove csrf_token variable assignments in JavaScript
        content = re.sub(r"csrfInput\.value = '{{ csrf_token\(\) }}';\s*\n?", '', content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    templates_dir = os.path.join(os.path.dirname(__file__), 'app', 'templates')
    fixed_count = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                if fix_file(filepath):
                    print(f"Fixed: {filepath}")
                    fixed_count += 1
    
    print(f"\nDone! Fixed {fixed_count} files.")

if __name__ == '__main__':
    main()
