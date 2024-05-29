import streamlit as st
from github import Github
import pandas as pd
import json
import plotly.express as px
from datetime import datetime
import database.mongodb

# Função para obter todos os commits
def get_all_commits(repo_name, token):
    g = Github(token)
    repo = g.get_repo(repo_name)
    commits = repo.get_commits()

    commit_data = []
    for commit in commits:
        commit_info = {
            "sha": commit.sha,
            "message": commit.commit.message,
            "author": commit.commit.author.name,
            "date": commit.commit.author.date.isoformat(),
            "url": commit.html_url
        }
        commit_data.append(commit_info)
    
    return commit_data

# Função para obter todos os pull requests
def get_all_pull_requests(repo_name, token):
    g = Github(token)
    repo = g.get_repo(repo_name)
    pulls = repo.get_pulls(state='all', sort='created', direction='desc')

    pull_data = []
    for pull in pulls:
        pull_info = {
            "number": pull.number,
            "title": pull.title,
            "author": pull.user.login,
            "created_at": pull.created_at.isoformat(),
            "state": pull.state,
            "comments": pull.comments,
            "review_comments": pull.review_comments,
            "commits": [c.sha for c in pull.get_commits()],
            "url": pull.html_url
        }
        pull_data.append(pull_info)
    
    return pull_data

# Interface do Streamlit
st.title("GitHub Commit and PR Extractor")

# Entradas do usuário
repo_name = st.text_input("Nome do Repositório (ex: usuario/repo):")
token = st.text_input("Token do GitHub:", type="password")

if st.button("Extrair Dados"):
    if repo_name and token:
        try:
            with st.spinner('Buscando commits e pull requests...'):
                commits = get_all_commits(repo_name, token)
                pull_requests = get_all_pull_requests(repo_name, token)
            
            if commits:
                st.success(f"Encontrado {len(commits)} commits.")
                df_commits = pd.DataFrame(commits)
                df_commits['date'] = pd.to_datetime(df_commits['date'])
                st.dataframe(df_commits)

                try:
                    database.mongodb.ping_database()

                    commits = {repo_name: commits}

                    database.mongodb.insert_document_into('commits', commits)

                except Exception as e:
                    st.error(f"Erro ao conectar ao banco de dados: {e}")
                
                # Download do JSON de commits
                json_data_commits = json.dumps(commits, indent=4)
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

                try:
                    database.mongodb.ping_database()

                    pull_requests = {repo_name: pull_requests}
                    
                    database.mongodb.insert_document_into('pull-requests', pull_requests)
                        
                except Exception as e:
                    st.error(f"Erro ao conectar ao banco de dados: {e}")
                
                # Download do JSON de pull requests
                json_data_pulls = json.dumps(pull_requests, indent=4)
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
