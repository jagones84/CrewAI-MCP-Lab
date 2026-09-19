import json, sys, urllib.request
d = json.loads(urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=10).read())
keys = list(d.keys())
print("Total nodes:", len(keys))
print("Has RMBG?     ", any("RMBG" in k for k in keys))
print("Has LayerMask?", any("LayerMask" in k for k in keys))
print("Has BiRefNet? ", any("BiRefNet" in k for k in keys))
print("Has Florence2?", any("Florence2" in k for k in keys))
print("Has SAM?      ", any(k.startswith("SAM") or "Segment" in k for k in keys))
print()
print("Inpaint classes:")
for k in keys:
    if "Inpaint" in k or "inpaint" in k:
        print("  -", k)
print()
print("Mask classes:")
for k in keys:
    if k.startswith("Mask") or k.endswith("Mask"):
        print("  -", k)
