FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /code

# Copia arquivos de dependências
COPY requirements.txt .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Expõe porta 8501 (porta padrão do Streamlit)
EXPOSE 8501

# Comando para executar a aplicação
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.fileWatcherType=none", "--browser.gatherUsageStats=false"]