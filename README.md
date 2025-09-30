# If using git
git clone <repository-url>
cd task-tracker-app

# Create Virtual Environment
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate

# Install Dependencies
pip install flask

# Project Structure Setup
task-tracker-app/
├── backend/
│   ├── app.py
│   ├── templates/
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── forgot_password.html
│   │   ├── verify_otp.html
│   │   ├── reset_password.html
│   │   ├── dashboard.html
│   │   ├── timesheet.html
│   │   └── weekly_report.html
│   └── static/
├── database/
│   └── database.db (auto-created)
└── README.md

# Configure Email (Optional)
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"

# Run the Application(if you're using Powershell)
cd backend
python app.py
