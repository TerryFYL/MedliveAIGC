import requests
import os
import time

url = "http://dots-ocr.mlproject.cn/extract"

img_path = './img_path/113753-1_slide_9.png'
img_name = '113753-1_slide_9.png'
payload = {'image_extract': 'true'}
files=[
  ('file',(img_name,open(img_path,'rb'),'application/images'))
]
headers = {}
time1 = time.time()
response = requests.request("POST", url, headers=headers, data=payload, files=files)
print(f"Response time: {time.time()-time1} seconds")
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")