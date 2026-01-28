
import os
import subprocess

def run_git_commands():
    commands = [
        ['git', 'init'],
        ['git', 'add', '.'],
        ['git', 'commit', '-m', 'Update Dashboard Logic: OEE Calculation and Active Machine Filtering'],
        ['git', 'branch', '-M', 'main']
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Success: {' '.join(cmd)}")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error running {' '.join(cmd)}:")
            print(e.stderr)
            # If commit fails because no changes or identities, that's fine to know
            if "identity" in e.stderr:
                print("Configuring git identity...")
                subprocess.run(['git', 'config', 'user.email', 'antigravity@example.com'], check=True)
                subprocess.run(['git', 'config', 'user.name', 'Antigravity AI'], check=True)
                # Retry commit
                subprocess.run(['git', 'commit', '-m', 'Update Dashboard Logic: OEE Calculation and Active Machine Filtering'], check=True)

if __name__ == "__main__":
    run_git_commands()
