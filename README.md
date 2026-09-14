# Personal Budget & Calendar App

A Streamlit application to manage your income, expenses, and forecast your weekly rolling balance.

## Deployment Instructions (Free on Streamlit Community Cloud)

Follow these step-by-step instructions to deploy your app so you can access it anywhere (phone or browser).

### 1. Create a GitHub Account and Repository
1. Go to [GitHub](https://github.com/) and create a free account if you don't have one.
2. Once logged in, click the **+** icon in the top right corner and select **New repository**.
3. Name your repository (e.g., `budget-app`).
4. Choose **Public** or **Private** (Private is recommended for personal finances, Streamlit allows 1 free private app).
5. Do NOT check "Add a README file" (you are uploading this one!).
6. Click **Create repository**.

### 2. Upload Your Files to GitHub
1. On your new repository page, click the link that says **uploading an existing file**.
2. Drag and drop the following files into the upload box:
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Wait for them to upload, add a brief commit message like "Initial commit", and click **Commit changes**.

### 3. Deploy on Streamlit Community Cloud
1. Go to [Streamlit Community Cloud](https://share.streamlit.io/) and sign up/log in. **Important:** Sign in using your GitHub account to link them automatically.
2. Click the **New app** button.
3. Since you linked GitHub, you will see a dropdown to select your repository. Select the repository you just created (e.g., `Glade/budget-app`).
4. For **Branch**, select `main`.
5. For **Main file path**, type `app.py`.
6. Click **Deploy!**

Streamlit will take a minute or two to install the requirements and launch your app. Once it's done, you will have a live URL to access your app from any device!
