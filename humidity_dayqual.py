import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

weather_data = pd.read_csv('tokyo_humidity_2025_10.csv')

dayqual = weather_data['Avg_Humidity']
dayqual = round(dayqual / 10)
print(dayqual)
plt.plot(dayqual)
plt.show()
#plt.savefig("figure.png")