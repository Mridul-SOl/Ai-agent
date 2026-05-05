import os
import re

regex = re.compile(r'(\b[\w\[\]\s,]+)\s*\|\s*None\b')

for root, dirs, files in os.walk('.'):
    if 'venv' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            
            if '| None' in content or '|None' in content:
                new_content = regex.sub(r'Optional[\1]', content)
                
                # Make sure typing is imported
                if 'Optional' in new_content and 'from typing import Optional, ' not in new_content:
                    new_content = 'from typing import Optional\n' + new_content
                elif 'Optional' in new_content and 'from typing import ' in new_content and 'Optional' not in new_content.split('from typing import')[1].split('\n')[0]:
                    new_content = new_content.replace('from typing import ', 'from typing import Optional, ', 1)
                
                with open(path, 'w') as f:
                    f.write(new_content)
                print(f"Fixed {path}")
