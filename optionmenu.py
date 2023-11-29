import streamlit as st
from streamlit_option_menu import option_menu
import base64

LOGO_IMAGE = "./palugada.png"
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
# 1. as sidebar menu
menu = option_menu(None, ["Home","Anonymizer", "Phising Monitoring", "Log Based Monitoring", "News Monitoring", "Chatbot"], 
    icons=['house', 'incognito', "virus", 'router','newspaper','chat-text'], 
    menu_icon="cast", default_index=0, orientation="horizontal",
    styles={
        "container": {"padding": "0!important"},
        "icon": {"color": "white", "font-size": "15px"}, 
        "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "blue"},
    })
if menu == "Home":
    st.write("Welcome to Home")
elif menu == "Anonymizer":
    st.write("Anonymizer")
elif menu == "Phising Monitoring":
    st.write("Phising Monitoring")
elif menu == "Log Based Monitoring":
    st.write("Log Based Monitoring")
elif menu == "News Monitoring":
    st.write("News Monitoring")
else:
    st.write("Phising Monitoring")
    