import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

base_url = "https://pdc.adm.ncu.edu.tw"
page_url = "https://pdc.adm.ncu.edu.tw/p/426-1019-7.php?Lang=zh-tw"  # 你的目錄頁

resp = requests.get(page_url)
soup = BeautifulSoup(resp.text, "html.parser")

pdfs = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if href.lower().endswith(".pdf"):
        full_url = urljoin(base_url, href)
        # 嘗試抓學系名稱
        dept = a.text.strip()
        pdfs.append({"dept": dept, "url": full_url})

os.makedirs("pdfs", exist_ok=True)
for item in pdfs:
    fname = f"pdfs/{item['dept']}.pdf"
    r = requests.get(item["url"])
    with open(fname, "wb") as f:
        f.write(r.content)