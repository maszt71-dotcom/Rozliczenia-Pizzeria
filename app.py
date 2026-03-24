from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
DB_FILE = 'finanse_data.csv'

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            for col in ['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data_zdarzenia']:
                if col not in df.columns: df[col] = ""
            return df
        except: pass
    return pd.DataFrame(columns=['Data', 'Typ', 'Kwota', 'Opis', 'Status', 'Data_zdarzenia'])

@app.route('/')
def index():
    df = load_data()
    df_active = df[df['Status'] == 'Aktywny'].copy()
    df_active['Kwota'] = pd.to_numeric(df_active['Kwota'], errors='coerce').fillna(0)
    
    # Obliczenia do kafelków
    s_og = df_active[df_active['Typ'] == 'Przychód ogólny']['Kwota'].sum()
    s_wyd = df_active[df_active['Typ'] == 'Wydatki gotówkowe']['Kwota'].sum()
    s_got = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]['Kwota'].sum() - s_wyd
    
    # RZECZ ŚWIĘTA - Podsumowanie kierowców
    gotowka_df = df_active[df_active['Typ'].str.contains('Gotówka', na=False)]
    rozliczenie = gotowka_df.groupby('Typ')['Kwota'].sum().to_dict()

    return render_template('index.html', s_og=s_og, s_got=s_got, s_wyd=s_wyd, 
                           rozliczenie=rozliczenie, now=datetime.now().strftime("%Y-%m-%d"))

@app.route('/add', methods=['POST'])
def add():
    typ = request.form.get('typ')
    kwota = float(request.form.get('kwota') or 0)
    opis = request.form.get('opis', '')
    data_zd = request.form.get('data_zd')
    
    df = load_data()
    nowy = pd.DataFrame([{'Data': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Typ': typ, 
                          'Kwota': kwota, 'Opis': opis, 'Status': 'Aktywny', 'Data_zdarzenia': data_zd}])
    pd.concat([df, nowy], ignore_index=True).to_csv(DB_FILE, index=False)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
