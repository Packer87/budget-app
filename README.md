# Budget App
A simple Streamlit application for personal budgeting.

## Features
- Track expenses and incomes.
- Automatic pay calculations based on daily rate (Semi-monthly or Biweekly).
- Monthly calendar view grouped by week with rollover calculation for running deficits.
- Local persistence via JSON.

## Importing Bills from a Bank CSV
You can import your transaction history to automatically find recurring bills, instead of typing them in one by one:
1. In your bank's online banking (this works with typical US Bank and Citizens Community Credit Union exports, and most other banks too), open the account, choose Export or Download, and save your transactions as a CSV file.
2. Upload that CSV in the "Import Bills from Bank CSV" section of the app.
3. The app auto-detects the date, description, and amount columns and scans for charges that repeat across 2 or more months at a similar amount.
4. Review the suggested recurring bills it finds. Click "Add to recurring payments" on the ones you want. Nothing is added automatically, one-time purchases are intentionally left out, and you decide what gets added.

## Running Locally
1. Clone this repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `streamlit run app.py`

## Deploying
This app is ready to be deployed on Streamlit Community Cloud or any other platform supporting Python.
