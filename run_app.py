import subprocess

p = subprocess.Popen(
    ["dist/WoW Advisor.app/Contents/MacOS/wow-advisor"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
try:
    stdout, stderr = p.communicate(timeout=5)
except subprocess.TimeoutExpired:
    p.kill()
    stdout, stderr = p.communicate()
    print("Process killed after 5 seconds")

print("STDOUT:")
print(stdout)
print("STDERR:")
print(stderr)
