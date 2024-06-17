import streamlit as st
import pandas as pd
import json
import plotly.express as px
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
from datetime import datetime
import re

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Function to connect to the database
def connect_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Function to get the list of repository names
def get_repo_names():
    conn = connect_db()
    with conn.cursor() as cursor:
        cursor.execute("SELECT DISTINCT repo_name FROM commits")
        repo_names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return repo_names

# Function to extract groups from repository names
def extract_groups(repo_names):
    groups = set()
    for name in repo_names:
        match = re.search(r'T\d{2}', name)
        if match:
            groups.add(match.group())
    return sorted(groups)

# Function to get repository names by group
def get_repo_names_by_group(group, repo_names):
    return [name for name in repo_names if group in name]

# Function to get all commits from the database by repository
def get_all_commits(repo_name):
    conn = connect_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM commits WHERE repo_name = %s", (repo_name,))
        commit_data = cursor.fetchall()
    conn.close()
    return commit_data

# Function to get all pull requests from the database by repository
def get_all_pull_requests(repo_name):
    conn = connect_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM pull_requests WHERE repo_name = %s", (repo_name,))
        pull_data = cursor.fetchall()
    conn.close()
    return pull_data

# Function to serialize dates to string when creating JSON
def serialize_dates(data):
    for entry in data:
        for key, value in entry.items():
            if isinstance(value, datetime):
                entry[key] = value.isoformat()
    return data

# Streamlit interface
st.title("GitHub Commits and PRs Extractor")

# Get repository names and groups
repo_names = get_repo_names()
groups = extract_groups(repo_names)

# Dropdown to select the group
group = st.selectbox("Select Group:", groups)

if group:
    # Filter repository names by the selected group
    filtered_repo_names = get_repo_names_by_group(group, repo_names)
    repo_name = st.selectbox("Select Repository:", filtered_repo_names)

    if st.button("Extract Data"):
        if repo_name:
            try:
                with st.spinner('Fetching commits and pull requests...'):
                    commits = get_all_commits(repo_name)
                    pull_requests = get_all_pull_requests(repo_name)

                if commits:
                    st.success(f"Found {len(commits)} commits.")
                    df_commits = pd.DataFrame(commits)
                    df_commits['date'] = pd.to_datetime(df_commits['date'])
                    st.dataframe(df_commits)

                    # Download JSON of commits
                    commits_serialized = serialize_dates(commits)
                    json_data_commits = json.dumps(commits_serialized, indent=4)
                    st.download_button(
                        label="Download Commits JSON",
                        data=json_data_commits,
                        file_name='commits.json',
                        mime='application/json'
                    )

                    # Analyze commit types
                    df_commits['type'] = df_commits['message'].apply(
                        lambda x: 'docs' if 'docs' in x else (
                            'feat' if 'feat' in x else (
                                'fix' if 'fix' in x else (
                                    'merge' if 'Merge' in x else (
                                        'tests' if 'tests' in x else 'other'
                                    )
                                )
                            )
                        )
                    )
                    type_counts = df_commits.groupby(['author', 'type']).size().unstack(fill_value=0)

                    # Add 'tests' column if it doesn't exist
                    if 'tests' not in type_counts.columns:
                        type_counts['tests'] = 0

                    # Commit type plots
                    fig_docs = px.bar(type_counts, x=type_counts.index, y='docs', title="Number of Docs by Author", labels={'x':'Author', 'y':'Number of Docs'})
                    st.plotly_chart(fig_docs)

                    fig_feats = px.bar(type_counts, x=type_counts.index, y='feat', title="Number of Feats by Author", labels={'x':'Author', 'y':'Number of Feats'})
                    st.plotly_chart(fig_feats)

                    fig_fix = px.bar(type_counts, x=type_counts.index, y='fix', title="Number of Fixes by Author", labels={'x':'Author', 'y':'Number of Fixes'})
                    st.plotly_chart(fig_fix)

                    fig_merge = px.bar(type_counts, x=type_counts.index, y='merge', title="Number of Merges by Author", labels={'x':'Author', 'y':'Number of Merges'})
                    st.plotly_chart(fig_merge)

                    fig_tests = px.bar(type_counts, x=type_counts.index, y='tests', title="Number of Tests by Author", labels={'x':'Author', 'y':'Number of Tests'})
                    st.plotly_chart(fig_tests)

                    fig_others = px.bar(type_counts, x=type_counts.index, y=['docs', 'feat', 'fix', 'merge', 'tests', 'other'], title="Number of Other Commit Types by Author")
                    st.plotly_chart(fig_others)

                else:
                    st.warning("No commits found.")

                if pull_requests:
                    st.success(f"Found {len(pull_requests)} pull requests.")
                    df_pulls = pd.DataFrame(pull_requests)
                    df_pulls['created_at'] = pd.to_datetime(df_pulls['created_at'])
                    st.dataframe(df_pulls)

                    # Download JSON of pull requests
                    pull_requests_serialized = serialize_dates(pull_requests)
                    json_data_pulls = json.dumps(pull_requests_serialized, indent=4)
                    st.download_button(
                        label="Download Pull Requests JSON",
                        data=json_data_pulls,
                        file_name='pull_requests.json',
                        mime='application/json'
                    )

                    # Analyze pull requests by author
                    author_counts = df_pulls['author'].value_counts()
                    fig_pr_author = px.bar(author_counts, x=author_counts.index, y=author_counts.values, title="Number of Pull Requests by Author")
                    st.plotly_chart(fig_pr_author)

                    # Analyze pull requests by state
                    state_counts = df_pulls['state'].value_counts()
                    fig_pr_state = px.pie(names=state_counts.index, values=state_counts.values, title="Pull Requests by State")
                    st.plotly_chart(fig_pr_state)

                    # Analyze commits per pull request
                    df_pulls['num_commits'] = df_pulls['commits'].apply(len)
                    fig_pr_commits = px.histogram(df_pulls, x='num_commits', nbins=10, title="Number of Commits per Pull Request")
                    st.plotly_chart(fig_pr_commits)

                else:
                    st.warning("No pull requests found.")

            except Exception as e:
                st.error(f"Error fetching commits and pull requests: {e}")
        else:
            st.warning("Please select a repository.")
else:
    st.warning("Please select a group.")
