# Rascunho.py
import requests,json,time
s=requests.Session()

url="http://127.0.0.1:11434/api/generate"

payload={
	"model":"phi3:mini",
	"prompt":"",
	"stream":False,
	"keep_alive":"1h",
	"options":{
		"num_ctx":512,
		"num_predict":128,
		"temperature":0.2,
		"num_batch":128,
		"num_gpu":1,
		"low_vram":True,
		"f16_kv":True,
		"use_mmap":True,
		"use_mlock":False,
		"num_thread":8
	}
}

def phi3(prompt):
	payload["prompt"]=prompt
	r=s.post(url,json=payload)

	return r.json()["response"]

while True:
	p=input(">>> ")
	if p=="sair":
		break

	t=time.time()
	resp=phi3(p)
	print(resp)
	print(f"\n{time.time()-t:.2f}s\n")
