#!/usr/bin/env python3
"""Publish a Cactus Commerce carousel to Instagram.

Usage:
  python scripts/instagram.py check
      Confirms the token works and prints the account username. Posts nothing.
  python scripts/instagram.py publish posts/2026-11-02
      Publishes the carousel in that folder (slide-01.jpg ... + caption.txt).

Environment:
  IG_ACCESS_TOKEN  (secret)  Instagram / Meta access token
  IG_USER_ID       (secret)  Instagram professional account ID
  IMAGE_BASE_URL             Public URL prefix where the post folder's JPEGs are served
"""
import json, os, sys, time, glob, urllib.parse, urllib.request, urllib.error

API_VERSION = os.environ.get("IG_API_VERSION", "v23.0")
HOSTS = ["https://graph.instagram.com", "https://graph.facebook.com"]
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
USER_ID = os.environ.get("IG_USER_ID", "").strip()


def call(host, method, path, params):
    params = dict(params, access_token=TOKEN)
    url = f"{host}/{API_VERSION}/{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} failed ({e.code}): {body}") from None


def pick_host():
    """The token works on one of the two Graph hosts depending on how it was made."""
    errors = []
    for host in HOSTS:
        try:
            info = call(host, "GET", USER_ID, {"fields": "username"})
            return host, info.get("username", "?")
        except RuntimeError as e:
            errors.append(f"{host}: {e}")
    sys.exit("Could not reach the Instagram account with this token.\n" + "\n".join(errors))


def diagnose():
    """Print what the token can see, to find the right Instagram account ID. Posts nothing."""
    def show(label, host, path, params):
        try:
            print(f"{label}: {json.dumps(call(host, 'GET', path, params))}")
        except RuntimeError as e:
            print(f"{label}: not available ({str(e)[:160]})")
    print(f"Saved IG_USER_ID is {len(USER_ID)} characters long")
    for host in HOSTS:
        print(f"--- {host}")
        show("me", host, "me", {"fields": "id,name,username,user_id"})
        show("permissions", host, "me/permissions", {})
        show("pages with Instagram", host, "me/accounts",
             {"fields": "name,instagram_business_account{id,username}"})
        show("businesses", host, "me/businesses", {"fields": "id,name"})
        show("token info", host, "debug_token", {"input_token": TOKEN})


def wait_ready(host, container_id, label):
    for _ in range(30):
        st = call(host, "GET", container_id, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"{label} failed to process (status {st})")
        time.sleep(5)
    sys.exit(f"{label} did not finish processing in time")


def check_url(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as r:
        ctype = r.headers.get("Content-Type", "")
    if "image/jpeg" not in ctype:
        sys.exit(f"Image URL is not served as image/jpeg ({ctype}): {url}")


def publish(folder):
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    slides = sorted(glob.glob(os.path.join(folder, "slide-*.jpg")))
    if not 2 <= len(slides) <= 10:
        sys.exit(f"A carousel needs 2 to 10 JPEG slides, found {len(slides)} in {folder}")
    caption = open(os.path.join(folder, "caption.txt"), encoding="utf-8").read().strip()
    if len(caption) > 2200:
        sys.exit("Caption is longer than Instagram's 2,200 character limit")

    host, username = pick_host()
    print(f"Posting to @{username} via {host}")

    children = []
    for i, path in enumerate(slides, 1):
        url = f"{base}/{os.path.basename(path)}"
        check_url(url)
        res = call(host, "POST", f"{USER_ID}/media", {"image_url": url, "is_carousel_item": "true"})
        children.append(res["id"])
        print(f"  slide {i} uploaded")
    for i, cid in enumerate(children, 1):
        wait_ready(host, cid, f"Slide {i}")

    parent = call(host, "POST", f"{USER_ID}/media",
                  {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})["id"]
    wait_ready(host, parent, "Carousel")
    post = call(host, "POST", f"{USER_ID}/media_publish", {"creation_id": parent})
    link = call(host, "GET", post["id"], {"fields": "permalink"}).get("permalink", "")
    print(f"Published! {link}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        open(summary, "a").write(f"### Posted to Instagram\n{link}\n")


if __name__ == "__main__":
    if not TOKEN or not USER_ID:
        sys.exit("IG_ACCESS_TOKEN and IG_USER_ID secrets must both be set")
    if len(sys.argv) >= 2 and sys.argv[1] == "check":
        diagnose()
        host, username = pick_host()
        print(f"Connection OK: token can reach @{username} via {host}")
    elif len(sys.argv) == 3 and sys.argv[1] == "publish":
        publish(sys.argv[2])
    else:
        sys.exit(__doc__)
