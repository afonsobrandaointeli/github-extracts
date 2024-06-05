import streamlit as st
import pandas as pd
import json
import plotly.express as px
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
from datetime import datetime  # Adicionado para resolver o erro

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Função para conectar ao banco de dados
def connect_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Função para obter a lista de repositórios
def get_repo_names():
    conn = connect_db()
    with conn.cursor() as cursor:
        cursor.execute("SELECT DISTINCT repo_name FROM commits")
        repo_names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return repo_names

# Função para obter todos os commits do banco de dados por repositório
def get_all_commits(repo_name):
    conn = connect_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM commits WHERE repo_name = %s", (repo_name,))
        commit_data = cursor.fetchall()
    conn.close()
    return commit_data

# Função para obter todos os pull requests do banco de dados por repositório
def get_all_pull_requests(repo_name):
    conn = connect_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM pull_requests WHERE repo_name = %s", (repo_name,))
        pull_data = cursor.fetchall()
    conn.close()
    return pull_data

# Função para converter datetime em string ao criar JSON
def serialize_dates(data):
    for entry in data:
        for key, value in entry.items():
            if isinstance(value, datetime):
                entry[key] = value.isoformat()
    return data

# Interface do Streamlit
st.title("GitHub Commit and PR Extractor")

# Dropdown para selecionar o repositório
repo_names = get_repo_names()
repo_name = st.selectbox("Selecione o Repositório:", repo_names)

if st.button("Extrair Dados"):
    if repo_name:
        try:
            with st.spinner('Buscando commits e pull requests...'):
                commits = get_all_commits(repo_name)
                pull_requests = get_all_pull_requests(repo_name)
            
            if commits:
                st.success(f"Encontrado {len(commits)} commits.")
                df_commits = pd.DataFrame(commits)
                df_commits['date'] = pd.to_datetime(df_commits['date'])
                st.dataframe(df_commits)
                
                # Download do JSON de commits
                commits_serialized = serialize_dates(commits)
                json_data_commits = json.dumps(commits_serialized, indent=4)
                st.download_button(
                    label="Baixar JSON de Commits",
                    data=json_data_commits,
                    file_name='commits.json',
                    mime='application/json'
                )

                # Análise de tipos de commits
                df_commits['type'] = df_commits['message'].apply(lambda x: 'docs' if 'docs' in x else ('feat' if 'feat' in x else ('fix' if 'fix' in x else 'other')))
                type_counts = df_commits.groupby(['author', 'type']).size().unstack(fill_value=0)
                
                # Gráfico de docs por autor
                fig_docs = px.bar(type_counts, x=type_counts.index, y='docs', title="Número de Docs por Autor", labels={'x':'Autor', 'y':'Número de Docs'})
                st.plotly_chart(fig_docs)
                
                # Gráfico de feats por autor
                fig_feats = px.bar(type_counts, x=type_counts.index, y='feat', title="Número de Feats por Autor", labels={'x':'Autor', 'y':'Número de Feats'})
                st.plotly_chart(fig_feats)
                
                # Gráfico de fix por autor
                fig_fix = px.bar(type_counts, x=type_counts.index, y='fix', title="Número de Fixes por Autor", labels={'x':'Autor', 'y':'Número de Fixes'})
                st.plotly_chart(fig_fix)
                
                # Gráfico de outros tipos por autor
                fig_others = px.bar(type_counts, x=type_counts.index, y=['docs', 'feat', 'fix', 'other'], title="Número de Outros Tipos de Commits por Autor")
                st.plotly_chart(fig_others)
            
            else:
                st.warning("Nenhum commit encontrado.")
                
            if pull_requests:
                st.success(f"Encontrado {len(pull_requests)} pull requests.")
                df_pulls = pd.DataFrame(pull_requests)
                df_pulls['created_at'] = pd.to_datetime(df_pulls['created_at'])
                st.dataframe(df_pulls)
                
                # Download do JSON de pull requests
                pull_requests_serialized = serialize_dates(pull_requests)
                json_data_pulls = json.dumps(pull_requests_serialized, indent=4)
                st.download_button(
                    label="Baixar JSON de Pull Requests",
                    data=json_data_pulls,
                    file_name='pull_requests.json',
                    mime='application/json'
                )

                # Análise de pull requests por autor
                author_counts = df_pulls['author'].value_counts()
                fig_pr_author = px.bar(author_counts, x=author_counts.index, y=author_counts.values, title="Número de Pull Requests por Autor")
                st.plotly_chart(fig_pr_author)

                # Análise de pull requests por estado
                state_counts = df_pulls['state'].value_counts()
                fig_pr_state = px.pie(names=state_counts.index, values=state_counts.values, title="Distribuição de Pull Requests por Estado")
                st.plotly_chart(fig_pr_state)

                # Análise de commits por pull request
                df_pulls['num_commits'] = df_pulls['commits'].apply(len)
                fig_pr_commits = px.histogram(df_pulls, x='num_commits', nbins=10, title="Distribuição do Número de Commits por Pull Request")
                st.plotly_chart(fig_pr_commits)
                
            else:
                st.warning("Nenhum pull request encontrado.")
                
        except Exception as e:
            st.error(f"Erro ao buscar commits e pull requests: {e}")
    else:
        st.warning("Por favor, preencha todos os campos.")
