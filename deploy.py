import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from requests_html import HTMLSession
from bs4 import BeautifulSoup
from pprint import pprint
import time
import pickle
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from st_aggrid import AgGrid
import random
import torch
import os
import joblib
import hashlib
import pprint
import google.generativeai as palm
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm
from sklearn.preprocessing import LabelEncoder
import sys
from streamlit_option_menu import option_menu
from pyvis.network import Network
import requests
from datetime import date
import plotly.express as px
import base64

LOGO_IMAGE = './palugada.png'
st.set_page_config(layout="wide")
#Disable Warning
st.set_option('deprecation.showPyplotGlobalUse', False)
st.markdown(
    f"""
    <div style="text-align: center;">
    <img class="logo-img" src="data:png;base64,{base64.b64encode(open(LOGO_IMAGE, 'rb').read()).decode()}">
    </div>
    """,
    unsafe_allow_html=True
)


# Load logistic regression model and label encoder
def load_models():
    logistic_model_path = './Model/logistic_regression_model/logistic_regression_model.pkl'
    label_encoder_path = './Model/label_encoder/label_encoder.pkl'
    logistic_model = joblib.load(logistic_model_path)
    label_encoder = joblib.load(label_encoder_path)
    return logistic_model, label_encoder

logistic_model, label_encoder = load_models()

# Load Model Log
model_log = pickle.load(open('./Model/modellog.pkl', 'rb'))

# Custom hashing function for anonymization
def hash_condition(cell_value):
    try:
        if (isinstance(cell_value, str) and 
            len(cell_value) == 16 and 
            11 <= int(cell_value[:2]) <= 95 and
            1 <= int(cell_value[2:4]) <= 79 and
            1 <= int(cell_value[4:6]) <= 55 and
            1 <= int(cell_value[6:8]) <= 71 and
            1 <= int(cell_value[8:10]) <= 12 and
            1900 <= int(cell_value[10:12]) <= 2024):
            return hashlib.md5(cell_value.encode()).hexdigest()
    except ValueError:
        pass  # Handle the case where int conversion fails
    return cell_value
    
#Function Berita
session = HTMLSession()
#Data Log
data_log = pd.read_csv('./dataset/data_log.csv')
# from pygooglenews import GoogleNews
def get_titletext(keyword,src,dest,country_id):
    topik = keyword #translate(keyword,dest,src)
    url = f'https://news.google.com/rss/search?q={topik}&hl={src}&gl={country_id}&ceid={country_id}%3Aid'
    r = session.get(url)
    newstitles = []
    links = []
    for title in r.html.find('title')[:100]:
      newstitles.append(title.text)
      time.sleep(0.1)
    for link in r.html.find('description')[:100]:
      links.append(link.text)
      time.sleep(0.1)
    texts = [i.split(" - ", 1)[0] for i in newstitles]
    sources = [i.split(" - ", 1)[1] for i in newstitles]
    links = [i.split(" ", 2)[1] for i in links]
    links = [w[6:-1] for w in links]
    df = pd.DataFrame(list(zip(texts,sources,links)),columns =['News_Title','Source','Link'])
    df['News_Title'] = df['News_Title']#.apply(translate,args=(src,dest))
    df['Country_ID'] = country_id
    df['Keyword'] = topik
    return df.iloc[1:, :]
#Function Hackernews
def link_to_soup(link):
    response = requests.get(link)
    if response.ok:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        return False
home_page_soup = link_to_soup('https://thehackernews.com/')
#Menu
menu = option_menu(None, ["Home","Anonymizer", "Phising Monitoring", "Log Based Monitoring", "News Monitoring", "Chatbot"], 
    icons=['house', 'incognito', "virus", 'router','newspaper','chat-text'], 
    menu_icon="cast", default_index=0, orientation="horizontal",
    styles={
        "container": {"padding": "0!important"},
        "icon": {"color": "white", "font-size": "15px"}, 
        "nav-link": {"font-size": "15   px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "blue"},
    })
if menu == "Anonymizer":
    st.title("Auto-Anonymizer")
    uploaded_file = st.file_uploader("Choose a file")

    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format. Please provide a CSV or Excel file.")

        if st.button('Anonymize Data'):
            melted_table = pd.melt(df, value_vars=df.columns, var_name='Column', value_name='Data')
            logistic_preds = logistic_model.predict(melted_table['Data'].astype(str).tolist())
            melted_table['Sensitive'] = label_encoder.inverse_transform(logistic_preds)
            melted_table.loc[melted_table['Sensitive'] == 1, 'Data'] = \
                melted_table.loc[melted_table['Sensitive'] == 1, 'Data'].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest())
            
            split_tables = np.array_split(melted_table, len(melted_table) // len(df))
            pivoted_tables = [split.pivot(columns='Column', values='Data').reset_index(drop=True) for split in split_tables]
            reverted_table = pivoted_tables[0]
            for table in pivoted_tables[1:]:
                reverted_table = pd.merge(reverted_table, table, left_index=True, right_index=True)
        
            st.dataframe(reverted_table)
            file_format = uploaded_file.name.split('.')[-1].lower()
            if file_format == 'csv':
                csv = reverted_table.to_csv(index=False)
                st.download_button(label="Download Anonymized Data as CSV", data=csv, file_name='anonymized_data.csv', mime='text/csv')
            elif file_format in ['xlsx', 'xls']:
                towrite = io.BytesIO()
                reverted_table.to_excel(towrite, index=False, engine='xlsxwriter')
                towrite.seek(0)
                st.download_button(label=f"Download Anonymized Data as {file_format.upper()}", data=towrite, file_name=f'anonymized_data.{file_format}', mime='application/vnd.ms-excel')
            else:
                st.error("Unsupported file format. Please provide a CSV or Excel file.")
            
if menu == 'Phising Monitoring':
    st.title('Phising Monitoring')
    #Data Phising (https://phishstats.info/#apidoc)
    url = "https://phishstats.info:2096/api/phishing?_sort=-date&_where=(countrycode,eq,ID)&&_size=100"
    # Send a GET request to the URL
    response = requests.get(url)
    #Create Dataframe Phising
    phising = pd.DataFrame(response.json())
    st.write('## Data Phising di Indonesia tanggal : ',date.today())
    st.dataframe(phising)
    #Extract ISP
    # Define a regular expression pattern to extract the desired parts
    pattern = r'(?:AS-AP|AS-ID)\s(.+?),\s'
    # Apply the regular expression to the DataFrame column
    phising['penyedia_isp'] = phising['isp'].str.extract(pattern)
    #Initiate Network
    g = Network(height="700px", width="700px", bgcolor="#718487", font_color="white",notebook=True)
    g.show_buttons(filter_=['physics'])

    url_number = 1
    url_counter = 0
    for url in phising.index:
        url_counter += 1

    #Cheking for data
    if url_counter <= 0:
        print("Not enough data to create network")
        exit(1)
    for index, entry in phising.iterrows():
        new_url = entry['url']
        new_url = '{}'.format(new_url)
        new_url_http_code = entry['http_code']
        new_url_http_server = entry['http_server']
        new_url_safebrowsing = entry['google_safebrowsing']
        new_url_technology = entry['technology']
        if new_url != "":
            g.add_node("URL-" + str(url_number), title = (new_url + "<br> HTTP code: " + str(new_url_http_code) + "<br> HTTP server: " + str(new_url_http_server) + "<br> Safebrowsing: " + str(new_url_safebrowsing) + "<br> Technologies:" + str(new_url_technology)), color = "#1ba1e2")

        new_title = entry['title']
        new_title = '{}'.format(new_title)
        if new_title != "":
            g.add_node(new_title, color = "#2eaf57")

        if new_url != "":
            if new_title != "":
                g.add_edge("URL-" + str(url_number), new_title)

        new_ip = entry['ip']
        new_ip = '{}'.format(new_ip)

        if new_ip != "":
            new_ip_times = entry['n_times_seen_ip']
            new_ip_vulns = entry['vulns']
            new_ip_ports = entry['ports']
            new_ip_tags = entry['tags']
            new_ip_os = entry['os']
            new_ip_abusech = entry['abuse_ch_malware']
            g.add_node(new_ip, title = ("N times seen IP: " + str(new_ip_times) + "<br> Vulnerabilities: " + str(new_ip_vulns) + "<br> Ports: " + str(new_ip_ports) + "<br> Tags: " + str(new_ip_tags) + "<br> OS: " + str(new_ip_os) + "<br> Abuse.ch (Malware): " + str(new_ip_abusech)), color = "#006699")

        if new_url != "":
            if new_ip != "":
                g.add_edge("URL-" + str(url_number), new_ip)

        new_host = entry['host']
        new_host = '{}'.format(new_host)
        if new_host != "":
            if new_host != new_ip:
                new_host_times = entry['n_times_seen_host']
                new_host_alexa = entry['alexa_rank_host']
                new_host_abusech = entry['abuse_ch_malware']
                g.add_node(new_host, title = ("N times seen Hostname: " + str(new_host_times) + "<br> Alexa rank: " + str(new_host_alexa) + "<br> Abuse.ch (Malware): " + str(new_host_abusech)), color = "#008080")

        if new_url != "":
            if new_host != "":
                g.add_edge("URL-" + str(url_number), new_host)

        new_domain = entry['domain']
        new_domain = '{}'.format(new_domain)
        if new_domain != "":
            if new_domain != "None":
                if new_host != new_domain:
                    new_domain_times = entry['n_times_seen_domain']
                    new_domain_days_ago = entry['domain_registered_n_days_ago']
                    new_domain_alexa = entry['alexa_rank_domain']
                    new_domain_virustotal = entry['virus_total']
                    new_domain_threat_crowd = entry['threat_crowd']
                    new_domain_threat_crowd_votes = entry['threat_crowd_votes']
                    g.add_node(new_domain, title = ("N times seen Domain: " + str(new_domain_times) + "<br> Domain registered N days ago: " + str(new_domain_days_ago) + "<br> Alexa rank: " + str(new_domain_alexa) + "<br> Virustotal: " + str(new_domain_virustotal) + "<br> ThreatCrowd: " + str(new_domain_threat_crowd) + "<br> ThreatCrowd votes: " + str(new_domain_threat_crowd_votes)), color = "#eed514")

        if new_domain != "":
            if new_host != "":
                if new_domain != "None":
                    if new_domain != new_host:
                        g.add_edge(new_host, new_domain)

        new_asn = entry['asn']
        new_asn = '{}'.format(new_asn)
        if new_asn != "":
            g.add_node(new_asn, color = "#db870e")

        if new_asn != "":
            if new_ip != "":
                g.add_edge(new_asn, new_ip)

        new_isp = entry['isp']
        new_isp = '{}'.format(new_isp)
        if new_isp != "":
            g.add_node(new_isp, color = "#7969a9")

        if new_isp != "":
            if new_asn != "":
                g.add_edge(new_asn, new_isp)

        new_countryname = entry['countryname']
        new_countryname = '{}'.format(new_countryname)
        if new_countryname != "":
            g.add_node(new_countryname, color = "#39af8e")

        if new_countryname != "":
            if new_isp != "":
                g.add_edge(new_countryname, new_isp)

        url_number += 1

    #Checking for size/value of nodes
    neighbor_map = g.get_adj_list()
    for node in g.nodes:
        node["value"] = len(neighbor_map[node["id"]])

    # st.write("URLs: " + str(url_counter))
    # st.write("Nodes: " + str(g.num_nodes()))
    # st.write("Edges: " + str(g.num_edges()))
    isp = phising['penyedia_isp'].value_counts()
    labels = isp.index
    values = isp.values

    # Use `hole` to create a donut-like pie chart
    st.write("#### ISP yang digunakan")
    fig = px.bar(isp, x=values, y=labels, orientation='h')
    st.plotly_chart(fig, use_container_width=True)

    col1,col2 = st.columns(2)
    with col1:
        g_safe_browsing = phising['google_safebrowsing'].value_counts()
        labels = g_safe_browsing.index
        values = g_safe_browsing.values

        # Use `hole` to create a donut-like pie chart
        st.write("#### Komponen HTTPS")
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        st.plotly_chart(fig, use_container_width=True)

        
    with col2:
        tld = phising['tld'].value_counts()
        labels = tld.index
        values = tld.values

        # Use `hole` to create a donut-like pie chart
        st.write("#### Ekstensi Domain")
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        st.plotly_chart(fig, use_container_width=True)
    net_yes = st.sidebar.checkbox('Tampilkan Network?')
    if net_yes:
        # Display the Pyvis network in Streamlit
        html_code = g.show('network.html')
        HtmlFile = open("network.html", 'r', encoding='utf-8')
        source_code = HtmlFile.read() 
        # Display the Pyvis network in Streamlit
        st.components.v1.html(source_code, height=590, width=700)
    wordcloud_desc =  st.sidebar.checkbox('Tampilkan Wordcloud Deskripsi Web Phising')
    if wordcloud_desc:
        # Assuming 'extracted_text' is the column name in your DataFrame
        texts = phising['title'].fillna('-').tolist()
        # Predefined rainbow colors
        rainbow_colors = ['#FF0000', '#FF7F00', '#FFFF00', '#00FF00', '#0000FF', '#4B0082', '#8B00FF']
        # Function to assign rainbow colors to sentences
        def rainbow_color_func(word=None, font_size=None, position=None, orientation=None, font_path=None, random_state=None):
            return np.random.choice(rainbow_colors)
        # Combine all texts into a single string
        # Define a separator for phrases (you can choose any unique string)
        separator = '||'
        # Combine all texts into a single string with phrases separated by the chosen separator
        combined_text = separator.join(texts)
        # Generate WordCloud with rainbow colors for each sentence
        wordcloud = WordCloud(width=1600, height=800, max_font_size=200, max_words=200, background_color="black",
                            color_func=rainbow_color_func).generate(combined_text)

        # Plot the WordCloud
        wc = plt.figure(figsize=(12, 10))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        st.pyplot(wc)
if menu == 'Log Based Monitoring':
    st.title('Log Based Monitoring')
    st.write(data_log.head())
    st.write("Menu Prediksi")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Source port</p>", unsafe_allow_html=True)
        source_port = st.selectbox("Pilih Source Port",data_log['id.orig_p'].unique())
        for item in data_log['id.orig_p'].unique():
            if item == source_port:
                st.write(' Source Port :', source_port)

        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Destination IP address</p>", unsafe_allow_html=True)
        dest_port = st.selectbox("Pilih Destination Port",data_log['id.resp_p'].unique())
        for item in data_log['id.resp_p'].unique():
            if item == dest_port:
                st.write(' Destination Port :', dest_port)

        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Network Protocol</p>", unsafe_allow_html=True)
        proto = st.selectbox("Pilih Network Protocol",data_log['proto'].unique())
        for item in data_log['proto'].unique():
            if item == proto:
                st.write(' Network Procotocol :', str(proto))
        
        
        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Service associated</p>", unsafe_allow_html=True)
        service = st.selectbox("Pilih Service",data_log['service'].unique())
        for item in data_log['service'].unique():
            if item == service:
                st.write(' Service associated with the connection :', str(service))
    with col2:
        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Duration of the connection</p>", unsafe_allow_html=True)
        duration = st.number_input('Duration of connection',key=1)
        st.write(duration)

        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Bytes sent from the source</p>", unsafe_allow_html=True)
        orig = st.number_input('Bytes sent from the source',key=2)
        st.write(orig)
        
        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Bytes sent from the destination</p>", unsafe_allow_html=True)
        resp = st.number_input('Bytes sent from the destination',key=3)
        st.write(resp)

        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>State of the connection</p>", unsafe_allow_html=True)
        statconn = st.selectbox("Pilih State Connection",data_log['conn_state'].unique())
        for item in data_log['conn_state'].unique():
            if item == service:
                st.write(' State of the connection :', str(statconn))
    with col3:
        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Number of packets(Source)</p>", unsafe_allow_html=True)
        orig_pkts = st.number_input('Number of packets sent',key=5,value=1)
        st.write(orig_pkts)

        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Number of IP bytes(Source)</p>", unsafe_allow_html=True)
        orig_ip_b = st.number_input('Number of IP bytes sent',key=6,value=40)
        st.write(orig_ip_b)

        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Number of packets(Dest)</p>", unsafe_allow_html=True)
        resp_pkts = st.number_input('Number of packets sent',key=7)
        st.write(resp_pkts)

        st.markdown("<p style='text-align: center; color: #FFCC29; font-family:arial'>Number of IP bytes(Dest)</p>", unsafe_allow_html=True)
        resp_ip_b = st.number_input('Number of IP bytes sent',key=8)
        st.write(resp_ip_b)
    #Create tabel predict
    index=[0]
    df_1_pred = pd.DataFrame({
                'id.orig_p' : source_port,
                'id.resp_p' : dest_port,
                'proto' : proto,
                'service':service,
                'duration': duration,
                'orig_bytes' : orig,
                'resp_bytes' : resp,
                'conn_state' : statconn,
                'orig_pkts' : orig_pkts,
                'orig_ip_bytes' : orig_ip_b,
                'resp_pkts' : resp_pkts,
                'resp_ip_bytes' : resp_ip_b
            },index=index)
    #Set semua nilai jadi 0
    df_kosong_1 = data_log[:1].drop(['proto','service','conn_state','label'],axis=1)
    for col in df_kosong_1.columns:
        df_kosong_1[col].values[:] = 0
        list_1 = []
    for i in df_1_pred.columns:
        x = df_1_pred[i][0]
        list_1.append(x)
    #buat dataset baru
    for i in df_kosong_1.columns:
        for j in list_1:
            if i == j:
                df_kosong_1[i] = df_kosong_1[i].replace(df_kosong_1[i].values,1)
    df_kosong_1['id.orig_p'] = df_1_pred['id.orig_p']
    df_kosong_1['id.resp_p'] = df_1_pred['id.resp_p']
    df_kosong_1['proto'] = df_1_pred['proto']
    df_kosong_1['service'] = df_1_pred['service']
    df_kosong_1['duration'] = df_1_pred['duration']
    df_kosong_1['orig_bytes'] = df_1_pred['orig_bytes']
    df_kosong_1['resp_bytes'] = df_1_pred['resp_bytes']
    df_kosong_1['conn_state'] = df_1_pred['conn_state']
    df_kosong_1['orig_pkts'] = df_1_pred['orig_pkts']
    df_kosong_1['orig_ip_bytes'] = df_1_pred['orig_ip_bytes']
    df_kosong_1['resp_pkts'] = df_1_pred['resp_pkts']
    df_kosong_1['resp_ip_bytes'] = df_1_pred['resp_ip_bytes']
    df_kosong_1 = data_log[:1].drop(['proto','service','conn_state','label'],axis=1)
    st.write("Data Prediksi :")            
    st.write(df_kosong_1)
    if st.button("Prediksi"):
        st.write("## Prediksi Sukses")
        pred_1 = model_log.predict(df_kosong_1)
        if pred_1[0] == 1:
            st.warning('Koneksi masuk kategori Berbahaya')
        else:
            st.success('Koneksi aman')
if menu == 'News Monitoring':
    st.title('News Monitoring')
    newssource = st.sidebar.radio("Pilih Sumber Berita",("Google News","Hacker News"))
    if newssource == 'Google News':
        custom_search = st.expander(label='Search Parameters')
        with custom_search:
            keyword = st.text_input("Search Keyword")
            if st.button("Run Scraping"):
                df_scrap = get_titletext(keyword.lower(),'id','en','ID')
                AgGrid(df_scrap.head())
    if newssource == 'Hacker News':
        no_pages = st.number_input('How many pages to extract the data from? ',step=1,value=1)
        pages = []
        pages.append(home_page_soup)
        if st.button("Run Scraping"):
            no_pages -= 1
            for i in range(no_pages):
                next_page_link = pages[i].find("a", class_="blog-pager-older-link-mobile")['href']
                pages.append(link_to_soup(next_page_link))
            posts_url_title_data = []
            posts_url_others_data = []

            for page in pages:
                posts_in_page = home_page_soup.find_all("a", class_='story-link')
                for post in posts_in_page:
                    posts_url_title_data.append({
                    "url" : post['href'],
                    "date": post.find("span", class_='h-datetime'),
                    "title" : post.find("h2", class_='home-title').text,
                    "tags": post.find("span", class_='h-tags'),
                    "desc" : post.find("div", class_='home-desc').text
                    })
            #st.write(posts_url_title_data[0])
            for entry in posts_url_title_data:
                if 'tags' in entry and entry['tags'] is not None:
                    #soup_tags = BeautifulSoup(entry['tags'], 'html.parser')
                    entry['tags'] = entry['tags'].get_text(strip=True)
                else:
                    entry['tags'] = 'N/A'
                #process date
                if 'date' in entry and entry['date'] is not None:
                    #soup_tags = BeautifulSoup(entry['tags'], 'html.parser')
                    entry['date'] = entry['date'].get_text(strip=True)
                else:
                    entry['date'] = 'N/A'
                #process date
            for entry in posts_url_title_data:
                entry['date'] = str(entry['date'])
            datanews = pd.DataFrame(posts_url_title_data)
            st.dataframe(datanews)
if menu == 'Chatbot':
    st.title('Chatbot')
    #Initiate API (dihapus setelah lomba)
    palm.configure(api_key='use API from PALM')
    prompt = st.text_input('Apa yang ingin kamu tanyakan? (in English) 🤖')
    model = 'models/text-bison-001'
    if st.button("Ask"):
        completion = palm.generate_text(
            model=model,
            prompt=str(prompt),
            temperature=0.2,
            # The maximum length of the response
            max_output_tokens=200,
        )
        with st.spinner('Wait for it...'):
            time.sleep(2)
            st.success('Done!')
            st.write(completion.result)
