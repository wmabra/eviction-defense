import os, re

SEO = "/opt/eviction-defense/seo"
html_path = os.path.join(SEO, "south-carolina/spartanburg-county/index.html")
html = open(html_path).read()

existing = re.findall(r'/assets/locations/([^"]+)', html)
print("Existing images in HTML:")
for e in existing:
    print(f"  {e}")

asset_dir = os.path.join(SEO, "assets/locations/south_carolina/spartanburg")
print(f"\nFiles on disk in {asset_dir}:")
if os.path.exists(asset_dir):
    for f in os.listdir(asset_dir):
        fpath = os.path.join(asset_dir, f)
        if os.path.isfile(fpath):
            print(f"  {f} ({os.path.getsize(fpath)} bytes)")
else:
    print("  DIR DOES NOT EXIST")
