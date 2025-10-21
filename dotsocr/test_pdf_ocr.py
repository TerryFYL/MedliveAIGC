import requests
import time

url = "http://dots-ocr.mlproject.cn/extract"
pdf_path = './pdf_path/105005-1.pdf'
pdf_name = '105005-1.pdf'
payload = {'image_extract': 'true', 'dpi': '200'}
files=[
  ('file',(pdf_name,open(pdf_path,'rb'),'application/pdf'))
]
headers = {}

time1 = time.time()
response = requests.request("POST", url, headers=headers, data=payload, files=files)
print(f"Response time: {time.time()-time1} seconds")
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")