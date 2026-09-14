import streamlit as st
import pandas as pd
import json
import os
import uuid
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import numpy as np

# --- CONFIG & SETUP ---
st.set_page_config(page_title="Budget & Calendar App", layout="wide")

DATA_FILE = "payments.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialize session state for data if not present
if 'payments' not in st.session_state:
    st.session_state.payments = load_data()

# --- HELPERS ---
def get_weekdays(start_dt, end_dt):
    # np.busday_count is end-exclusive, so we add 1 day to end_dt
    return int(np.busday_count(start_dt, end_dt + timedelta(days=1)))

def get_paycheck_estimate(target_month_date, daily_rate):
    # Paycheck on 1st of month
    # Rule from prompt: 27th of prior month through the 11th
    prior_month = target_month_date - relativedelta(months=1)
    p1_start = date(prior_month.year, prior_month.month, 27)
    p1_end = date(target_month_date.year, target_month_date.month, 11)
    days_p1 = get_weekdays(p1_start, p1_end)
    pay_1st = days_p1 * daily_rate

    # Paycheck on 16th of month
    # Rule from prompt: 12th through 26th
    p2_start = date(target_month_date.year, target_month_date.month, 12)
    p2_end = date(target_month_date.year, target_month_date.month, 26)
    days_p2 = get_weekdays(p2_start, p2_end)
    pay_16th = days_p2 * daily_rate

    return pay_1st, pay_16th

def get_payments_for_date(target_date, payments):
    due_today = []
    for p in payments:
        start_date = datetime.strptime(p['start_date'], '%Y-%m-%d').date()
        if target_date < start_date:
            continue

        if p['recurrence'] == 'single':
            if target_date == start_date:
                due_today.append(p)
            continue

        # Check end condition
        if p['end_condition'] == 'for X months' and p.get('end_months'):
            end_date = start_date + relativedelta(months=p['end_months'])
            if target_date > end_date:
                continue

        # Check recurrence match
        if p['recurrence'] == 'weekly':
            if (target_date - start_date).days % 7 == 0:
                due_today.append(p)
        elif p['recurrence'] == 'biweekly':
            if (target_date - start_date).days % 14 == 0:
                due_today.append(p)
        elif p['recurrence'] == 'monthly':
            # Match if it's the same day of the month
            if target_date.day == start_date.day:
                due_today.append(p)
            else:
                # Handle end of month edge cases (e.g., start 31st, current month has 30 days)
                import calendar
                last_day_of_month = calendar.monthrange(target_date.year, target_date.month)[1]
                if start_date.day > last_day_of_month and target_date.day == last_day_of_month:
                    due_today.append(p)
    return due_today

# --- UI --- 
st.title("Personal Budget & Calendar App")
st.markdown("Welcome to your personal budget manager! Add your payments, estimate your income, and see your weekly rollover balance below.")

# 1. Add Payment Form
st.header("Add Payment")
with st.form("add_payment_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("Name / Label")
        p_amount = st.number_input("Amount ($)", min_value=0.0, step=1.0)
        p_type = st.selectbox("Type", ["expense", "income"])
        p_start = st.date_input("Start Date")
    with col2:
        p_recurrence = st.selectbox("Recurrence", ["single", "weekly", "biweekly", "monthly"])
        p_end_cond = st.selectbox("End Condition", ["indefinite", "for X months"])
        p_end_months = st.number_input("If 'for X months', how many?", min_value=1, value=1, step=1)

    submitted = st.form_submit_button("Save Payment")
    if submitted and p_name:
        new_payment = {
            "id": str(uuid.uuid4()),
            "name": p_name,
            "amount": p_amount,
            "type": p_type,
            "recurrence": p_recurrence,
            "end_condition": p_end_cond,
            "end_months": p_end_months if p_end_cond == 'for X months' else None,
            "start_date": p_start.strftime('%Y-%m-%d')
        }
        st.session_state.payments.append(new_payment)
        save_data(st.session_state.payments)
        st.success(f"Added '{p_name}'!")
        st.rerun()

# Manage Payments
st.header("Manage Payments")
if st.session_state.payments:
    df = pd.DataFrame(st.session_state.payments)
    # Data Editor to allow deletions/edits
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if not edited_df.equals(df):
        st.session_state.payments = edited_df.to_dict('records')
        save_data(st.session_state.payments)
else:
    st.info("No payments added yet.")

# 2. Income Estimator
st.header("Income Estimator")
daily_rate = st.number_input("Estimated pay per weekday worked ($)", min_value=0.0, step=1.0, value=0.0)

# 3. Monthly Calendar & Rollover
st.header("Monthly Calendar & Rollover")
col_cal1, col_cal2 = st.columns([1, 3])
with col_cal1:
    selected_month = st.date_input("Select a month to view", value=date.today())
    selected_month = selected_month.replace(day=1) # normalize to 1st of month

if daily_rate > 0:
    pay_1, pay_16 = get_paycheck_estimate(selected_month, daily_rate)
    st.markdown(f"**Estimated Pay for {selected_month.strftime('%B %Y')}**: 1st = ${pay_1:,.2f} | 16th = ${pay_16:,.2f}")
else:
    pay_1, pay_16 = 0.0, 0.0

# Generate calendar view data
import calendar
_, num_days = calendar.monthrange(selected_month.year, selected_month.month)

weekly_data = []
current_week_start = selected_month
week_income = 0.0
week_expense = 0.0
week_events = []

running_deficit = 0.0

# To support rollover properly, we must compute from the start of the month, 
# but theoretically it should be from the beginning of time. For simplicity in this monthly view, 
# we will carry forward deficit within the viewed month.
for day in range(1, num_days + 1):
    current_date = date(selected_month.year, selected_month.month, day)

    # Add estimated paychecks
    if current_date.day == 1:
        week_income += pay_1
        week_events.append(f"Paycheck (1st): ${pay_1:,.2f}")
    if current_date.day == 16:
        week_income += pay_16
        week_events.append(f"Paycheck (16th): ${pay_16:,.2f}")

    # Add user payments
    due_today = get_payments_for_date(current_date, st.session_state.payments)
    for p in due_today:
        if p['type'] == 'income':
            week_income += p['amount']
            week_events.append(f"{p['name']} (+${p['amount']})")
        else:
            week_expense += p['amount']
            week_events.append(f"{p['name']} (-${p['amount']})")

    # End of week (Sunday) or end of month
    if current_date.weekday() == 6 or day == num_days:
        week_net = week_income - week_expense

        # Rollover Logic
        available_after_rollover = week_net + running_deficit
        if available_after_rollover < 0:
            running_deficit = available_after_rollover
            available_after_rollover = 0.0
        else:
            running_deficit = 0.0

        weekly_data.append({
            "Week": f"{current_week_start.strftime('%b %d')} - {current_date.strftime('%b %d')}",
            "Events": ", ".join(week_events),
            "Income": f"${week_income:,.2f}",
            "Expense": f"${week_expense:,.2f}",
            "Weekly Net": f"${week_net:,.2f}",
            "Deficit Carried": f"${running_deficit:,.2f}",
            "Available Savings": f"${available_after_rollover:,.2f}"
        })

        # Reset for next week
        if day < num_days:
            current_week_start = current_date + timedelta(days=1)
        week_income = 0.0
        week_expense = 0.0
        week_events = []

st.table(pd.DataFrame(weekly_data))
