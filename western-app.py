import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).with_name('truck_profit.db')

DRIVER_CARDS = {
    'Hunter': '7805-7497',
    'Jasper': '7708-4262',
    'Chris': '6772-9087',
    'Austin': '5156-2015',
    'Parks': '7390-3981',
    'Tyllian': '7049',
    'John': '2167',
    'Adam': '9353-8353',
    'Izahia': '2273',
    'Zach': '0366',
    'Jamara': '4941',
    'Ronnie': '2273',
    'Justin C': '5571-1904',
}


def connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS loads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                load_date TEXT NOT NULL,
                driver_name TEXT NOT NULL,
                driver_card TEXT,
                truck_number TEXT,
                load_description TEXT,
                load_pay REAL NOT NULL,
                fuel_gallons REAL NOT NULL,
                fuel_price REAL NOT NULL,
                fuel_cost REAL NOT NULL,
                driver_pay REAL NOT NULL,
                company_profit REAL NOT NULL,
                notes TEXT
            )
        ''')
        conn.commit()


def add_load(data):
    fuel_cost = data['fuel_gallons'] * data['fuel_price']
    driver_pay = data['load_pay'] * 0.25
    company_profit = data['load_pay'] - fuel_cost - driver_pay
    with connect() as conn:
        conn.execute('''
            INSERT INTO loads (
                created_at, load_date, driver_name, driver_card, truck_number,
                load_description, load_pay, fuel_gallons, fuel_price,
                fuel_cost, driver_pay, company_profit, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(timespec='seconds'),
            str(data['load_date']),
            data['driver_name'],
            data['driver_card'],
            data['truck_number'],
            data['load_description'],
            data['load_pay'],
            data['fuel_gallons'],
            data['fuel_price'],
            fuel_cost,
            driver_pay,
            company_profit,
            data['notes'],
        ))
        conn.commit()


def read_loads():
    with connect() as conn:
        return pd.read_sql_query('SELECT * FROM loads ORDER BY load_date DESC, id DESC', conn)


def delete_load(row_id):
    with connect() as conn:
        conn.execute('DELETE FROM loads WHERE id = ?', (row_id,))
        conn.commit()


init_db()
st.set_page_config(page_title='Truck Profit Tracker', page_icon='⛽', layout='wide')
st.title('Truck Fuel & Profit Tracker')
st.caption('Tracks fuel use, fuel spending, 25% driver pay, and company profit per load.')

with st.sidebar:
    st.header('Driver Cards')
    for name, card in DRIVER_CARDS.items():
        st.write(f'**{name}:** {card}')

st.subheader('Add Load')
with st.form('load_form', clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        load_date = st.date_input('Load date')
        driver_options = ['Custom'] + list(DRIVER_CARDS.keys())
        selected_driver = st.selectbox('Driver', driver_options)
        if selected_driver == 'Custom':
            driver_name = st.text_input('Custom driver name')
            driver_card = st.text_input('Driver card number')
        else:
            driver_name = selected_driver
            driver_card = DRIVER_CARDS[selected_driver]
            st.text_input('Driver card number', value=driver_card, disabled=True)
    with col2:
        truck_number = st.text_input('Truck number')
        load_description = st.text_input('Load description')
        load_pay = st.number_input('Money made from load ($)', min_value=0.0, step=50.0, format='%.2f')
    with col3:
        fuel_gallons = st.number_input('Fuel gallons used', min_value=0.0, step=1.0, format='%.3f')
        fuel_price = st.number_input('Fuel price per gallon ($)', min_value=0.0, step=0.10, format='%.3f')
        notes = st.text_area('Notes', height=70)

    fuel_cost_preview = fuel_gallons * fuel_price
    driver_pay_preview = load_pay * 0.25
    profit_preview = load_pay - fuel_cost_preview - driver_pay_preview
    st.info(f'Fuel cost: ${fuel_cost_preview:,.2f} | Driver pay 25%: ${driver_pay_preview:,.2f} | Company profit: ${profit_preview:,.2f}')

    submitted = st.form_submit_button('Save Load')
    if submitted:
        if not driver_name.strip():
            st.error('Driver name is required.')
        elif load_pay <= 0:
            st.error('Load pay must be greater than $0.')
        else:
            add_load({
                'load_date': load_date,
                'driver_name': driver_name.strip(),
                'driver_card': driver_card.strip(),
                'truck_number': truck_number.strip(),
                'load_description': load_description.strip(),
                'load_pay': float(load_pay),
                'fuel_gallons': float(fuel_gallons),
                'fuel_price': float(fuel_price),
                'notes': notes.strip(),
            })
            st.success('Load saved.')
            st.rerun()

st.subheader('Records')
df = read_loads()

if df.empty:
    st.warning('No loads entered yet.')
else:
    total_load_pay = df['load_pay'].sum()
    total_fuel = df['fuel_cost'].sum()
    total_driver_pay = df['driver_pay'].sum()
    total_profit = df['company_profit'].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Total Load Pay', f'${total_load_pay:,.2f}')
    m2.metric('Total Fuel Cost', f'${total_fuel:,.2f}')
    m3.metric('Total Driver Pay', f'${total_driver_pay:,.2f}')
    m4.metric('Company Profit', f'${total_profit:,.2f}')

    show_cols = [
        'id', 'load_date', 'driver_name', 'driver_card', 'truck_number',
        'load_description', 'load_pay', 'fuel_gallons', 'fuel_price',
        'fuel_cost', 'driver_pay', 'company_profit', 'notes'
    ]
    display_df = df[show_cols].copy()
    money_cols = ['load_pay', 'fuel_price', 'fuel_cost', 'driver_pay', 'company_profit']
    for col in money_cols:
        display_df[col] = display_df[col].map(lambda x: f'${x:,.2f}')
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button('Download CSV', csv, 'truck_profit_records.csv', 'text/csv')

    with st.expander('Delete a record'):
        record_id = st.number_input('Record ID to delete', min_value=1, step=1)
        if st.button('Delete Record'):
            delete_load(int(record_id))
            st.success(f'Deleted record {record_id}.')
            st.rerun()
