# Usar Python 3.13.3 slim
FROM python:3.13.3-slim

# Definir diretório de trabalho dentro do container
WORKDIR /app

# Copiar apenas os arquivos necessários (evita copiar venv, etc.)
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante da aplicação
COPY . .

# Expor a porta usada pelo app
EXPOSE 8000

# Rodar a aplicação usando uvicorn
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
