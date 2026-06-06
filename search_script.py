import os
for root, dirs, files in os.walk('/app/viewflow'):
    for file in files:
        if file.endswith('.py'):
            try:
                with open(os.path.join(root, file), 'r') as f:
                    content = f.read()
                    if 'def perform' in content or 'class Activation' in content:
                        print(f"Found in {os.path.join(root, file)}")
                        if 'def perform' in content:
                            print("  -> Has 'def perform'")
            except:
                pass
