# Como Rodar no Proxmox VE (Self-Hosted)

Você pode rodar esta aplicação no seu Proxmox de duas maneiras simples e leves:

---

## Opção 1: Container LXC (Debian ou Ubuntu) - Mais Leve (Recomendado)

1. **Crie um container LXC** leve (512 MB de RAM e 1 vCPU são suficientes):
   - Template: Debian 12 ou Ubuntu 22.04 / 24.04.

2. **Dentro do LXC, instale o Python e as dependências**:
   ```bash
   apt update && apt install -y python3 python3-pip git
   pip install pypdf pdfplumber --break-system-packages
   ```

3. **Copie os arquivos do projeto** (`separar_notas.py` e `app.py`) para `/opt/separador_notas/`.

4. **Crie um serviço no systemd** para iniciar automaticamente no boot:
   ```bash
   cat << 'EOF' > /etc/systemd/system/separador.service
   [Unit]
   Description=Separador de Notas e Boletos Web
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/separador_notas
   ExecStart=/usr/bin/python3 /opt/separador_notas/app.py --porta 5000 --host 0.0.0.0
   Restart=always

   [Install]
   WantedBy=multi-user.target
   EOF

   systemctl daemon-reload
   systemctl enable --now separador.service
   ```

5. **Pronto!** Acesse pelo navegador de qualquer máquina da sua rede:
   `http://<IP_DO_LXC>:5000`

---

## Opção 2: Docker / Docker Compose

Se já usa Docker ou Portainer no Proxmox:

### `Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pypdf pdfplumber
COPY separar_notas.py app.py ./
EXPOSE 5000
CMD ["python", "app.py", "--porta", "5000", "--host", "0.0.0.0"]
```

### Iniciar:
```bash
docker build -t separador-notas .
docker run -d --name separador-notas -p 5000:5000 --restart always separador-notas
```
