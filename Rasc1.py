# Rasc1.py
import os
arquivo = r'C:\teste\foto.png'

print(os.path.exists(arquivo))   # existe?
print(os.path.isfile(arquivo))   # é arquivo?
print(os.path.getsize(arquivo))  # tamanho
