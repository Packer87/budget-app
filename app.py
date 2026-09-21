import streamlit as st
import json
import os
import calendar
from datetime import date, timedelta
import pandas as pd
import pdfplumber
import uuid

# --- CORE LOGIC ---
PAYMENTS_FILE = "payments.json"

def load_payments():
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_payments(payments):
    with open(PAYMENTS_FILE, "w") as f:
        json.dump(payments, f, indent=4)

def get_weekdays_in_range(start_date, end_date):
    count = 0
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5:
            count += 1
        curr += timedelta(days=1)
    return count

def calculate_semi_monthly_pay(year, month, daily_rate):
    # 1st of month paycheck
    pay_date_1 = date(year, month, 1)
    if month == 1:
        prior_month = 12
        prior_year = year - 1
    else:
        prior_month = month - 1
        prior_year = year
    start_date_1 = date(prior_year, prior_month, 27)
    end_date_1 = date(year, month, 11)
    weekdays_1 = get_weekdays_in_range(start_date_1, end_date_1)
    pay_1 = weekdays_1 * daily_rate

    # 16th of month paycheck
    pay_date_2 = date(year, month, 16)
    start_date_2 = date(year, month, 12)
    end_date_2 = date(year, month, 26)
    weekdays_2 = get_weekdays_in_range(start_date_2, end_date_2)
    pay_2 = weekdays_2 * daily_rate

    return [
        {'date': pay_date_1, 'amount': pay_1, 'name': 'Paycheck (1st)', 'type': 'income'},
        {'date': pay_date_2, 'amount': pay_2, 'name': 'Paycheck (16th)', 'type': 'income'}
    ]

def calculate_biweekly_pay(year, month, anchor_date, daily_rate):
    month_start = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)
    month_end = date(year, month, days_in_month)

    # Find first pay date in the month
    diff = (month_start - anchor_date).days
    days_to_first = (14 - (diff % 14)) % 14
    first_pay_date = month_start + timedelta(days=days_to_first)

    pay_dates = []
    curr = first_pay_date
    while curr <= month_end:
        start_date = curr - timedelta(days=13)
        weekdays = get_weekdays_in_range(start_date, curr)
        pay = weekdays * daily_rate
        pay_dates.append({'date': curr, 'amount': pay, 'name': f'Paycheck ({curr.strftime("%b %d")})', 'type': 'income'})
        curr += timedelta(days=14)

    return pay_dates

# Generate occurrences of a payment within the month
def get_payment_occurrences(payment, year, month):
    occurrences = []
    start_date = date.fromisoformat(payment['start_date'])

    # Check end condition
    end_date = None
    if payment.get('end_condition') == 'for X months' and payment.get('end_months'):
        end_date = start_date + timedelta(days=30 * int(payment['end_months']))

    month_start = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)
    month_end = date(year, month, days_in_month)

    if start_date > month_end:
        return occurrences

    curr_date = start_date

    if curr_date < month_start:
        if payment['recurrence'] == 'single':
            return []
        elif payment['recurrence'] == 'weekly':
            diff = (month_start - curr_date).days
            days_to_add = ((diff // 7) + (1 if diff % 7 != 0 else 0)) * 7
            curr_date += timedelta(days=days_to_add)
        elif payment['recurrence'] == 'biweekly':
            diff = (month_start - curr_date).days
            days_to_add = ((diff // 14) + (1 if diff % 14 != 0 else 0)) * 14
            curr_date += timedelta(days=days_to_add)
        elif payment['recurrence'] == 'monthly':
            try:
                curr_date = date(year, month, curr_date.day)
            except ValueError:
                curr_date = date(year, month, calendar.monthrange(year, month)[1])

    while curr_date <= month_end:
        if end_date and curr_date > end_date:
            break

        if curr_date >= month_start:
            occurrences.append({
                'date': curr_date,
                'amount': float(payment['amount']),
                'name': payment['name'],
                'type': payment['type']
            })

        if payment['recurrence'] == 'single':
            break
        elif payment['recurrence'] == 'weekly':
            curr_date += timedelta(days=7)
        elif payment['recurrence'] == 'biweekly':
            curr_date += timedelta(days=14)
        elif payment['recurrence'] == 'monthly':
            next_month = curr_date.month % 12 + 1
            next_year = curr_date.year + (curr_date.month // 12)
            try:
                curr_date = date(next_year, next_month, start_date.day)
            except ValueError:
                curr_date = date(next_year, next_month, calendar.monthrange(next_year, next_month)[1])

    return occurrences


# --- STREAMLIT UI ---
st.set_page_config(page_title="Personal Budget App", layout="wide")

st.title("Personal Budget App")
st.markdown("A simple app to manage recurring payments, estimate your paycheck income, and view your weekly rollover budget.")

if "payments" not in st.session_state:
    st.session_state.payments = load_payments()

# --- 0. IMPORT PDF ---
st.header("Import Data from PDF")
uploaded_pdf = st.file_uploader("Upload PDF (e.g. statement)", type=["pdf"])
if uploaded_pdf:
    import pdfplumber
    with pdfplumber.open(uploaded_pdf) as pdf:
        extracted = chr(10).join(page.extract_text() for page in pdf.pages if page.extract_text())
        st.success("PDF loaded successfully!")
        with st.expander("View extracted text"):
            st.text(extracted)

# --- 1. ADD PAYMENT ---
st.header("Add Payment")
with st.form("add_payment_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        p_name = st.text_input("Name")
        p_amount = st.number_input("Amount", min_value=0.0, step=1.0)
        p_type = st.selectbox("Type", ["expense", "income"])
    with col2:
        p_start_date = st.date_input("Start Date")
        p_recurrence = st.selectbox("Recurrence", ["single", "weekly", "biweekly", "monthly"])
    with col3:
        p_end_cond = st.selectbox("End Condition", ["indefinite", "for X months"])
        p_end_months = st.number_input("Months", min_value=1, step=1, value=1)

    submitted = st.form_submit_button("Add Payment")
    if submitted:
        new_payment = {
            "id": str(uuid.uuid4()),
            "name": p_name,
            "amount": p_amount,
            "type": p_type,
            "start_date": p_start_date.isoformat(),
            "recurrence": p_recurrence,
            "end_condition": p_end_cond,
            "end_months": p_end_months if p_end_cond == "for X months" else None
        }
        st.session_state.payments.append(new_payment)
        save_payments(st.session_state.payments)
        st.success(f"Added {p_name}!")

# --- 2. MANAGE PAYMENTS ---
st.header("Manage Payments")
if len(st.session_state.payments) > 0:
    df = pd.DataFrame(st.session_state.payments)
    edited_df = st.data_editor(df, num_rows="dynamic", key="data_editor")

    if st.button("Save Changes"):
        updated_payments = edited_df.to_dict(orient="records")
        st.session_state.payments = updated_payments
        save_payments(updated_payments)
        st.success("Changes saved!")
else:
    st.info("No payments added yet.")

# --- 3. INCOME ESTIMATOR ---
st.header("Income Estimator")
income_mode = st.radio("Pay Schedule", ["Semi-monthly (1st & 16th)", "Biweekly (every 14 days)"])

col1, col2 = st.columns(2)
with col1:
    daily_rate = st.number_input("Daily Rate (per weekday worked)", min_value=0.0, step=10.0, value=100.0)

anchor_date = None
if income_mode == "Biweekly (every 14 days)":
    with col2:
        anchor_date = st.date_input("Most recent/last pay date (Anchor)")

# --- 4. MONTHLY CALENDAR & ROLLOVER ---
st.header("Monthly Calendar & Rollover")
col_y, col_m = st.columns(2)
with col_y:
    view_year = st.number_input("Year", min_value=2000, max_value=2100, value=date.today().year)
with col_m:
    view_month = st.selectbox("Month", range(1, 13), format_func=lambda x: calendar.month_name[x], index=date.today().month - 1)

# Generate events
month_events = []
for p in st.session_state.payments:
    month_events.extend(get_payment_occurrences(p, view_year, view_month))

if income_mode == "Semi-monthly (1st & 16th)":
    paychecks = calculate_semi_monthly_pay(view_year, view_month, daily_rate)
    month_events.extend(paychecks)
elif income_mode == "Biweekly (every 14 days)" and anchor_date is not None:
    paychecks = calculate_biweekly_pay(view_year, view_month, anchor_date, daily_rate)
    month_events.extend(paychecks)

initial_deficit = st.number_input("Carried Deficit from previous month", value=0.0, step=10.0)
running_deficit = initial_deficit

cal = calendar.Calendar(firstweekday=0) # Monday=0, Sunday=6
month_dates = cal.itermonthdates(view_year, view_month)

weekly_tally = []
current_week_income = 0
current_week_expense = 0
current_week_start = None
current_week_events = []

for d in month_dates:
    if current_week_start is None:
        current_week_start = d

    if d.month == view_month and d.year == view_year:
        day_events = [e for e in month_events if e['date'] == d]
        for e in day_events:
            if e['type'] == 'income':
                current_week_income += e['amount']
            else:
                current_week_expense += e['amount']
            current_week_events.append(e)

    if d.weekday() == 6: # Sunday end of week
        current_week_end = d
        net = current_week_income - current_week_expense
        total_balance = net + running_deficit

        if total_balance < 0:
            running_deficit = total_balance
            available_savings = 0.0
        else:
            available_savings = total_balance
            running_deficit = 0.0

        week_contains_month = any((current_week_start + timedelta(days=i)).month == view_month for i in range(7))
        if week_contains_month:
            weekly_tally.append({
                'week_range': f"{current_week_start.strftime('%b %d')} - {current_week_end.strftime('%b %d')}",
                'income': current_week_income,
                'expense': current_week_expense,
                'net': net,
                'deficit_carried': running_deficit,
                'available_savings': available_savings,
                'events': current_week_events
            })

        current_week_income = 0
        current_week_expense = 0
        current_week_start = None
        current_week_events = []

for w in weekly_tally:
    st.subheader(f"Week: {w['week_range']}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Income", f"${w['income']:.2f}")
    c2.metric("Expense", f"${w['expense']:.2f}")
    c3.metric("Net", f"${w['net']:.2f}")
    c4.metric("Carried Deficit", f"${w['deficit_carried']:.2f}")
    c5.metric("Available Savings", f"${w['available_savings']:.2f}")

    if w['events']:
        event_df = pd.DataFrame(w['events'])
        event_df['date'] = event_df['date'].astype(str)
        st.dataframe(event_df[['date', 'name', 'type', 'amount']], use_container_width=True, hide_index=True)
    else:
        st.write("No events this week.")
    st.markdown("---")
