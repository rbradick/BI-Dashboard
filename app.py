
# Revised AI Business Intelligence Dashboard

import streamlit as st
import pandas as pd
import plotly.express as px
import openai
import os
from io import BytesIO

# ---------------------------
# CONFIGURATION
# ---------------------------
st.set_page_config(page_title="AI Business Intelligence Dashboard", layout="wide")
st.title("📊 AI Business Intelligence Dashboard")
st.write("Upload your CSV, Excel, or TXT file. This dashboard will analyze it and provide business insights automatically.")

# ---------------------------
# API KEY HANDLING
# ---------------------------
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except:
    openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    st.warning("⚠️ OpenAI API key not found. Please add it to `.streamlit/secrets.toml` or your environment.")

# ---------------------------
# FILE UPLOADER
# ---------------------------
@st.cache_data
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith(".txt"):
        return pd.read_csv(file, delimiter="\t")
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(file)
    else:
        return None

uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "txt"])

if uploaded_file:
    try:
        df = load_file(uploaded_file)
        st.success(f"✅ Uploaded: `{uploaded_file.name}`")

        # ---------------------------
        # DATA PREPROCESSING
        # ---------------------------
        sample = df.head(3).to_dict(orient="records")
        id_like_cols = [col for col in df.columns if 'id' in col.lower() or df[col].nunique() == len(df)]
        df.drop(columns=id_like_cols, inplace=True, errors='ignore')

        for col in df.columns:
            if 'date' in col.lower() or 'time' in col.lower():
                df[col] = pd.to_datetime(df[col], errors='coerce')

        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        time_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        cat_cols = df.select_dtypes(include='object').columns.tolist()

        # ---------------------------
        # USER SELECTION
        # ---------------------------
        st.sidebar.header("🔧 Controls")
        target_col = st.sidebar.selectbox("Select target numeric column", numeric_cols)
        time_col = st.sidebar.selectbox("Select time column", [None] + time_cols)
        cat_col = st.sidebar.selectbox("Select categorical column", [None] + cat_cols)

        # ---------------------------
        # METRICS
        # ---------------------------
        st.subheader("Key Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", f"{df[target_col].sum():,.2f}")
        with col2:
            st.metric("Average", f"{df[target_col].mean():,.2f}")
        with col3:
            st.metric("Max", f"{df[target_col].max():,.2f}")

        # ---------------------------
        # AI INSIGHTS
        # ---------------------------
        st.subheader("📌 AI-Generated Insights")

        if openai.api_key:
            with st.spinner("Generating insights with OpenAI..."):
                schema = "\n".join([f"{col} ({str(df[col].dtype)})" for col in df.columns])
                prompt = f"""
You are a senior business intelligence analyst. Analyze the uploaded dataset described below.

Schema:
{schema}

Target Metric: {target_col}
Sample Data: {sample}

Write a short business insights summary including trends, drivers, and opportunities.
"""
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a business intelligence assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
                st.markdown(response.choices[0].message.content)
        else:
            st.info("Add your OpenAI API key to unlock AI insights.")

        # ---------------------------
        # CHARTS
        # ---------------------------
        st.subheader("Visual Trends")

        if time_col:
            df_sorted = df.dropna(subset=[time_col]).sort_values(time_col)
            fig1 = px.line(df_sorted, x=time_col, y=target_col, title=f"{target_col} Over Time")
            st.plotly_chart(fig1, use_container_width=True)

        if cat_col:
            top_cats = df.groupby(cat_col)[target_col].sum().sort_values(ascending=False).head(10)
            fig2 = px.bar(x=top_cats.index, y=top_cats.values, labels={'x': cat_col, 'y': target_col},
                          title=f"Top {cat_col} by {target_col}")
            st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.histogram(df, x=target_col, title=f"Distribution of {target_col}")
        st.plotly_chart(fig3, use_container_width=True)

        # ---------------------------
        # DATA PREVIEW (MOVED TO BOTTOM)
        # ---------------------------
        st.subheader("Data Preview")
        st.dataframe(df.head())

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👈 Upload a file to begin.")
