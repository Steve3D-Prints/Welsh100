import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import base64

# --- CONFIGURATION ---
DATA_FILE = "welsh_100.csv"
DATA_DIR = "/data" if os.path.exists("/data") else "."
PROGRESS_FILE = os.path.join(DATA_DIR, "my_progress.csv")
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")

st.set_page_config(page_title="Welsh 100 Tracker", layout="wide", initial_sidebar_state="expanded")
os.makedirs(PHOTOS_DIR, exist_ok=True)

# --- SESSION STATE MAGIC (Fixes Zombie Checkboxes) ---
if 'reset_id' not in st.session_state:
    st.session_state.reset_id = 0

# --- CSS STYLING ---
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%); }
    .center-header { display: flex; justify-content: center; align-items: center; gap: 15px; margin-bottom: 20px; }
    .stat-box { padding: 10px 20px; background: rgba(255, 255, 255, 0.05); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.08); text-align: center; min-width: 100px; }
    .stat-box small { font-size: 0.7rem; text-transform: uppercase; opacity: 0.6; display: block; }
    .stat-box strong { font-size: 1.3rem; font-weight: 700; display: block; margin-top: 4px; }
    .title-center h1 { background: linear-gradient(135deg, #C8102E 0%, #00AB66 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 2rem; margin: 0; }
    .stProgress > div > div > div { background: linear-gradient(90deg, #C8102E 0%, #00AB66 50%, #FFD700 100%); }
</style>
""", unsafe_allow_html=True)

# --- LOAD DATA ---
if not os.path.exists(DATA_FILE):
    st.error(f"⚠️ Missing {DATA_FILE}")
    st.stop()

df = pd.read_csv(DATA_FILE)
df['Height_Display'] = df['Height']
df['Height'] = df['Height'].astype(str).str.replace('m', '').str.replace(',', '').str.strip()
df['Height'] = pd.to_numeric(df['Height'], errors='coerce').fillna(0).astype(int)
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
df = df.sort_values(by='Height', ascending=False)

# Load Progress
if os.path.exists(PROGRESS_FILE):
    progress_df = pd.read_csv(PROGRESS_FILE)
    progress_df = progress_df.drop_duplicates(subset=['Mountain'], keep='last')
    progress_df['Bagged'] = progress_df['Bagged'].fillna(False).astype(bool)
else:
    progress_df = pd.DataFrame({'Mountain': df['Mountain'], 'Bagged': False, 'Date': '', 'Photo': '', 'ActivityLink': ''})

full_data = pd.merge(df, progress_df, on='Mountain', how='left')
full_data['Bagged'] = full_data['Bagged'].fillna(False)
full_data['Date'] = full_data['Date'].fillna('')
full_data['Photo'] = full_data['Photo'].fillna('')
full_data['ActivityLink'] = full_data['ActivityLink'].fillna('')

# --- STATS ---
total = len(full_data)
bagged = full_data['Bagged'].sum()
remaining = total - bagged
percent = int((bagged / total) * 100) if total > 0 else 0
total_elevation = full_data[full_data['Bagged'] == True]['Height'].sum()

# --- HEADER ---
st.markdown(f"""
<div class='center-header'>
    <div class='stat-box'><small>Summited</small><strong>{bagged}/{total}</strong></div>
    <div class='stat-box'><small>Completion</small><strong>{percent}%</strong></div>
    <div class='title-center'><h1>Welsh 100</h1></div>
    <div class='stat-box'><small>Elev. Gained</small><strong>{total_elevation:,}m</strong></div>
    <div class='stat-box'><small>Remaining</small><strong>{remaining}</strong></div>
</div>
""", unsafe_allow_html=True)
st.progress(bagged / total if total > 0 else 0)

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Map", "✅ Log Book", "📊 Analysis", "⚙️ Data"])

with tab1:
    m = folium.Map(location=[full_data['Latitude'].mean(), full_data['Longitude'].mean()], zoom_start=8, tiles="OpenStreetMap")
    for _, row in full_data.iterrows():
        color = "green" if row['Bagged'] else "red"
        icon = "flag" if row['Bagged'] else "mountain"
        img_html = ""
        if row['Bagged'] and row['Photo'] and os.path.exists(row['Photo']):
            with open(row['Photo'], 'rb') as f: b64_img = base64.b64encode(f.read()).decode()
            img_html = f'<br><img src="data:image/jpeg;base64,{b64_img}" style="width:100%; border-radius:5px;">'
        popup_html = f"""<div style="font-family:sans-serif; width:200px;"><h4 style="margin-bottom:0; color:{'#00AB66' if row['Bagged'] else '#C8102E'}">{row['Mountain']}</h4><small>{row['Height']}m</small><br><b>{row['Region']}</b>{img_html}</div>"""
        folium.Marker(location=[row['Latitude'], row['Longitude']], popup=folium.Popup(popup_html, max_width=250), icon=folium.Icon(color=color, icon=icon, prefix="fa")).add_to(m)
    st_folium(m, width=None, height=600)

with tab2:
    col_search, col_filter = st.columns([2, 1])
    search_term = col_search.text_input("🔍 Search", "")
    filter_type = col_filter.selectbox("Filter", ["All", "To Do", "Completed"])

    view_df = full_data.copy()
    if search_term: view_df = view_df[view_df['Mountain'].str.contains(search_term, case=False)]
    if filter_type == "To Do": view_df = view_df[view_df['Bagged'] == False]
    elif filter_type == "Completed": view_df = view_df[view_df['Bagged'] == True]

    for idx, row in view_df.iterrows():
        with st.expander(f"{'✅' if row['Bagged'] else '⬜'} {row['Mountain']} - {row['Height']}m"):
            c1, c2 = st.columns([1, 2])
            with c1:
                # MAGIC FIX: We append 'reset_id' to the key. 
                # When reset_id changes, Streamlit thinks this is a totally new button and forgets the old click.
                unique_key = f"chk_{idx}_{row['Mountain']}_{st.session_state.reset_id}"
                
                is_bagged = st.checkbox("Summited", value=row['Bagged'], key=unique_key)
                
                if is_bagged != row['Bagged']:
                    if row['Mountain'] not in progress_df['Mountain'].values:
                         new_row = pd.DataFrame([{'Mountain': row['Mountain'], 'Bagged': is_bagged}])
                         progress_df = pd.concat([progress_df, new_row], ignore_index=True)
                    else:
                        progress_df.loc[progress_df['Mountain'] == row['Mountain'], 'Bagged'] = is_bagged
                    progress_df.to_csv(PROGRESS_FILE, index=False)
                    st.rerun()

                if row['Bagged']:
                    curr_date = None
                    try: 
                        if row['Date']: curr_date = datetime.strptime(row['Date'], "%Y-%m-%d")
                    except: pass
                    new_date = st.date_input("Date", value=curr_date, key=f"date_{unique_key}")
                    if str(new_date) != str(row['Date']) and new_date:
                        progress_df.loc[progress_df['Mountain'] == row['Mountain'], 'Date'] = str(new_date)
                        progress_df.to_csv(PROGRESS_FILE, index=False)

            with c2:
                if row['Bagged']:
                    if row['Photo'] and os.path.exists(row['Photo']):
                        st.image(row['Photo'], width=300)
                        if st.button("Delete Photo", key=f"del_{unique_key}"):
                            os.remove(row['Photo'])
                            progress_df.loc[progress_df['Mountain'] == row['Mountain'], 'Photo'] = ''
                            progress_df.to_csv(PROGRESS_FILE, index=False)
                            st.rerun()
                    else:
                        up_file = st.file_uploader("Upload", type=['jpg','png'], key=f"up_{unique_key}", label_visibility="collapsed")
                        if up_file:
                            fname = f"{row['Mountain'].replace(' ','_')}_{idx}.jpg"
                            fpath = os.path.join(PHOTOS_DIR, fname)
                            img = Image.open(up_file)
                            img.thumbnail((800,800))
                            img.save(fpath)
                            progress_df.loc[progress_df['Mountain'] == row['Mountain'], 'Photo'] = fpath
                            progress_df.to_csv(PROGRESS_FILE, index=False)
                            st.rerun()

with tab3:
    c_a, c_b = st.columns(2)
    with c_a:
        fig_pie = go.Figure(data=[go.Pie(labels=['Done', 'Left'], values=[bagged, remaining], hole=.4, marker_colors=['#00AB66', '#C8102E'])])
        fig_pie.update_layout(title="Overall Progress", paper_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig_pie, use_container_width=True)
    with c_b:
        if 'Region' in df.columns:
            reg_stats = full_data.groupby('Region')['Bagged'].agg(['sum', 'count']).reset_index()
            reg_stats.columns = ['Region', 'Completed', 'Total']
            fig_bar = px.bar(reg_stats, y='Region', x=['Completed', 'Total'], orientation='h', barmode='overlay', title="Region Progress")
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_bar, use_container_width=True)

with tab4:
    st.info(f"Data Source: {DATA_FILE}")
    csv = progress_df.to_csv(index=False)
    st.download_button("💾 Backup Progress", csv, "welsh100_backup.csv", "text/csv")
    st.divider()
    
    # --- UPDATED FACTORY RESET LOGIC ---
    if st.button("⚠️ Factory Reset"):
        # 1. Delete the file
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            
        # 2. Increment the reset ID to invalidate all old checkboxes
        st.session_state.reset_id += 1
        
        st.success("Reset complete. Refreshing...")
        st.rerun()
