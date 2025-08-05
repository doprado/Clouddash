import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
from datetime import datetime, timedelta
import time
import pytz

# Configuração da página
st.set_page_config(
    page_title="Cloudflare AI Gateway Dashboard",
    page_icon="🔮",
    layout="wide"
)

def fetch_all_logs(base_url, headers):
    """Busca todos os logs de todas as páginas"""
    all_logs = []
    page = 1
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Primeira requisição para descobrir o total de páginas
        url = f"{base_url}?page={page}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success', False):
            st.error(f"Erro na API: {data}")
            return []
        
        result_info = data.get('result_info', {})
        total_count = result_info.get('total_count', 0)
        per_page = result_info.get('per_page', 20)
        total_pages = math.ceil(total_count / per_page)
        
        st.info(f"Total de registros: {total_count} | Total de páginas: {total_pages}")
        
        # Adiciona os logs da primeira página
        all_logs.extend(data.get('result', []))
        
        # Busca as páginas restantes
        for page in range(2, total_pages + 1):
            status_text.text(f"Buscando página {page} de {total_pages}...")
            progress_bar.progress(page / total_pages)
            
            url = f"{base_url}?page={page}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            page_data = response.json()
            if page_data.get('success', False):
                all_logs.extend(page_data.get('result', []))
            
            # Pequena pausa para não sobrecarregar a API
            time.sleep(0.1)
        
        progress_bar.progress(1.0)
        status_text.text(f"✅ Carregamento concluído! {len(all_logs)} registros obtidos.")
        
    except requests.exceptions.RequestException as e:
        st.error(f"Erro na requisição: {e}")
        return []
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
        return []
    
    return all_logs

def process_logs_data(logs):
    """Processa os logs e retorna um DataFrame"""
    processed_data = []
    
    for log in logs:
        email = log.get('metadata', {}).get('email', 'Não informado')
        model = log.get('model', 'Não informado')
        cost = log.get('cost', 0)
        tokens_in = log.get('tokens_in', 0)
        tokens_out = log.get('tokens_out', 0)
        duration = log.get('duration', 0)
        success = log.get('success', False)
        created_at = log.get('created_at', '')
        provider = log.get('provider', 'Não informado')
        
        # Converte created_at para datetime
        try:
            if created_at:
                # Remove o 'Z' e converte para datetime UTC
                created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                created_at_dt = None
        except:
            created_at_dt = None
        
        processed_data.append({
            'email': email,
            'model': model,
            'cost': cost,
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'total_tokens': tokens_in + tokens_out,
            'duration': duration,
            'success': success,
            'created_at': created_at,
            'created_at_dt': created_at_dt,
            'provider': provider
        })
    
    df = pd.DataFrame(processed_data)
    
    # Remove registros sem data válida
    df = df.dropna(subset=['created_at_dt'])
    
    return df

def filter_by_date_range(df, date_filter):
    """Filtra o DataFrame por período de tempo"""
    if df.empty or 'created_at_dt' not in df.columns:
        return df
    
    # Obtém a data/hora atual em UTC
    now_utc = datetime.now(pytz.UTC)
    
    # Define o período baseado no filtro
    if date_filter == "Últimas 24 horas":
        start_date = now_utc - timedelta(hours=24)
    elif date_filter == "Últimos 3 dias":
        start_date = now_utc - timedelta(days=3)
    elif date_filter == "Últimos 7 dias":
        start_date = now_utc - timedelta(days=7)
    elif date_filter == "Últimos 14 dias":
        start_date = now_utc - timedelta(days=14)
    elif date_filter == "Últimos 30 dias":
        start_date = now_utc - timedelta(days=30)
    else:  # "Todos os dados"
        return df
    
    # Filtra os dados
    filtered_df = df[df['created_at_dt'] >= start_date].copy()
    
    return filtered_df

def create_user_summary(df):
    """Cria resumo por usuário"""
    user_summary = df.groupby('email').agg({
        'cost': 'sum',
        'total_tokens': 'sum',
        'tokens_in': 'sum',
        'tokens_out': 'sum',
        'duration': 'mean',
        'model': 'count',  # Conta total de requests
        'success': lambda x: (x == True).sum()  # Conta requests bem-sucedidos
    }).round(6)
    
    user_summary.columns = ['Custo Total', 'Total Tokens', 'Tokens Input', 'Tokens Output', 'Duração Média (ms)', 'Total Requests', 'Requests Sucesso']
    user_summary['Taxa Sucesso (%)'] = (user_summary['Requests Sucesso'] / user_summary['Total Requests'] * 100).round(2)
    
    return user_summary.sort_values('Custo Total', ascending=False)

def create_model_usage_by_user(df):
    """Cria resumo de uso de modelos por usuário"""
    model_usage = df.groupby(['email', 'model']).agg({
        'cost': 'sum',
        'model': 'count',  # Conta requests
        'total_tokens': 'sum'
    }).round(6)
    
    model_usage.columns = ['Custo', 'Requests', 'Total Tokens']
    
    return model_usage.sort_values(['email', 'Custo'], ascending=[True, False])
    """Cria resumo por usuário"""
    user_summary = df.groupby('email').agg({
        'cost': 'sum',
        'total_tokens': 'sum',
        'tokens_in': 'sum',
        'tokens_out': 'sum',
        'duration': 'mean',
        'model': 'count',  # Conta total de requests
        'success': lambda x: (x == True).sum()  # Conta requests bem-sucedidos
    }).round(6)
    
    user_summary.columns = ['Custo Total', 'Total Tokens', 'Tokens Input', 'Tokens Output', 'Duração Média (ms)', 'Total Requests', 'Requests Sucesso']
    user_summary['Taxa Sucesso (%)'] = (user_summary['Requests Sucesso'] / user_summary['Total Requests'] * 100).round(2)
    
    return user_summary.sort_values('Custo Total', ascending=False)

def create_model_usage_by_user(df):
    """Cria resumo de uso de modelos por usuário"""
    model_usage = df.groupby(['email', 'model']).agg({
        'cost': 'sum',
        'model': 'count',  # Conta requests
        'total_tokens': 'sum'
    }).round(6)
    
    model_usage.columns = ['Custo', 'Requests', 'Total Tokens']
    
    return model_usage.sort_values(['email', 'Custo'], ascending=[True, False])

# Interface principal
st.title("🔮 Cloudflare AI Gateway Dashboard")
st.markdown("---")

# Configurações na sidebar
st.sidebar.title("⚙️ Configurações")

# Input para URL base (sem parâmetros)
default_url = ""
base_url = st.sidebar.text_input(
    "URL da API (sem parâmetros):",
    value=default_url,
    help="Insira a URL base da API do Cloudflare AI Gateway"
)

# Input para token de autorização
auth_token = st.sidebar.text_input(
    "Token de Autorização:",
    type="password",
    help="Token Bearer para autenticação"
)

# Input para email (opcional)
auth_email = st.sidebar.text_input(
    "Email da conta Cloudflare (opcional):",
    help="Email associado à conta Cloudflare"
)

if st.sidebar.button("🔄 Carregar Dados", type="primary"):
    if not base_url or not auth_token:
        st.error("Por favor, preencha a URL da API e o token de autorização.")
    else:
        # Prepara headers
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        if auth_email:
            headers["X-Auth-Email"] = auth_email
        
        with st.spinner("Carregando dados da API..."):
            logs = fetch_all_logs(base_url, headers)
        
        if logs:
            # Processa os dados
            df = process_logs_data(logs)
            
            # Salva no session state
            st.session_state['df'] = df
            st.session_state['last_update'] = datetime.now()
            
            st.success(f"✅ Dados carregados com sucesso! {len(logs)} registros processados.")

# Verifica se há dados carregados
if 'df' in st.session_state:
    df_original = st.session_state['df']
    last_update = st.session_state.get('last_update', 'Desconhecido')
    
    # Filtros de data
    st.markdown("## 🗓️ Filtros")
    
    col_filter1, col_filter2 = st.columns([2, 1])
    
    with col_filter1:
        # Filtro de período
        date_options = [
            "Todos os dados",
            "Últimas 24 horas", 
            "Últimos 3 dias",
            "Últimos 7 dias", 
            "Últimos 30 dias"
        ]
        
        selected_period = st.selectbox(
            "📅 Período:",
            options=date_options,
            index=0,
            help="Filtre os dados por período de tempo"
        )
    
    with col_filter2:
        # Mostra informações do período de dados
        if not df_original.empty and 'created_at_dt' in df_original.columns:
            min_date = df_original['created_at_dt'].min()
            max_date = df_original['created_at_dt'].max()
            st.info(f"📊 Dados de {min_date.strftime('%d/%m/%Y %H:%M')} até {max_date.strftime('%d/%m/%Y %H:%M')}")
    
    # Aplica o filtro de data
    df = filter_by_date_range(df_original, selected_period)
    
    # Mostra informações sobre o filtro aplicado
    if selected_period != "Todos os dados":
        filtered_count = len(df)
        total_count = len(df_original)
        st.success(f"🎯 Filtro aplicado: **{selected_period}** | Mostrando {filtered_count:,} de {total_count:,} registros")
    else:
        st.info(f"📊 Dados carregados: {len(df):,} registros | Última atualização: {last_update}")
    
    # Verifica se ainda há dados após o filtro
    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado para o período selecionado.")
        st.stop()
    
    st.markdown("---")
    
    # Métricas gerais
    st.markdown("## 📈 Métricas Gerais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total de Usuários",
            df['email'].nunique(),
            help="Número único de usuários"
        )
    
    with col2:
        st.metric(
            "Custo Total",
            f"${df['cost'].sum():.6f}",
            help="Soma de todos os custos"
        )
    
    with col3:
        st.metric(
            "Total de Requests",
            f"{len(df):,}",
            help="Número total de requisições"
        )
    
    with col4:
        success_rate = (df['success'].sum() / len(df) * 100)
        st.metric(
            "Taxa de Sucesso",
            f"{success_rate:.1f}%",
            help="Porcentagem de requisições bem-sucedidas"
        )
    
    # Resumo por usuário
    st.markdown("## 👥 Resumo por Usuário")
    
    user_summary = create_user_summary(df)
    st.dataframe(user_summary, use_container_width=True)
    
    # Gráficos
    st.markdown("## 📊 Visualizações")
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Custos por Usuário", "🤖 Modelos Mais Usados", "📈 Uso de Tokens", "⏱️ Performance"])
    
    with tab1:
        # Gráfico de custos por usuário
        fig_cost = px.bar(
            user_summary.head(10).reset_index(),
            x='email',
            y='Custo Total',
            title="Top 10 Usuários por Custo Total",
            labels={'email': 'Usuário', 'Custo Total': 'Custo ($)'}
        )
        fig_cost.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_cost, use_container_width=True)
    
    with tab2:
        # Gráfico de modelos mais usados
        model_usage = df.groupby('model').agg({
            'cost': 'sum',
            'model': 'count'
        }).round(6)
        model_usage.columns = ['Custo Total', 'Total Requests']
        model_usage = model_usage.sort_values('Total Requests', ascending=False)
        
        fig_models = px.pie(
            model_usage.head(10).reset_index(),
            values='Total Requests',
            names='model',
            title="Distribuição de Uso por Modelo (Top 10)"
        )
        st.plotly_chart(fig_models, use_container_width=True)
        
        # Tabela de modelos
        st.subheader("Detalhes por Modelo")
        st.dataframe(model_usage, use_container_width=True)
    
    with tab3:
        # Gráfico de tokens por usuário
        fig_tokens = px.bar(
            user_summary.head(10).reset_index(),
            x='email',
            y='Total Tokens',
            title="Top 10 Usuários por Total de Tokens",
            labels={'email': 'Usuário', 'Total Tokens': 'Tokens'}
        )
        fig_tokens.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_tokens, use_container_width=True)
    
    with tab4:
        # Gráfico de duração média por usuário
        fig_duration = px.bar(
            user_summary.head(10).reset_index(),
            x='email',
            y='Duração Média (ms)',
            title="Top 10 Usuários por Duração Média de Request",
            labels={'email': 'Usuário', 'Duração Média (ms)': 'Duração (ms)'}
        )
        fig_duration.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_duration, use_container_width=True)
    
    # Detalhes por usuário e modelo
    st.markdown("## 🔍 Detalhes por Usuário e Modelo")
    
    model_usage_detailed = create_model_usage_by_user(df)
    
    # Filtro por usuário
    selected_user = st.selectbox(
        "Selecione um usuário para ver detalhes:",
        options=['Todos'] + list(df['email'].unique()),
        index=0
    )
    
    if selected_user != 'Todos':
        filtered_data = model_usage_detailed.loc[selected_user]
        st.subheader(f"Uso de Modelos - {selected_user}")
        st.dataframe(filtered_data, use_container_width=True)
        
        # Gráfico para o usuário selecionado
        fig_user_models = px.pie(
            filtered_data.reset_index(),
            values='Requests',
            names='model',
            title=f"Distribuição de Modelos - {selected_user}"
        )
        st.plotly_chart(fig_user_models, use_container_width=True)
    else:
        st.dataframe(model_usage_detailed, use_container_width=True)

else:
    st.info("👆 Configure as credenciais na barra lateral e clique em 'Carregar Dados' para começar.")
    
    # Instruções
    st.markdown("""
    ## 📋 Como usar:
    
    1. **Configure a URL da API**: Insira a URL base da API do Cloudflare AI Gateway (sem parâmetros de página)
    2. **Adicione o Token**: Insira seu token de autorização Bearer
    3. **Email (opcional)**: Adicione o email associado à sua conta Cloudflare se necessário
    4. **Carregue os Dados**: Clique no botão "Carregar Dados"
    
    O dashboard irá:
    - ✅ Buscar automaticamente todas as páginas de dados
    - 📊 Apresentar métricas gerais
    - 👥 Mostrar resumo por usuário
    - 🤖 Exibir modelos mais utilizados
    - 💰 Calcular custos por usuário e modelo
    - 📈 Gerar visualizações interativas
    """)

# Footer
st.markdown("---")
st.markdown("Dashboard criado com ❤️ usando Streamlit")