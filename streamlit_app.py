#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 09:31:20 2025

@author: Joshua Robinson
"""

from astroquery.heasarc import Heasarc

from astropy.coordinates import SkyCoord
from astropy.units import deg
from astroquery.ipac.ned import Ned

import streamlit as st
#import numpy as np
import plotly.express as px

st.set_page_config(
        page_title="High-Energy Data Explorer",
        page_icon="🛰️",
        layout="wide",
    )

def get_position(object_name=None,ra=None,dec=None):
    if object_name:
        if st.session_state['current query'] != object_name:#we already have the position, it should not be requested again
            try:
                st.session_state[input_object_name]=SkyCoord.from_name(object_name)
                st.session_state['object ra']=st.session_state[input_object_name].ra.value
                st.session_state['object dec']=st.session_state[input_object_name].dec.value
                st.session_state['current query'] = input_object_name
            except:
                st.warning(f"Could not resolve name \"{input_object_name}\"")
                st.session_state['object ra'] =None
                st.session_state['object dec']=None
    if ra and dec:
        st.session_state['user position']=SkyCoord(ra=ra*deg,dec=dec*deg)
        st.session_state['object ra']=ra
        st.session_state['object dec']=dec
tab={}

if 'list_of_catalogues' not in st.session_state:
    st.session_state['list_of_catalogues']=Heasarc.list_catalogs(master=True)

if 'query object name' not in st.session_state:    
    st.session_state['query object name']=''

if 'NED data' not in st.session_state:  
    st.session_state['NED data']={}
    
if 'current query'not in st.session_state:
    st.session_state['current query'] =''
    
    
if 'object ra' not in st.session_state:
    st.session_state['object ra']=0.0
    
if 'object dec' not in st.session_state:
    st.session_state['object dec']=0.0

parameters_col, information_col= st.columns([1,3])

HEASARC_tab, NED_tab = information_col.tabs(["HEASARC", "NED"])

selected_obs=-1
#tab = Heasarc.query_region(pos, catalog='ixmaster')

#tab = tab[tab['time'] > 0]

#tab.sort('time')
can_search=True
query_type=parameters_col.radio("Query Type",['Resolve Name', 'Coordinates'])
parameters_col.divider()

default_name_value = st.session_state['query object name'] if query_type == 'Resolve Name' else '-'
input_object_name = parameters_col.text_input("Object Name",value=default_name_value,disabled= (query_type != 'Resolve Name'))

if query_type == 'Resolve Name':
    if st.session_state['current query'] != input_object_name:#we already have the position, it should not be requested again
        get_position(object_name=input_object_name)

ra_text=parameters_col.number_input('RA', value=st.session_state['object ra'],disabled= (query_type == 'Resolve Name'))
dec_text=parameters_col.number_input('DEC', value=st.session_state['object dec'],disabled= (query_type == 'Resolve Name'))

if query_type == 'Coordinates':
    get_position(ra=ra_text,dec=dec_text)
    

search_radius=parameters_col.number_input('Search Radius [ ° ]', min_value=0.0, value=5.000)
parameters_col.divider()
    
catalogue_name_to_search=HEASARC_tab.selectbox('Select Catalog:', st.session_state['list_of_catalogues']['description'])
catalogue_to_search=st.session_state['list_of_catalogues']['name'][st.session_state['list_of_catalogues']['description']==catalogue_name_to_search]


position_key=f"user position ({ra_text}, {dec_text})" if query_type != 'Resolve Name' else input_object_name
query_key=position_key+' '+catalogue_name_to_search


HEASARC_table=''
    
if query_key in st.session_state:#dont search the same catalog for the same info twice
    print("skipped catalogue search, used local data")
    HEASARC_table=st.session_state[query_key]
else:
    if HEASARC_tab.button(f"Search {catalogue_to_search[0]}",help=f"Search {catalogue_to_search[0]} ({search_radius}° radius around ({st.session_state['object ra']},{st.session_state['object dec']}) )",type="primary"):
        print("query heasarc")
        with HEASARC_tab:
            with st.spinner("Running query..."):
                HEASARC_table=Heasarc.query_region(st.session_state[position_key], catalog=catalogue_to_search[0],radius=search_radius*deg)
                HEASARC_table=HEASARC_table
                st.session_state[query_key]=HEASARC_table
        
  
has_ned_data=False
if NED_tab.button("Search NED photometry",help=f'Search object {st.session_state["query object name"]} in NED',disabled=not(can_search),type="primary"):
    try:
        with NED_tab:
            with st.spinner('Downloading data'):
                st.session_state['NED data']=Ned.get_table(position_key, table = 'photometry')
            with st.spinner('Transforming data'):
                neddata_df=st.session_state['NED data'].to_pandas()
                
                neddata_df['nuFnu']=neddata_df["Frequency"]*neddata_df["Flux Density"]*(neddata_df['NED Units']=='Jy')+\
                    neddata_df["Flux Density"]*(neddata_df['NED Units']=='Jy-Hz')
                
                neddata_df["NED Uncertainty"]=neddata_df["NED Uncertainty"].str.replace("...","0.0")
                neddata_df["NED Uncertainty"]=neddata_df["NED Uncertainty"].str.replace("+/-","")
                neddata_df["NED Uncertainty"]=neddata_df["NED Uncertainty"].str.replace("<","")
                neddata_df["NED Uncertainty"]=neddata_df["NED Uncertainty"].str.replace(">","")
                neddata_df["NED Uncertainty"]=neddata_df["NED Uncertainty"].str.replace(" ","")
                neddata_df["NED Uncertainty"]=neddata_df["NED Uncertainty"].replace("","0.0")
                
                neddata_df["NED Uncertainty"]=neddata_df["NED Uncertainty"].astype(float)
                
                neddata_df['nuFnu_e']=(1+neddata_df["Frequency"]*(neddata_df['NED Units']=='Jy'))*neddata_df["NED Uncertainty"]
                NED_tab.download_button(
                    label="Download text",
                    data=((st.session_state['NED data']).to_pandas()).to_csv(index=False).encode('utf-8'),
                    on_click="ignore",
                    type="secondary",
                    icon=":material/download:",
                )    
            with st.spinner('Graphing data'):
                fig = px.scatter(neddata_df, x="Frequency", y="nuFnu",
                                 color="Observed Passband",error_y='nuFnu_e',
                                 log_x=True,log_y=True,
                                 title="SED",
                                 labels={
                                     "Frequency": "Frequency [Hz]",
                                     "nuFnu": r'\nu F_\nu [JyHz]',
                                 })
                
                fig.update_xaxes(exponentformat = 'power')
                
                fig.update_yaxes(exponentformat = 'power')
                NED_tab.plotly_chart(fig)
            
            NED_tab.dataframe(neddata_df)
            has_ned_data=True
    except:
        name = f"user position (RA={ra_text}, DEC={dec_text})" if query_type != 'Resolve Name' else input_object_name
        NED_tab.warning(f"No photometry found for {name}")
   
        
@st.dialog("Citations")
def download():
    st.write("Please cite NED and any related works correctly.")
    st.write("https://ned.ipac.caltech.edu/Documents/Overview/Acknowledgments")
    if st.button("Okay"):
        st.rerun()
        
ned_download_name=input_object_name if query_type == 'Resolve Name' else f"RA:{st.session_state['object ra']}-DEC:{st.session_state['object ra']}"
          

#else:

    
    #if NED_tab.button("Search NED photometry",help=f"Search Position (RA,DEC) = ({st.session_state['object ra']},{st.session_state['object dec']}) in NED",disabled=not(can_search)):
        #try:
            
            #st.session_state['NED data']=Ned.get_table(st.session_state[position_key],radius=search_radius*deg, table = 'photometry')
            
            #NED_tab.write(st.session_state['NED data'])
        #except:
            #NED_tab.warning(f"No photometry found for (RA,DEC) = ({st.session_state['object ra']},{st.session_state['object dec']})")

has_searched_heasarc=True if query_key in st.session_state else False

#HEASARC_tab.write(f"query key in session state: {query_key in st.session_state}")
#HEASARC_tab.write(f"has_searched_heasarc k: {has_searched_heasarc}")

if not HEASARC_table and has_searched_heasarc:
    if has_searched_heasarc:
        HEASARC_tab.warning(f"No results found in {catalogue_name_to_search} for {position_key}")
else:
    if has_searched_heasarc:
        HEASARC_tab.write(f"{len(HEASARC_table)} results found for {query_key}")
        HEASARC_table_df=HEASARC_table
        selected_obs = HEASARC_tab.dataframe(HEASARC_table,selection_mode=["single-row"],on_select='rerun')
    
                
        if selected_obs !=-1:
            if selected_obs.selection.rows:
                HEASARC_tab.divider()
                selected_row = selected_obs.selection.rows[0]
                filtered_tab = HEASARC_table[selected_row:selected_row+1]
                with HEASARC_tab:
                    with st.spinner("Fetching data location..."):
                            data_location=Heasarc.locate_data(filtered_tab)[0]
                data_length=data_location['content_length']
                if data_length < 1e3:
                    HEASARC_tab.markdown(f"Data directory ({data_length*1e-3:.1f} KB) {data_location['access_url']}")
                elif data_length < 1e9:
                    HEASARC_tab.markdown(f"Data directory ({data_length*1e-6:.1f} MB) {data_location['access_url']}")
                elif data_length > 1e9:
                    HEASARC_tab.markdown(f"Data directory ({data_length*1e-9:.1f} GB) {data_location['access_url']}")
                else:
                    HEASARC_tab.write(f"Data directory ({data_length} B)")
    
                HEASARC_tab.markdown('Download command:',help='Copy and paste the following text into your command line to download the data')
                HEASARC_tab.code(f"wget -q -nH --no-check-certificate --cut-dirs=5 -r -w1 -l0 -c -N -np -R 'index*' -erobots=off --retr-symlinks {data_location['access_url']}",language='None')


st.divider()

st.markdown("__Acknowledgements__")
st.markdown("*This interface has made use of data, software and/or web tools obtained from the High Energy Astrophysics Science Archive Research Center (HEASARC), a service of the Astrophysics Science Division at NASA/GSFC and of the Smithsonian Astrophysical Observatory's High Energy Astrophysics Division.*" )
st.markdown("*This interface has made use of the NASA/IPAC Extragalactic Database, which is funded by the National Aeronautics and Space Administration and operated by the California Institute of Technology.*")
