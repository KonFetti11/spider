import urllib.request
import json
import sys

base = "http://127.0.0.1:8765"


def get(path):
    r = urllib.request.urlopen(base + path)
    return json.loads(r.read())


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        base + path, data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    r = urllib.request.urlopen(req)
    return json.loads(r.read())


print("=== Spider POC End-to-End Test ===")
errors = []

# Test 1: Stats
try:
    stats = get("/tree/stats")
    total = stats["total_nodes"]
    rg = stats["root_reifegrad"]
    cp = stats["completion_percentage"]
    print(f"[1] /tree/stats: {total} Nodes, reifegrad={rg:.3f}, completion={cp}%")
    assert rg < 1.0
    print("    OK: root_reifegrad < 1.0")
except Exception as e:
    print(f"    FEHLER: {e}")
    errors.append(1)

# Test 2: Alle Nodes
try:
    nodes = get("/nodes")
    print(f"[2] /nodes: {len(nodes)} Nodes")
    assert len(nodes) > 0
    print("    OK")
except Exception as e:
    print(f"    FEHLER: {e}")
    errors.append(2)

# Test 3: Einzelner Node
try:
    n = get("/nodes/root-001")
    print(f"[3] /nodes/root-001: name={n['name']}, reifegrad={n['reifegrad']:.3f}")
    assert n["id"] == "root-001"
    print("    OK")
except Exception as e:
    print(f"    FEHLER: {e}")
    errors.append(3)

# Test 4: Accept erhoet reifegrad
try:
    old_rg = stats["root_reifegrad"]
    result = post("/nodes/deploy-pkg/accept", {
        "issuer": "test-agent",
        "reason": "pip-Package als Distributionsweg bestaetigt"
    })
    print(f"[4] /nodes/deploy-pkg/accept: status={result['status']}")
    assert result["status"] == "accepted"
    new_stats = get("/tree/stats")
    new_rg = new_stats["root_reifegrad"]
    print(f"    root_reifegrad: {old_rg:.3f} -> {new_rg:.3f}")
    assert new_rg >= old_rg
    print("    OK: reifegrad gestiegen oder gleichgeblieben")
except Exception as e:
    print(f"    FEHLER: {e}")
    errors.append(4)

# Test 5: Actions
try:
    actions = get("/actions")
    print(f"[5] /actions: {len(actions)} Actions")
    assert len(actions) > 0
    print("    OK")
except Exception as e:
    print(f"    FEHLER: {e}")
    errors.append(5)

# Test 6: Nested Tree
try:
    tree = get("/tree/nested")
    children_count = len(tree[0]["children"]) if tree else 0
    print(f"[6] /tree/nested: {len(tree)} Root-Nodes, {children_count} direkte Children")
    assert len(tree) > 0
    print("    OK")
except Exception as e:
    print(f"    FEHLER: {e}")
    errors.append(6)

# Test 7: Visualisierungsserver
try:
    r = urllib.request.urlopen("http://127.0.0.1:8766/")
    print(f"[7] Visualisierung (8766): HTTP {r.status}")
    assert r.status == 200
    print("    OK")
except Exception as e:
    print(f"    FEHLER: {e}")
    errors.append(7)

print()
if not errors:
    print("=== Alle 7 Tests bestanden! ===")
    final = get("/tree/stats")
    print(f"    Planungsfortschritt: {final['completion_percentage']}%")
    sys.exit(0)
else:
    print(f"=== {len(errors)} Test(s) fehlgeschlagen: {errors} ===")
    sys.exit(1)

