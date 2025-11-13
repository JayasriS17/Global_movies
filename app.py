# app.py
import streamlit as st
import pandas as pd
import numpy as np
import os
from prepare_data import OUTPUT_CSV, main as prepare_main

st.set_page_config(page_title="Movie Rating Explorer", layout="wide")
st.title("🎬 Movie Rating Explorer")

# Ensure data present (if not, run prepare_data which may download from Kaggle or create a sample)
if not os.path.exists(OUTPUT_CSV):
    with st.spinner("Preparing dataset (this may download from Kaggle if credentials are available)..."):
        prepare_main()

# Load data
@st.cache_data(show_spinner=False)
def load_data(path=OUTPUT_CSV):
    df = pd.read_csv(path, parse_dates=['release_date'], low_memory=False)
    # Ensure helper columns exist
    if 'title_lower' not in df.columns:
        df['title_lower'] = df['title'].str.lower()
    if 'release_year' not in df.columns:
        if 'release_date' in df.columns:
            df['release_year'] = pd.to_datetime(df['release_date'], errors='coerce').dt.year
        else:
            df['release_year'] = np.nan
    return df

df = load_data()

# Sidebar controls
st.sidebar.header("Search & Filters")
query = st.sidebar.text_input("Search movie title (partial allowed)")
languages_opt = sorted(df['original_language'].dropna().unique())
languages = st.sidebar.multiselect("Filter by original language", options=languages_opt, default=[])
min_votes = st.sidebar.number_input("Minimum vote count", min_value=0, value=50, step=50)
rating_threshold = st.sidebar.slider("Good threshold (vote_average)", 0.0, 10.0, 7.0, 0.1)
year_range = st.sidebar.slider("Release year range", int(df['release_year'].dropna().min()) if not df['release_year'].dropna().empty else 1950,
                               int(df['release_year'].dropna().max()) if not df['release_year'].dropna().empty else 2023,
                               (1980, 2023))

# Apply filters
filtered = df.copy()
if languages:
    filtered = filtered[filtered['original_language'].isin(languages)]
filtered = filtered[filtered['vote_count'] >= int(min_votes)]
filtered = filtered[(filtered['release_year'] >= year_range[0]) & (filtered['release_year'] <= year_range[1])]
if query:
    q = query.strip().lower()
    filtered = filtered[filtered['title_lower'].str.contains(q, na=False)]

st.sidebar.write(f"Matching titles: {len(filtered):,}")

# Layout
col1, col2 = st.columns([2,1])

with col1:
    st.subheader("Search results")
    display_cols = ['title','release_year','original_language','vote_average','vote_count']
    st.dataframe(filtered[display_cols].sort_values(['vote_average','vote_count'], ascending=[False,False]).head(500), use_container_width=True)

    # Optionally allow CSV download of filtered results
    csv_bytes = filtered[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button("Download filtered results (CSV)", data=csv_bytes, file_name="filtered_movies.csv", mime="text/csv")

with col2:
    st.subheader("Select a movie")
    movie_title = st.selectbox("Pick exact movie title", options=[''] + sorted(df['title'].dropna().unique()))
    if movie_title:
        movie = df[df['title'] == movie_title].iloc[0]
        st.markdown(f"### {movie['title']} ({int(movie['release_year']) if not pd.isna(movie['release_year']) else 'N/A'})")
        st.write(f"**Original language:** {movie.get('original_language','N/A')}")
        st.write(f"**Release date:** {movie.get('release_date','N/A')}")
        st.write(f"**Rating (avg):** {movie.get('vote_average','N/A')}  —  **Votes:** {movie.get('vote_count','N/A')}")

        good = (not pd.isna(movie.get('vote_average'))) and (movie['vote_average'] >= rating_threshold) and (movie['vote_count'] >= min_votes)
        verdict = "✅ Good to watch" if good else "⚠️ Maybe skip (low rating or few votes)"
        st.markdown(f"### Verdict: {verdict}")

        st.markdown("#### Similar movies (same language & year range)")
        lang = movie.get('original_language')
        sims = df[(df['original_language'] == lang) & (df['title'] != movie['title'])]
        sims = sims[(sims['vote_count'] >= min_votes) & (sims['release_year'] >= year_range[0]) & (sims['release_year'] <= year_range[1])]
        sims = sims.sort_values(['vote_average','vote_count'], ascending=[False, False]).head(10)
        if sims.empty:
            st.write("No similar movies found for current filters.")
        else:
            st.table(sims[['title','release_year','vote_average','vote_count']].reset_index(drop=True))

# Footer notes
st.markdown("---")
st.markdown("**Notes:**\n- Decision rule = rating >= threshold AND votes >= min votes.\n- You can change thresholds in the sidebar.\n- To use the full TMDb dataset, add your Kaggle credentials as environment variables or Streamlit secrets (KAGGLE_USERNAME, KAGGLE_KEY).")
