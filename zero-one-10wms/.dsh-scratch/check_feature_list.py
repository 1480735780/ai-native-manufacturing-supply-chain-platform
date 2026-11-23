import json, collections
p = r"D:\Learning\code\AIWMSproject\zero-one-10wms\feature_list.json"
d = json.load(open(p, encoding="utf-8"))
feats = d["features"]
ids = [f["id"] for f in feats]
assert len(ids) == len(set(ids)), "duplicate ids"
st = d["rules"]["allowed_status"]; vl = d["rules"]["allowed_verification_level"]
for f in feats:
    assert f["status"] in st, f
    assert f["verification_level"] in vl, f
    if f["status"] == "passing": assert f["evidence"], f["id"]
    if f["status"] == "in_progress": assert f["verification_level"] == "not_started", f["id"]
ip = [f["id"] for f in feats if f["status"] == "in_progress"]
assert len(ip) == 1, ip
prio = [f["priority"] for f in feats]
assert len(prio) == len(set(prio)), "priority not unique"
assert sorted(prio) == list(range(1, len(feats)+1)), sorted(prio)
assert ids == sorted(ids), "features array not id-ascending"
print("features:", len(feats))
for f in sorted(feats, key=lambda x: x["priority"]):
    print("  P%-2d %-6s %-9s %s" % (f["priority"], f["id"], f["status"], f["title"][:40]))
print("in_progress:", ip)
print("next_candidate:", d["next_candidate"], "| agent_track_order:", d["rules"]["agent_track_order"])
print("tool_endpoints for F-009:", len([f for f in feats if f["id"]=="F-009"][0]["tool_endpoints"]))
print("ALL CHECKS PASS")
