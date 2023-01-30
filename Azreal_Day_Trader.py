import streamlit as st

from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

from smtplib import SMTP
import smtplib
import sys

import datetime as dt

from tvDatafeed import TvDatafeed, Interval
import numpy as np
import pandas as pd
import pandas_ta as ta

import time

def FEMUR():
    Forex_Pairs_List = ["EURUSD","USDJPY","GBPUSD","AUDUSD","USDCHF","NZDUSD","USDCAD",
                       "EURJPY","EURGBP","EURAUD","EURCHF","EURNZD","EURCAD",
                       "GBPJPY","CHFJPY","NZDJPY","AUDJPY","CADJPY",
                       "GBPAUD","AUDCHF","AUDNZD","AUDCAD",
                       "GBPCHF","NZDCHF","CADCHF",
                       "GBPNZD","GBPCAD",
                       "NZDCAD"]

    Final_df = pd.DataFrame()

    username = 'Azreal1'
    password = st.secrets["tv_password"]

    tv = TvDatafeed(username, password)

    for Currency_Pair in Forex_Pairs_List:
        Symbol_String = Currency_Pair
        Currency_Pair = tv.get_hist(symbol = 'FX:{}'.format(Currency_Pair), exchange = 'FXCM',
                                    interval = Interval.in_15_minute, n_bars = 100)
        #Stochastic
        Stoch = round(ta.stoch(high = Currency_Pair["high"], low = Currency_Pair["low"], 
                               close = Currency_Pair["close"], window = 14, smooth_window = 3),2)
        Currency_Pair["Stochastic %K"] = Stoch["STOCHk_14_3_3"]
        Currency_Pair["Stochastic %D"] = Stoch["STOCHd_14_3_3"]
        #Heiken Ashi
        if Symbol_String[-3:] == "JPY":
            Rounding = 3
        else:
            Rounding = 5
        Heiken_Ashi = round(ta.ha(Currency_Pair["open"], high = Currency_Pair["high"], 
                                  low = Currency_Pair["low"], close = Currency_Pair["close"]),Rounding)
        Currency_Pair["Heiken Ashi Open"] = Heiken_Ashi["HA_open"]
        Currency_Pair["Heiken Ashi High"] = Heiken_Ashi["HA_high"]
        Currency_Pair["Heiken Ashi Low"] = Heiken_Ashi["HA_low"]
        Currency_Pair["Heiken Ashi Close"] = Heiken_Ashi["HA_close"]

        #Heiken Ashi Bool
        Heiken_Ashi_Boolean = []

        i = 0
        while i < Currency_Pair.shape[0]:
            if (Currency_Pair["Heiken Ashi Close"][i] - Currency_Pair["Heiken Ashi Open"][i]) >= 0:
                Heiken_Ashi_Boolean.append(1)
            elif(Currency_Pair["Heiken Ashi Close"][i] - Currency_Pair["Heiken Ashi Open"][i]) < 0:
                Heiken_Ashi_Boolean.append(0)
            i+=1
        Currency_Pair["Heiken Ashi Boolean"] = Heiken_Ashi_Boolean
        Currency_Pair = Currency_Pair.iloc[15:,:]
        
        # Peak swing high and low calculations
        Peak_Value = []
        Peak_Stochastic_Value = []
        Peak_Value_List = list()
        Peak_Stochastic_Value_List = list()
        Peak_Value_List = [np.nan]*Currency_Pair.shape[0]
        Peak_Stochastic_Value_List = [np.nan]*Currency_Pair.shape[0]

        i = 0

        while i < Currency_Pair.shape[0] - 1:
            if Currency_Pair["Heiken Ashi Boolean"][i] == 1 and Currency_Pair["Heiken Ashi Boolean"][i+1] == 0:
                Peak_Value.append(Currency_Pair["close"][i])
                Peak_Stochastic_Value.append(Currency_Pair["Stochastic %K"][i])
                j = i
                while Currency_Pair["Heiken Ashi Boolean"][j] == 1:
                    Peak_Value.append(Currency_Pair["close"][j])
                    Peak_Stochastic_Value.append(Currency_Pair["Stochastic %K"][j])
                    j-=1
                Max_Value = max(Peak_Value)
                Max_Stochastic_Value = max(Peak_Stochastic_Value)
                Peak_Value = []
                Peak_Stochastic_Value = []
                Peak_Value_List[i+1] = Max_Value
                Peak_Stochastic_Value_List[i+1] = Max_Stochastic_Value
                i+=1
            elif Currency_Pair["Heiken Ashi Boolean"][i] == 0 and Currency_Pair["Heiken Ashi Boolean"][i+1] == 1:
                Peak_Value.append(Currency_Pair["close"][i])
                Peak_Stochastic_Value.append(Currency_Pair["Stochastic %K"][i])
                j = i
                while Currency_Pair["Heiken Ashi Boolean"][j] == 0:
                    Peak_Value.append(Currency_Pair["close"][j])
                    Peak_Stochastic_Value.append(Currency_Pair["Stochastic %K"][j])
                    j-=1
                Min_Value = min(Peak_Value)
                Min_Stochastic_Value = min(Peak_Stochastic_Value)
                Peak_Value = []
                Peak_Stochastic_Value = []
                Peak_Value_List[i+1] = Min_Value
                Peak_Stochastic_Value_List[i+1] = Min_Stochastic_Value
                i+=1
            elif Currency_Pair["Heiken Ashi Boolean"][i] == 1 and Currency_Pair["Heiken Ashi Boolean"][i+1] == 1:
                i+=1
            elif Currency_Pair["Heiken Ashi Boolean"][i] == 0 and Currency_Pair["Heiken Ashi Boolean"][i+1] == 0:
                i+=1

        Currency_Pair["Peak Value"] = Peak_Value_List
        Currency_Pair["Stochastic Peak Value"] = Peak_Stochastic_Value_List

        Swing_High_Recent = np.nan
        Stochastic_High_Recent = np.nan
        Swing_Low_Recent = np.nan
        Stochastic_Low_Recent = np.nan

        Looking_For_Shorts = np.nan
        Looking_For_Longs = np.nan

        Divergence_List = list()
        Divergence_List = [np.nan]*Currency_Pair.shape[0]

        i = 0

        while i < Currency_Pair.shape[0] - 1:
          if (pd.isna(Currency_Pair["Peak Value"][i]) == False and Currency_Pair["Heiken Ashi Boolean"][i] == 1):
              Swing_Low_Recent = Currency_Pair["Peak Value"][i]
              Stochastic_Low_Recent = Currency_Pair["Stochastic Peak Value"][i]
              Looking_For_Shorts = True
              Looking_For_Longs = False
              i+=1
          elif (pd.isna(Currency_Pair["Peak Value"][i]) == False and Currency_Pair["Heiken Ashi Boolean"][i] == 0):
              Swing_High_Recent = Currency_Pair["Peak Value"][i]
              Stochastic_High_Recent = Currency_Pair["Stochastic Peak Value"][i]
              Looking_For_Shorts = False
              Looking_For_Longs = True
              i+=1
          if (pd.isna(Swing_High_Recent) == False and pd.isna(Swing_Low_Recent) == False):
            if (Looking_For_Shorts == True):
              if(Currency_Pair["close"][i] >= Swing_High_Recent and Currency_Pair["Stochastic %K"][i] <= Stochastic_High_Recent):
                Divergence_List[i] = "Regular Divergence Short"
                i+=1
              else:
                i+=1
            elif (Looking_For_Longs == True):
                if(Currency_Pair["close"][i] <= Swing_Low_Recent and Currency_Pair["Stochastic %K"][i] >= Stochastic_Low_Recent):
                  Divergence_List[i] = "Regular Divergence Long"
                  i+=1
                else:
                  i+=1
          else:
            i+=1

        Currency_Pair["Divergence"] = Divergence_List

        Final_df = pd.concat([Final_df , Currency_Pair.iloc[[-2]]])
    Final_df = Final_df.drop(["open","high","low","close","volume","Heiken Ashi Open","Heiken Ashi High","Heiken Ashi Low","Heiken Ashi Close"
    ,"Heiken Ashi Boolean","Stochastic %K","Stochastic %D","Peak Value","Stochastic Peak Value"], axis = 1)
    return Final_df

st.title("Notification Engine")

while True:
    if datetime.now().time().hour in range(3,13) and dt.datetime.today().weekday() in range(0,5):
        password_mail = st.secrets["password"]
        Output = FEMUR()
        Output_msg = Output[pd.isna(Output['Divergence']) == False]
        if Output_msg.empty == False:
            msg = MIMEMultipart()
            msg['Subject'] = "Azreal Notification"
            msg['From'] = 'dhruv.suresh2@gmail.com'
            html = """\
            <html>
              <head></head>
              <body>
                {0}
              </body>
            </html>
            """.format(Output_msg.to_html())
            part1 = MIMEText(html, 'html')
            msg.attach(part1)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login('dhruv.suresh2@gmail.com', password_mail)
            server.sendmail(msg['From'], 'f20180884g@alumni.bits-pilani.ac.in' , msg.as_string())
            server.close()
            time.sleep(900)
        else:
            time.sleep(900)
    else:
        time.sleep(3600)
