import streamlit as st
import re
import json
import os
import calendar
from datetime import date, timedelta
import pandas as pd
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

def get_payment_occurrences(payment, year, month):
    occurrences = []
    start_date = date.fromisoformat(payment['start_date'])
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
            occurrences.append({'date': curr_date,'amount': float(payment['amount']),'name': payment['name'],'type': payment['type']})
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

st.set_page_config(page_title="Personal Budget App", layout="wide")
st.title("Personal Budget App")
st.markdown("A simple app to manage recurring payments, estimate your paycheck income, and view your weekly rollover budget.")

if "payments" not in st.session_state:
    st.session_state.payments = load_payments()

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
        new_payment = {"id": str(uuid.uuid4()),"name": p_name,"amount": p_amount,"type": p_type,"start_date": p_start_date.isoformat(),"recurrence": p_recurrence,"end_condition": p_end_cond,"end_months": p_end_months if p_end_cond == "for X months" else None}
        st.session_state.payments.append(new_payment)
        save_payments(st.session_state.payments)
        st.success(f"Added {p_name}!")

st.header("Import Bills from Bank CSV")
st.info("Only recurring-looking charges get flagged as suggestions below. One-time purchases are intentionally left out. Nothing is added to your payments until you explicitly click 'Add to recurring payments' on a specific suggestion.")
uploaded_file = st.file_uploader("Upload a CSV exported from your bank (US Bank, Citizens Community Credit Union, etc.)", type=["csv"])
if uploaded_file is not None:
    try:
        df_csv = pd.read_csv(uploaded_file)
        cols_lower = [str(c).lower().strip() for c in df_csv.columns]

        date_col = None
        for c in ['date', 'transaction date', 'posting date']:
            if c in cols_lower:
                date_col = df_csv.columns[cols_lower.index(c)]
                break

        desc_col = None
        for c in ['description', 'payee', 'memo', 'merchant name', 'transaction']:
            if c in cols_lower:
                desc_col = df_csv.columns[cols_lower.index(c)]
                break

        amount_setup = None
        if 'amount' in cols_lower:
            amount_setup = ('single', df_csv.columns[cols_lower.index('amount')])
        elif 'debit' in cols_lower and 'credit' in cols_lower:
            amount_setup = ('split', df_csv.columns[cols_lower.index('debit')], df_csv.columns[cols_lower.index('credit')])
        elif 'withdrawal' in cols_lower and 'deposit' in cols_lower:
            amount_setup = ('split', df_csv.columns[cols_lower.index('withdrawal')], df_csv.columns[cols_lower.index('deposit')])

        if not date_col or not desc_col or not amount_setup:
            st.error(f"Could not find the expected columns (date, description, amount). Columns found in your file: {list(df_csv.columns)}")
        else:
            if amount_setup[0] == 'single':
                df_csv['_amount'] = pd.to_numeric(df_csv[amount_setup[1]], errors='coerce').fillna(0)
            else:
                debits = pd.to_numeric(df_csv[amount_setup[1]], errors='coerce').fillna(0).abs()
                credits = pd.to_numeric(df_csv[amount_setup[2]], errors='coerce').fillna(0).abs()
                df_csv['_amount'] = credits - debits

            orig_len = len(df_csv)
            df_csv['_pdate'] = pd.to_datetime(df_csv[date_col], errors='coerce')
            df_csv = df_csv.dropna(subset=['_pdate']).copy()
            skipped = orig_len - len(df_csv)
            if skipped > 0:
                st.warning(f"Skipped {skipped} row(s) with dates that couldn't be parsed.")

            def normalize_desc(d):
                d = str(d).upper().strip()
                d = re.sub(r'\s+', ' ', d)
                d = re.sub(r'\s+[A-Z0-9]*\d+[A-Z0-9]*$', '', d).strip()
                return d

            df_csv['_norm_desc'] = df_csv[desc_col].apply(normalize_desc)
            df_csv['_ym'] = df_csv['_pdate'].dt.to_period('M')
            df_csv['_day'] = df_csv['_pdate'].dt.day

            suggestions = []
            for name, group in df_csv.groupby('_norm_desc'):
                if name == '' or group['_ym'].nunique() < 2:
                    continue
                amts = group['_amount'].abs()
                mean_amt = amts.mean()
                spread = amts.max() - amts.min()
                if spread <= 5 or (mean_amt > 0 and spread <= 0.10 * mean_amt):
                    suggestions.append({
                        'suggested_name': name.title(),
                        'avg_amount': round(float(mean_amt), 2),
                        'avg_day': int(round(group['_day'].mean())),
                        'occurrence_count': int(len(group))
                    })

            if suggestions:
                st.subheader("Suggested Recurring Bills")
                for idx, sug in enumerate(suggestions):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 2])
                    c1.write(sug['suggested_name'])
                    c2.write(f"${sug['avg_amount']:.2f}")
                    c3.write(f"Day {sug['avg_day']}")
                    c4.write(f"{sug['occurrence_count']}x")
                    if c5.button("Add to recurring payments", key=f"add_sug_{idx}"):
                        today = date.today()
                        safe_day = min(sug['avg_day'], calendar.monthrange(today.year, today.month)[1])
                        new_payment = {
                            "id": str(uuid.uuid4()),
                            "name": sug['suggested_name'],
                            "amount": sug['avg_amount'],
                            "type": "expense",
                            "start_date": date(today.year, today.month, safe_day).isoformat(),
                            "recurrence": "monthly",
                            "end_condition": "indefinite",
                            "end_months": None
                        }
                        st.session_state.payments.append(new_payment)
                        save_payments(st.session_state.payments)
                        st.success(f"Added {sug['suggested_name']} to your recurring payments!")
                        st.rerun()
            else:
                st.info("No recurring-looking bills detected in this file yet.")

            st.subheader("All Parsed Transactions")
            display_df = df_csv[[date_col, desc_col, '_amount']].copy()
            display_df.columns = ['Date', 'Description', 'Amount']
            st.dataframe(display_df.sort_values('Date', ascending=False), use_container_width=True)
    except Exception as e:
        st.error(f"Couldn't process that file: {e}")

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

st.header("Income Estimator")
income_mode = st.radio("Pay Schedule", ["Semi-monthly (1st & 16th)", "Biweekly (every 14 days)"])
col1, col2 = st.columns(2)
with col1:
    daily_rate = st.number_input("Daily Rate (per weekday worked)", min_value=0.0, step=10.0, value=100.0)
anchor_date = None
if income_mode == "Biweekly (every 14 days)":
    with col2:
        anchor_date = st.date_input("Most recent/last pay date (Anchor)")

st.header("Monthly Calendar & Rollover")
col_y, col_m = st.columns(2)
with col_y:
    view_year = st.number_input("Year", min_value=2000, max_value=2100, value=date.today().year)
with col_m:
    view_month = st.selectbox("Month", range(1, 13), format_func=lambda x: calendar.month_name[x], index=date.today().month - 1)

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
cal = calendar.Calendar(firstweekday=0)
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
    if d.weekday() == 6:
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
            weekly_tally.append({'week_range': f"{current_week_start.strftime('%b %d')} - {current_week_end.strftime('%b %d')}",'income': current_week_income,'expense': current_week_expense,'net': net,'deficit': running_deficit,'savings': available_savings})
        current_week_income = 0
        current_week_expense = 0
        current_week_start = None
        current_week_events = []
if weekly_tally:
    st.dataframe(pd.DataFrame(weekly_tally))
else:
    st.info("No data for this month yet.")
